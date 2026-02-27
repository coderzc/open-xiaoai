use open_xiaoai::services::audio::config::AudioConfig;
use open_xiaoai::services::monitor::kws::KwsMonitor;
use serde_json::json;
use serde_json::Value;
use std::sync::{Arc, LazyLock};
use std::time::Instant;
use std::time::Duration;
use tokio::time::sleep;
use tokio_tungstenite::connect_async;

use open_xiaoai::base::AppError;
use open_xiaoai::base::VERSION;
use open_xiaoai::services::audio::play::AudioPlayer;
use open_xiaoai::services::audio::record::AudioRecorder;
use open_xiaoai::services::connect::data::{Event, Request, Response, Stream};
use open_xiaoai::services::connect::handler::MessageHandler;
use open_xiaoai::services::connect::message::{MessageManager, WsStream};
use open_xiaoai::services::connect::rpc::RPC;
use open_xiaoai::services::monitor::file::FileMonitorEvent;
use open_xiaoai::services::monitor::instruction::InstructionMonitor;
use open_xiaoai::services::monitor::playing::PlayingMonitor;
use tokio::sync::Mutex;
use tokio::task::JoinHandle;

struct AppClient {
    kws_monitor: KwsMonitor,
    instruction_monitor: InstructionMonitor,
    playing_monitor: PlayingMonitor,
    server_stream_monitor_task: Option<JoinHandle<()>>,
}

#[derive(Default)]
struct ServerStreamState {
    active: bool,
    last_chunk_at: Option<Instant>,
}

static SERVER_STREAM_STATE: LazyLock<Arc<Mutex<ServerStreamState>>> =
    LazyLock::new(|| Arc::new(Mutex::new(ServerStreamState::default())));

impl AppClient {
    pub fn new() -> Self {
        Self {
            kws_monitor: KwsMonitor::new(),
            instruction_monitor: InstructionMonitor::new(),
            playing_monitor: PlayingMonitor::new(),
            server_stream_monitor_task: None,
        }
    }

    pub async fn connect(&self, url: &str) -> Result<WsStream, AppError> {
        let (ws_stream, _) = connect_async(url).await?;
        Ok(WsStream::Client(ws_stream))
    }

    pub async fn run(&mut self) {
        let url = std::env::args().nth(1).expect("❌ 请输入服务器地址");
        println!("✅ 已启动");
        loop {
            let Ok(ws_stream) = self.connect(&url).await else {
                sleep(Duration::from_secs(1)).await;
                continue;
            };
            println!("✅ 已连接: {:?}", url);
            self.init(ws_stream).await;
            if let Err(e) = MessageManager::instance().process_messages().await {
                eprintln!("❌ 消息处理异常: {}", e);
            }
            self.dispose().await;
            eprintln!("❌ 已断开连接");
        }
    }

    async fn init(&mut self, ws_stream: WsStream) {
        MessageManager::instance().init(ws_stream).await;
        MessageHandler::<Event>::instance()
            .set_handler(on_event)
            .await;
        MessageHandler::<Stream>::instance()
            .set_handler(on_stream)
            .await;

        let rpc = RPC::instance();
        rpc.add_command("get_version", get_version).await;
        rpc.add_command("run_shell", run_shell).await;
        rpc.add_command("start_play", start_play).await;
        rpc.add_command("stop_play", stop_play).await;
        rpc.add_command("start_recording", start_recording).await;
        rpc.add_command("stop_recording", stop_recording).await;

        self.instruction_monitor
            .start(|event| async move {
                MessageManager::instance()
                    .send_event("instruction", Some(json!(event)))
                    .await?;

                if let Some(tts_state_event) = extract_tts_state_event(&event) {
                    MessageManager::instance()
                        .send_event("tts_state", Some(tts_state_event))
                        .await?;
                }
                Ok(())
            })
            .await;

        self.playing_monitor
            .start(|event| async move {
                MessageManager::instance()
                    .send_event("playing", Some(json!(event)))
                    .await
            })
            .await;

        self.kws_monitor
            .start(|event| async move {
                MessageManager::instance()
                    .send_event("kws", Some(json!(event)))
                    .await
            })
            .await;

        self.start_server_stream_tts_monitor().await;
    }

    async fn dispose(&mut self) {
        MessageManager::instance().dispose().await;
        let _ = AudioPlayer::instance().stop().await;
        let _ = AudioRecorder::instance().stop_recording().await;
        self.instruction_monitor.stop().await;
        self.playing_monitor.stop().await;
        self.kws_monitor.stop().await;
        if let Some(task) = self.server_stream_monitor_task.take() {
            task.abort();
        }
        let mut state = SERVER_STREAM_STATE.lock().await;
        state.active = false;
        state.last_chunk_at = None;
    }

