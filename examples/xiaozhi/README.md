# Open-XiaoAI x 小智 AI

[Open-XiaoAI](https://github.com/idootop/open-xiaoai) 的 Python 版 Server 端，用来演示小爱音箱接入[小智 AI](https://github.com/78/xiaozhi-esp32)。

> [!IMPORTANT]
> 本项目只是一个简单的演示程序，抛砖引玉。诸如一些音频压缩、加密传输、多账号管理等功能并未提供，建议只在局域网内测试运行，不推荐部署在公网服务器上（消耗流量 100kb/s），请自行评估相关风险，合理使用。

## 功能特性

- 小爱音箱接入小智 AI
- 支持连续对话和中途打断
- 自定义唤醒词（中英文）和提示语
- 支持自定义消息处理，方便个人定制
- **HTTP API Server** - 支持远程播放文字/音频/TTS ([详情](#api-server))
- **连续对话模式** - 小爱原生支持多轮对话，无需反复唤醒
- **VAD + KWS 唤醒** - 语音活动检测前置，避免唤醒词长期监听，更省电
- **环境变量配置** - 通过 `XIAOZHI_ENABLE` 和 `API_SERVER_ENABLE` 灵活控制服务启停

## 与上游的主要改进

相较于 [idootop/open-xiaoai](https://github.com/idootop/open-xiaoai) 上游版本，本 fork 主要做了以下增强：

1. **小爱连续对话** - 新增小爱音箱原生的连续对话模式，支持多轮交互
2. **VAD 前置优化** - 在 KWS 唤醒词检测前增加 VAD 语音活动检测，避免唤醒词模型长期处于工作状态，降低资源消耗
3. **HTTP API Server** - 新增 RESTful API，支持远程播放文字、音频文件、TTS 合成（参见下方 API 文档）
4. **服务模块化** - 支持通过环境变量 `XIAOZHI_ENABLE` 和 `API_SERVER_ENABLE` 独立控制小智 AI 连接和 API 服务启停

## 快速开始

> [!NOTE]
> 继续下面的操作之前，你需要先在小爱音箱上启动运行 Rust 补丁程序 [👉 教程](../../packages/client-rust/README.md)

首先，克隆仓库代码到本地。

```shell
# 克隆代码
git clone https://github.com/idootop/open-xiaoai.git

# 进入当前项目根目录
cd examples/xiaozhi
```

然后把 `config.py` 文件里的配置修改成你自己的。

```typescript
APP_CONFIG = {
    "wakeup": {
        # 自定义唤醒词
        "keywords": [
            "豆包豆包",
            "你好小智",
            "hi siri",
        ],
    },
    "xiaozhi": {
        "OTA_URL": "https://api.tenclass.net/xiaozhi/ota/",
        "WEBSOCKET_URL": "wss://api.tenclass.net/xiaozhi/v1/",
    },
}
```

### Docker 运行

[![Docker Image Version](https://img.shields.io/docker/v/idootop/open-xiaoai-xiaozhi?color=%23086DCD&label=docker%20image)](https://hub.docker.com/r/idootop/open-xiaoai-xiaozhi)

推荐使用以下命令，直接 Docker 一键运行。

```shell
docker run -it --rm -p 4399:4399 -v $(pwd)/config.py:/app/config.py idootop/open-xiaoai-xiaozhi:latest
```

### 编译运行

为了能够正常编译运行该项目，你需要安装以下依赖环境/工具：

- uv：https://github.com/astral-sh/uv
- Rust: https://www.rust-lang.org/learn/get-started
- [Opus](https://opus-codec.org/): 自行询问 AI 如何安装动态链接库，或参考[这篇文章](https://github.com/huangjunsen0406/py-xiaozhi/blob/3bfd2887244c510a13912c1d63263ae564a941e9/documents/docs/guide/01_%E7%B3%BB%E7%BB%9F%E4%BE%9D%E8%B5%96%E5%AE%89%E8%A3%85.md#2-opus-%E9%9F%B3%E9%A2%91%E7%BC%96%E8%A7%A3%E7%A0%81%E5%99%A8)

```bash
# 安装 Python 依赖
uv sync --locked

# 编译运行（仅小爱音箱模式）
uv run main.py

# 开启小智 AI 连接
XIAOZHI_ENABLE=1 uv run main.py

# 开启 API Server
API_SERVER_ENABLE=1 uv run main.py

# 全功能模式（小爱 + 小智 AI + API Server）
XIAOZHI_ENABLE=1 API_SERVER_ENABLE=1 uv run main.py

# 或者设置环境变量 CLI=true，开启 CLI 模式（支持自定义唤醒词）
CLI=true XIAOZHI_ENABLE=1 uv run main.py
```

### 环境变量配置

| 环境变量 | 说明 | 示例 |
|---------|------|------|
| `XIAOZHI_ENABLE` | 连接小智 AI 服务 | `XIAOZHI_ENABLE=1` |
| `API_SERVER_ENABLE` | 开启 HTTP API 服务（端口 9092） | `API_SERVER_ENABLE=1` |
| `CLI` | 使用 CLI 模式（无 GUI，支持唤醒词） | `CLI=true` |
| `OPENCLAW_ENABLED` | 启用 OpenClaw 集成 | `OPENCLAW_ENABLED=true` |
| `OPENCLAW_URL` | OpenClaw WebSocket 地址 | `OPENCLAW_URL=ws://localhost:4399` |
| `OPENCLAW_TOKEN` | OpenClaw 认证令牌 | `OPENCLAW_TOKEN=your_token` |

## OpenClaw 集成

支持通过 [OpenClaw](../openclaw/README.md) 将消息转发到外部 AI Agent 服务。

### 启用 OpenClaw

```bash
# 启用 OpenClaw（需在 config.py 中配置 URL 和 Token）
OPENCLAW_ENABLED=true uv run main.py

# 或通过环境变量完整配置
OPENCLAW_ENABLED=true OPENCLAW_URL=ws://your-server:4399 OPENCLAW_TOKEN=xxx uv run main.py
```

### 在 before_wakeup 中使用

编辑 `config.py`，通过 `app.send_to_openclaw()` 发送消息：

```python
async def before_wakeup(speaker, text, source, xiaozhi, xiaoai, app):
    if source == "xiaoai":
        if text.startswith("问龙虾"):
            # 发送给 OpenClaw，不唤醒小智
            await app.send_to_openclaw(text.replace("问龙虾", ""))
            return False
    return True
```

## 常见问题

### Q：回答太长了，如何打断小智 AI 的回答？

直接召唤“小爱同学”，即可打断小智 AI 的回答 ;)

### Q：第一次运行提示我输入验证码绑定设备，如何操作？

第一次启动对话时，会有语音提示使用验证码绑定设备。请打开你的小智 AI [管理后台](https://xiaozhi.me/)，然后根据提示创建 Agent 绑定设备即可。验证码消息会在终端打印，或者打开你的 `config.py` 文件查看。

```py
APP_CONFIG = {
    "xiaozhi": {
        "VERIFICATION_INFO": "首次登录时，验证码会在这里更新",
    },
    # ... 其他配置
}
```

PS：绑定设备成功后，可能需要重启应用才会生效。

### Q：怎样使用自己部署的 [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server) 服务？

如果你想使用自己部署的 [xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server)，请更新 `config.py` 文件里的接口地址，然后重启应用。

```py
APP_CONFIG = {
    "xiaozhi": {
        "OTA_URL": "https://2662r3426b.vicp.fun/xiaozhi/ota/",
        "WEBSOCKET_URL": "wss://2662r3426b.vicp.fun/xiaozhi/v1/",
    },
    # ... 其他配置
}
```

### Q：有时候话还没说完 AI 就开始回答了，如何优化？

你可以调大 `config.py` 配置文件里的 `min_silence_duration` 参数，然后重启应用 / Docker 试试看。

```py
APP_CONFIG = {
    "vad": {
        # 最小静默时长（ms）
        "min_silence_duration": 1000,
    },
    # ... 其他配置
}
```

### Q：对话的时候，文字识别不是很准？

文字识别结果取决于你的小智 AI 服务器端的语音识别方案，与本项目无关。

### Q：唤醒词一直没有反应？

如果唤醒词还是不敏感，可以先调低 `vad.threshold`，然后重启应用 / Docker 试试看。

```py
APP_CONFIG = {
    "vad": {
        # 语音检测阈值（0-1，越小越灵敏）
        "threshold": 0.05,
    },
    # ... 其他配置
}
```

另外，应用 / Docker 刚刚启动时需要加载模型文件，比较耗时一些，可以等 30s 之后再试试看。

如果是英文唤醒词，可以尝试将最小发音用空格分开，比如：比如：'openai' 👉 'open ai'

PS：如果还是不行，建议更换其他更易识别的唤醒词。

## API Server

当设置 `API_SERVER_ENABLE=1` 启动时，会开启 HTTP API 服务（默认端口 9092），支持以下接口：

### API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/play/text` | 播放文字（TTS） |
| POST | `/api/play/url` | 播放音频链接 |
| POST | `/api/play/file` | 上传并播放音频文件 |
| POST | `/api/tts/doubao` | 豆包 TTS 合成并播放 |
| GET | `/api/tts/doubao_voices` | 获取可用音色列表 |
| POST | `/api/wakeup` | 唤醒小爱音箱 |
| POST | `/api/interrupt` | 打断当前播放 |
| GET | `/api/status` | 获取播放状态 |
| GET | `/api/health` | 健康检查 |

### 使用示例

```bash
# 播放文字
curl -X POST http://localhost:9092/api/play/text \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，我是小爱同学"}'

# 播放音频链接
curl -X POST http://localhost:9092/api/play/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/audio.mp3"}'

# 上传音频文件
curl -X POST http://localhost:9092/api/play/file \
  -F "file=@/path/to/audio.mp3"

# 豆包 TTS
curl -X POST http://localhost:9092/api/tts/doubao \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，这是豆包语音合成", "speaker": "zh_female_cancan_mars_bigtts"}'

# 打断当前播放
curl -X POST http://localhost:9092/api/interrupt
```

### Q: 我想自己编译运行，模型文件在哪里下载？

由于 ASR 相关模型文件体积较大，并未直接提交在 git 仓库中，你可以在 release 中下载 [VAD + KWS 相关模型](https://github.com/idootop/open-xiaoai/releases/tag/vad-kws-models)，然后解压到 `xiaozhi/models` 路径下即可。

## 相关项目

- [oxa-server](https://github.com/pu-007/oxa-server): 提供了更强大易用的 config.py 的配置方式

## 鸣谢

该演示使用的 Python 版小智 AI 客户端基于 [py-xiaozhi](https://github.com/Huang-junsen/py-xiaozhi) 项目，特此鸣谢。
