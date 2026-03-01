"""OpenClaw integration manager for xiaozhi.

Configuration (priority: env vars > config file > defaults):

    1. config.py:
        APP_CONFIG = {
            "openclaw": {
                "enabled": True,
                "url": "ws://localhost:4399",
                "token": "your_token",
                "session_key": "main",
            }
        }

    2. Environment variables (override config):
        export OPENCLAW_ENABLED=true
        export OPENCLAW_URL=ws://localhost:4399
        export OPENCLAW_TOKEN=your_token
        export OPENCLAW_SESSION_KEY=main

Usage:
    from xiaozhi.openclaw import OpenClawManager
    await OpenClawManager.send_message("Hello OpenClaw")
"""

import asyncio
import json
import uuid

import websockets

from xiaozhi.utils.base import get_env
from xiaozhi.utils.logger import logger


class OpenClawManager:
    """Manager for OpenClaw connection and messaging."""

    _instance = None
    _initialized = False

    # Connection
    _websocket = None
    _connected = False
    _receiver_task = None
    _pending: dict[str, asyncio.Future] = {}

    # Config
    _enabled = False
    _url = None
    _token = None
    _session_key = None
    last_error: str | None = None

    @classmethod
    def initialize(cls):
        """Initialize the manager (called once at startup).

        Configuration priority (highest first):
        1. Environment variables (OPENCLAW_*)
        2. APP_CONFIG["openclaw"]
        3. Default values
        """
        if cls._initialized:
            return

        from config import APP_CONFIG

        # Get config from APP_CONFIG with defaults
        config = APP_CONFIG.get("openclaw", {})
        cfg_url = config.get("url", "ws://localhost:4399")
        cfg_token = config.get("token", "")
        cfg_session = config.get("session_key", "main")

        # Only environment variable controls enable/disable
        env_enabled = get_env("OPENCLAW_ENABLED")
        if env_enabled is not None:
            cls._enabled = env_enabled.lower() == "true"
        else:
            cls._enabled = False  # Default to disabled if no env var set

        cls._url = get_env("OPENCLAW_URL", cfg_url)
        cls._token = get_env("OPENCLAW_TOKEN", cfg_token)
        cls._session_key = get_env("OPENCLAW_SESSION_KEY", cfg_session)

        if cls._enabled:
            logger.info(f"[OpenClaw] Enabled, will connect to {cls._url}")
        else:
            logger.info("[OpenClaw] Disabled (set openclaw.enabled=true in config or OPENCLAW_ENABLED=true env)")

        cls._initialized = True

    @classmethod
    async def connect(cls) -> bool:
        """Connect to OpenClaw gateway."""
        if not cls._initialized:
            cls.initialize()

        if not cls._enabled:
            return False

        if cls._connected and cls._websocket:
            return True

        try:
            cls._websocket = await websockets.connect(cls._url)
            cls._receiver_task = asyncio.create_task(cls._receiver())

            # Send connect request
            res = await cls._request(
                "connect",
                {
                    "minProtocol": 3,
                    "maxProtocol": 3,
                    "client": {
                        "id": "openclaw-xiaoai",
                        "displayName": "Xiaoai OpenClaw Bridge",
                        "version": "1.0.0",
                        "platform": "open-xiaoai",
                        "mode": "ui",
                        "instanceId": f"xiaoai-{uuid.uuid4().hex[:8]}",
                    },
                    "locale": "zh-CN",
                    "userAgent": "xiaoai-bridge",
                    "role": "operator",
                    "scopes": ["operator.read", "operator.write"],
                    "caps": [],
                    "auth": {"token": cls._token},
                },
                timeout=10,
            )

            if res.get("ok"):
                cls._connected = True
                logger.info(f"[OpenClaw] Connected to {cls._url}")
                return True
            else:
                error = (res.get("error") or {}).get("message") or "connect failed"
                logger.error(f"[OpenClaw] Connection failed: {error}")
                return False

        except Exception as e:
            logger.error(f"[OpenClaw] Connection error: {e}")
            return False

    @classmethod
    async def close(cls):
        """Close the connection."""
        cls._connected = False
        if cls._receiver_task:
            cls._receiver_task.cancel()
            cls._receiver_task = None
        if cls._websocket:
            await cls._websocket.close()
            cls._websocket = None

    @classmethod
    async def send_message(cls, text: str) -> bool:
        """Send a message to OpenClaw.

        Sends message and waits for agent response to confirm acceptance,
        but does not wait for the full conversation completion.

        Args:
            text: The message text to send

        Returns:
            True if message was accepted by OpenClaw, False otherwise
        """
        if not cls._initialized:
            cls.initialize()

        if not cls._enabled:
            return False

        if not cls._connected:
            # Try to connect if not connected
            if not await cls.connect():
                return False

        try:
            idem = str(uuid.uuid4())
            # Send agent request and wait for acceptance response
            agent_res = await cls._request(
                "agent",
                {
                    "message": text,
                    "sessionKey": cls._session_key,
                    "deliver": False,
                    "idempotencyKey": idem,
                },
                timeout=60,
            )

            if not agent_res.get("ok"):
                err = (agent_res.get("error") or {}).get("message") or str(agent_res)
                cls.last_error = err
                logger.error(f"[OpenClaw] agent call failed: {agent_res}")
                return False

            run_id = (agent_res.get("payload") or {}).get("runId")
            if not run_id:
                cls.last_error = "agent response missing runId"
                logger.error(f"[OpenClaw] agent response missing runId: {agent_res}")
                return False

            logger.info(f"[OpenClaw] Message accepted, runId: {run_id}")
            return True
        except Exception as e:
            logger.error(f"[OpenClaw] Failed to send message: {e}")
            return False

    @classmethod
    async def _request(cls, method: str, params=None, timeout: float = 30):
        """Send a request and wait for response."""
        if not cls._websocket:
            raise RuntimeError("OpenClaw websocket is not connected")

        req_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        cls._pending[req_id] = fut

        await cls._websocket.send(
            json.dumps(
                {
                    "type": "req",
                    "id": req_id,
                    "method": method,
                    "params": params or {},
                }
            )
        )

        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            cls._pending.pop(req_id, None)

    @classmethod
    async def _receiver(cls):
        """Background task to receive responses."""
        try:
            async for message in cls._websocket:
                if not isinstance(message, str):
                    continue

                try:
                    data = json.loads(message)
                    if data.get("type") != "res":
                        continue

                    req_id = data.get("id")
                    if not req_id:
                        continue

                    future = cls._pending.get(req_id)
                    if future and not future.done():
                        future.set_result(data)
                except json.JSONDecodeError:
                    pass
        except Exception:
            cls._connected = False

    @classmethod
    def is_connected(cls) -> bool:
        """Check if connected to OpenClaw."""
        return cls._connected and cls._websocket is not None

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if OpenClaw is enabled."""
        if not cls._initialized:
            cls.initialize()
        return cls._enabled


# Auto-initialize on import
OpenClawManager.initialize()
