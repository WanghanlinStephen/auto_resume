import redis
from django.conf import settings

class RedisMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.redis_client = None

    def __call__(self, request):
        if not self.redis_client:
            self.redis_client = redis.StrictRedis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=getattr(settings, "REDIS_DB", 0),
                decode_responses=True,
                socket_timeout=5
            )
            try:
                self.redis_client.ping()
                print("✅ Middleware: Redis 连接成功！")
            except redis.ConnectionError:
                print("❌ Middleware: Redis 连接失败！")
                self.redis_client = None

        request.redis_client = self.redis_client
        response = self.get_response(request)
        return response
