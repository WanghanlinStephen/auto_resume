import jwt
from django.conf import settings
from django.contrib.auth.models import User
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse

SECRET_KEY = settings.SECRET_KEY  # ✅ 确保和 encode 的 SECRET_KEY 一致

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.user = None  # **默认 user 为空**

        auth_header = request.headers.get("Authorization", None)
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user = User.objects.filter(id=payload["id"]).first()
                if user:
                    request.user = user  # ✅ **成功解析 token，赋值 user**
                else:
                    request.user = None  # 用户不存在
            except jwt.ExpiredSignatureError:
                return JsonResponse({"error": "Token 已过期"}, status=401)
            except jwt.DecodeError:
                return JsonResponse({"error": "无效 Token"}, status=401)
