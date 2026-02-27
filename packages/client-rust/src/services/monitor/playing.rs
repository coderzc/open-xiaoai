use serde::{Deserialize, Serialize};
use std::future::Future;
use tokio::task::JoinHandle;
use tokio::time::{sleep, Duration};
use std::time::Instant;

use crate::base::AppError;
use crate::utils::shell::run_shell;

#[derive(Debug, Serialize, Deserialize, PartialEq, Clone)]
pub enum PlayingMonitorEvent {
    Playing,
    Paused,
    Idle,
}

pub struct PlayingMonitor {
    task_holder: Option<JoinHandle<()>>,
}

impl Default for PlayingMonitor {
    fn default() -> Self {
        Self::new()
    }
}

impl PlayingMonitor {
    pub fn new() -> Self {
        Self { task_holder: None }
    }

    pub async fn start<F, Fut>(&mut self, on_update: F)
    where
        F: Fn(PlayingMonitorEvent) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<(), AppError>> + Send + 'static,
    {
        let monitor = tokio::spawn(async move {
            let _ = PlayingMonitor::start_monitor(on_update).await;
        });

        if let Some(old_task) = self.task_holder.replace(monitor) {
            println!("Aborting old playing monitor task");
            old_task.abort();
        };
    }

    pub async fn stop(&mut self) {
        if let Some(handle) = self.task_holder.take() {
            handle.abort();
        }
    }

    async fn start_monitor<F, Fut>(on_update: F) -> Result<(), AppError>
    where
        F: Fn(PlayingMonitorEvent) -> Fut + Send + Sync + 'static,
        Fut: Future<Output = Result<(), AppError>> + Send + 'static,
    {
        let mut last_status = PlayingMonitorEvent::Idle;
        let mut last_emit_at = Instant::now();
        loop {
            let res = run_shell("mphelper mute_stat").await?;
            let status = if res.stdout.contains("1") {
                PlayingMonitorEvent::Playing
            } else if res.stdout.contains("2") {
                PlayingMonitorEvent::Paused
            } else {
                PlayingMonitorEvent::Idle
            };

            // Some firmware paths don't emit a clear Playing->Idle transition.
            // Emit periodic idle heartbeats so upper layers can close a turn reliably.
            let should_emit_heartbeat =
                status == PlayingMonitorEvent::Idle
                    && last_status == PlayingMonitorEvent::Idle
                    && last_emit_at.elapsed() >= Duration::from_millis(500);

            if last_status != status || should_emit_heartbeat {
                last_status = status.clone();
                let _ = on_update(status).await;
                last_emit_at = Instant::now();
            }

            sleep(Duration::from_millis(50)).await;
        }
    }
}
