FROM python:3.12-slim AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# 更新源
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential libopus-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

# 设置环境变量
ENV BASH_ENV=/root/.bash_env
RUN touch "$BASH_ENV"
RUN echo '. "$BASH_ENV"' >> "$HOME/.bashrc"
RUN echo '[ -s "$HOME/.cargo/env" ] && . "$HOME/.cargo/env"' >> "$BASH_ENV"

# 设置工作目录
WORKDIR /app

# 复制项目文件
COPY examples/xiaozhi .
COPY packages/client-rust ./client-rust

# 构建
RUN sed -i 's/\.\.\/\.\.\/packages\///g' Cargo.toml \
    && cargo build --release

# 安装依赖
RUN --mount=type=cache,target=/root/.cache/uv \
    uv remove pyaudio && uv sync --locked --no-install-project --no-editable

# 构建 wheel 并安装
RUN uv run maturin build --release && uv remove maturin


FROM python:3.12-slim

WORKDIR /app

# 更新源
RUN apt-get update && apt-get install -y --no-install-recommends \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

ENV CLI=true

COPY --from=builder /app/.venv /app/.venv
COPY examples/xiaozhi/main.py . 
COPY examples/xiaozhi/xiaozhi ./xiaozhi

# 先初始化关键词模型，然后启动主程序
CMD ["/bin/bash", "-c", "source /app/.venv/bin/activate && python xiaozhi/services/audio/kws/keywords.py && python main.py"]
