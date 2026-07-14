"""
HTTP 请求日志中间件

拦截所有进入后端的请求，记录：
  → 请求：方法、路径、查询参数、客户端 IP、请求体摘要
  ← 响应：状态码、耗时、响应体摘要

注意：使用纯 ASGI 中间件实现，而非 BaseHTTPMiddleware。
BaseHTTPMiddleware 在 uvicorn --reload 模式下存在静默失败的问题（dispatch 不被调用），
纯 ASGI 实现更可靠，也没有 BaseHTTPMiddleware 的性能开销。
"""

import time

from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import access_logger


def _truncate(data: str, max_len: int = 500) -> str:
    return data if len(data) <= max_len else data[:max_len] + "…"


class AccessLogMiddleware:
    """纯 ASGI 请求日志中间件"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            # 非 HTTP 请求（如 WebSocket、lifespan）直接透传
            await self.app(scope, receive, send)
            return

        # 构造 Request 对象，方便读取请求信息
        request = Request(scope, receive)

        path = request.url.path
        # 跳过非业务路径（OpenAPI 文档等）
        if path in ("/docs", "/redoc", "/openapi.json") or path.startswith("/docs/"):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        method = request.method
        query = str(request.query_params) or "-"
        client_ip = request.client.host if request.client else "unknown"

        # 读取请求体（仅对有 body 的方法）
        # 关键：读取后必须构造新的 receive 传给下游 app，否则下游无法再读取请求体
        body_summary = "-"
        new_receive = receive  # 默认透传原始 receive
        if method in ("POST", "PUT", "PATCH"):
            try:
                raw = await request.body()
                if raw:
                    body_summary = _truncate(raw.decode("utf-8", errors="replace"))

                # 构造新的 receive，让下游 app 能重新读取已缓存的请求体
                # ASGI 规范中，http 请求体通过 receive() 获取
                # 传入 http.request 消息，body 标记 more_body=False 表示读取完毕
                async def receive_with_body() -> Message:
                    return {"type": "http.request", "body": raw, "more_body": False}

                new_receive = receive_with_body
            except Exception:
                body_summary = "<read error>"

        # 记录请求
        access_logger.info("→ %s %s  query=%s  ip=%s  body=%s", method, path, query, client_ip, body_summary)

        # 拦截响应，收集状态码和响应体
        status_code: int = 200
        resp_chunks: list[bytes] = []

        async def send_with_capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")
                if chunk:
                    resp_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
            await send(message)

        # 执行后续处理（使用新的 receive，确保下游能读取请求体）
        await self.app(scope, new_receive, send_with_capture)

        # 计算耗时
        duration_ms = round((time.perf_counter() - start) * 1000)

        # 读取响应体摘要（仅对业务接口）
        resp_summary = "-"
        if path.startswith("/api/") and resp_chunks:
            try:
                resp_body = b"".join(resp_chunks)
                resp_summary = _truncate(resp_body.decode("utf-8", errors="replace"))
            except Exception:
                resp_summary = "<read error>"

        log_func = access_logger.warning if status_code >= 400 else access_logger.info
        log_func("← %s %s  %d  %dms  resp=%s", method, path, status_code, duration_ms, resp_summary)