    async fn start_server_stream_tts_monitor(&mut self) {
        if let Some(task) = self.server_stream_monitor_task.take() {
            task.abort();
        }
        let state = SERVER_STREAM_STATE.clone();
        self.server_stream_monitor_task = Some(tokio::spawn(async move {
            loop {
                sleep(Duration::from_millis(100)).await;
                let should_stop = {
                    let mut guard = state.lock().await;
                    if !guard.active {
                        false
                    } else {
                        match guard.last_chunk_at {
                            Some(last) if last.elapsed() >= Duration::from_millis(800) => {
                                guard.active = false;
                                guard.last_chunk_at = None;
                                true
                            }
                            _ => false,
                        }
                    }
                };
                if should_stop {
                    let _ = MessageManager::instance()
                        .send_event(
                            "tts_state",
                            Some(json!({
                                "state": "stop",
                                "source": "server_stream",
                                "reason": "chunk_inactive_timeout",
                            })),
                        )
                        .await;
                }
            }
        }));
    }
}

async fn get_version(_: Request) -> Result<Response, AppError> {
    let data = json!(VERSION.to_string());
    Ok(Response::from_data(data))
}

async fn start_play(request: Request) -> Result<Response, AppError> {
    let config = request
        .payload
        .and_then(|payload| serde_json::from_value::<AudioConfig>(payload).ok());
    AudioPlayer::instance().start(config).await?;
    Ok(Response::success())
}

async fn stop_play(_: Request) -> Result<Response, AppError> {
    AudioPlayer::instance().stop().await?;
    Ok(Response::success())
}

async fn start_recording(request: Request) -> Result<Response, AppError> {
    let config = request
        .payload
        .and_then(|payload| serde_json::from_value::<AudioConfig>(payload).ok());
    AudioRecorder::instance()
        .start_recording(
            |bytes| async {
                MessageManager::instance()
                    .send_stream("record", bytes, None)
                    .await
            },
            config,
        )
        .await?;
    Ok(Response::success())
}

async fn stop_recording(_: Request) -> Result<Response, AppError> {
    AudioRecorder::instance().stop_recording().await?;
    Ok(Response::success())
}

async fn run_shell(request: Request) -> Result<Response, AppError> {
    let script = match request.payload {
        Some(payload) => serde_json::from_value::<String>(payload)?,
        _ => return Err("empty command".into()),
    };
    let res = open_xiaoai::utils::shell::run_shell(script.as_str()).await?;
    Ok(Response::from_data(json!(res)))
}

async fn on_event(event: Event) -> Result<(), AppError> {
    println!("🔥 收到事件: {:?}", event);
    Ok(())
}

async fn on_stream(stream: Stream) -> Result<(), AppError> {
    let Stream { tag, bytes, .. } = stream;
    if tag.as_str() == "play" {
        let is_new_stream = {
            let mut state = SERVER_STREAM_STATE.lock().await;
            state.last_chunk_at = Some(Instant::now());
            if !state.active {
                state.active = true;
                true
            } else {
                false
            }
        };
        if is_new_stream {
            let _ = MessageManager::instance()
                .send_event(
                    "tts_state",
                    Some(json!({
                        "state": "start",
                        "source": "server_stream",
                    })),
                )
                .await;
        }
        // 播放接收到的音频流
        let _ = AudioPlayer::instance().play(bytes).await;
    }
    Ok(())
}

fn extract_tts_state_event(event: &FileMonitorEvent) -> Option<Value> {
    let FileMonitorEvent::NewLine(line) = event else {
        return None;
    };
    let root = serde_json::from_str::<Value>(line).ok()?;
    let header = root.get("header")?;
    let namespace = header.get("namespace")?.as_str()?;
    if namespace != "AudioPlayer" {
        return None;
    }
    let name = header
        .get("name")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    let state = infer_tts_state(name)?;
    Some(json!({
        "state": state,
        "name": name,
        "source": "instruction",
    }))
}

fn infer_tts_state(name: &str) -> Option<&'static str> {
    let lower = name.to_ascii_lowercase();
    // Common finish/end tokens from AudioPlayer directives.
    if lower.contains("finish")
        || lower.contains("end")
        || lower.contains("complete")
        || lower.contains("stop")
        || lower.contains("pause")
    {
        return Some("stop");
    }
    // Common start tokens from AudioPlayer directives.
    if lower.contains("start")
        || lower.contains("play")
        || lower.contains("resume")
        || lower.contains("speak")
    {
        return Some("start");
    }
    None
}

#[tokio::main]
async fn main() {
    AppClient::new().run().await;
}
