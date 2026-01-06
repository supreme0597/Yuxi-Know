import asyncio
import time
from collections import defaultdict, deque

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from server.routers import router
from server.utils.lifespan import lifespan
from server.utils.auth_middleware import is_public_path
from server.utils.common_utils import setup_logging
from server.utils.access_log_middleware import AccessLogMiddleware

# 设置日志配置
setup_logging()

RATE_LIMIT_MAX_ATTEMPTS = 10
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_ENDPOINTS = {("/api/auth/token", "POST")}

# Redis 客户端（延迟初始化）
_redis_client = None
_redis_available = None


def get_redis_client():
    """获取 Redis 客户端（用于频率限制）"""
    global _redis_client, _redis_available
    
    if _redis_available is False:
        return None
    
    if _redis_client is None:
        try:
            import redis
            import os
            
            _redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                password=os.getenv("REDIS_PASSWORD"),
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 测试连接
            _redis_client.ping()
            _redis_available = True
            from src.utils.logging_config import logger
            logger.info("Redis connected for rate limiting")
        except Exception as e:
            from src.utils.logging_config import logger
            logger.warning(f"Redis unavailable, rate limiting will use in-memory fallback: {e}")
            _redis_available = False
            _redis_client = None
    
    return _redis_client


# 内存降级存储（Redis 不可用时）
_login_attempts_fallback: defaultdict[str, deque[float]] = defaultdict(deque)
_fallback_lock = asyncio.Lock()

app = FastAPI(lifespan=lifespan)
app.include_router(router, prefix="/api")

# CORS 设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    """登录频率限制中间件（支持 Redis 分布式限流）"""
    
    async def dispatch(self, request: Request, call_next):
        normalized_path = request.url.path.rstrip("/") or "/"
        request_signature = (normalized_path, request.method.upper())

        if request_signature in RATE_LIMIT_ENDPOINTS:
            client_ip = _extract_client_ip(request)
            redis_client = get_redis_client()
            
            # 使用 Redis 或降级到内存
            if redis_client:
                # Redis 模式
                is_limited, retry_after = await self._check_rate_limit_redis(client_ip, redis_client)
            else:
                # 内存降级模式
                is_limited, retry_after = await self._check_rate_limit_memory(client_ip)
            
            if is_limited:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "登录尝试过于频繁，请稍后再试"},
                    headers={"Retry-After": str(retry_after)},
                )

            response = await call_next(request)

            # 登录成功，清除限制
            if response.status_code < 400:
                if redis_client:
                    try:
                        key = f"yuxi:login_attempts:{client_ip}"
                        redis_client.delete(key)
                    except Exception:
                        pass
                else:
                    async with _fallback_lock:
                        _login_attempts_fallback.pop(client_ip, None)

            return response

        return await call_next(request)
    
    async def _check_rate_limit_redis(self, client_ip: str, redis_client) -> tuple[bool, int]:
        """使用 Redis 检查频率限制"""
        try:
            key = f"yuxi:login_attempts:{client_ip}"
            
            # 使用 Redis 事务保证原子性
            pipe = redis_client.pipeline()
            pipe.incr(key)
            pipe.expire(key, RATE_LIMIT_WINDOW_SECONDS)
            pipe.ttl(key)
            results = pipe.execute()
            
            attempts = results[0]
            ttl = results[2]
            
            if attempts > RATE_LIMIT_MAX_ATTEMPTS:
                retry_after = max(1, ttl)
                return True, retry_after
            
            return False, 0
            
        except Exception as e:
            from src.utils.logging_config import logger
            logger.error(f"Redis rate limit check failed: {e}")
            # 降级到内存模式
            return await self._check_rate_limit_memory(client_ip)
    
    async def _check_rate_limit_memory(self, client_ip: str) -> tuple[bool, int]:
        """使用内存检查频率限制（降级方案）"""
        now = time.monotonic()
        
        async with _fallback_lock:
            attempt_history = _login_attempts_fallback[client_ip]
            
            # 清理过期记录
            while attempt_history and now - attempt_history[0] > RATE_LIMIT_WINDOW_SECONDS:
                attempt_history.popleft()
            
            if len(attempt_history) >= RATE_LIMIT_MAX_ATTEMPTS:
                retry_after = int(max(1, RATE_LIMIT_WINDOW_SECONDS - (now - attempt_history[0])))
                return True, retry_after
            
            attempt_history.append(now)
            return False, 0


# 鉴权中间件
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 获取请求路径
        path = request.url.path

        # 检查是否为公开路径，公开路径无需身份验证
        if is_public_path(path):
            return await call_next(request)

        if not path.startswith("/api"):
            # 非API路径，可能是前端路由或静态资源
            return await call_next(request)

        # # 提取Authorization头
        # auth_header = request.headers.get("Authorization")
        # if not auth_header or not auth_header.startswith("Bearer "):
        #     return JSONResponse(
        #         status_code=status.HTTP_401_UNAUTHORIZED,
        #         content={"detail": f"请先登录。Path: {path}"},
        #         headers={"WWW-Authenticate": "Bearer"}
        #     )

        # # 获取token
        # token = auth_header.split("Bearer ")[1]

        # # 添加token到请求状态，后续路由可以直接使用
        # request.state.token = token

        # 继续处理请求
        return await call_next(request)


# 添加访问日志中间件（记录请求处理时间）
app.add_middleware(AccessLogMiddleware)

# 添加鉴权中间件
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(AuthMiddleware)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5050, threads=10, workers=10, reload=True)
