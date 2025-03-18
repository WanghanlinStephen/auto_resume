
import requests
from datetime import datetime, timedelta
import uuid
from .aws_config import s3_client, AWS_STORAGE_BUCKET_NAME, S3_BASE_URL
import os
from .utils import generate_pdf_from_html,generate_html_from_json_resume,modify_resume_with_chatgpt,parse_resume_file,parse_modified_resume_to_json,generate_pdf_from_json_resume,check_rate_limit
from django.contrib.auth.models import User
import jwt
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate
from django.conf import settings
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import AlipayOrder, WeChatOrder, StripeOrder
from .serializers import AlipayOrderSerializer, WeChatOrderSerializer, StripeOrderSerializer
from .payment.alipay_payment import generate_alipay_url
from .payment.wechat import generate_wechat_qr
from .payment.stripe_pay import process_stripe_payment
import base64
import pytesseract
from PIL import Image
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from rest_framework import status
from functools import wraps



SECRET_KEY = settings.SECRET_KEY

# JWT 认证装饰器
def login_required(f):
    """JWT Token 认证装饰器"""
    @wraps(f)
    def decorated_function(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")  # 获取请求头
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "未提供有效 Token，无法访问"}, status=401)

        token = auth_header.split("Bearer ")[1]  # 只取 Token 部分
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = User.objects.get(id=payload["id"])  # 绑定 user
        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token 已过期"}, status=401)
        except jwt.InvalidTokenError:
            return JsonResponse({"error": "无效 Token"}, status=401)
        except User.DoesNotExist:
            return JsonResponse({"error": "用户不存在"}, status=401)

        return f(request, *args, **kwargs)
    return decorated_function

@csrf_exempt
def register(request):
    if request.method == "POST":
        data = json.loads(request.body)
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")

        # **🔥 检查用户名是否已存在**
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "用户名已存在，请使用其他用户名"}, status=400)

        # **🔥 检查邮箱是否已注册**
        if User.objects.filter(email=email).exists():
            return JsonResponse({"error": "邮箱已注册，请使用其他邮箱"}, status=400)

        # **🔥 创建新用户**
        user = User.objects.create_user(username=username, email=email, password=password)

        # **✅ 生成 JWT Token**
        token = jwt.encode({"id": user.id, "exp": datetime.utcnow() + timedelta(days=1)}, SECRET_KEY, algorithm="HS256")

        return JsonResponse({"message": "注册成功", "token": token}, status=201)


@csrf_exempt
def login(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        password = data.get("password")

        print("用户尝试登录:", email, password)  # 🔍 Debug 用

        # **🔥 用 email 找到对应的 `username`**
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return JsonResponse({"error": "用户不存在"}, status=400)

        user = authenticate(username=user.username, password=password)
        if user:
            token = jwt.encode({"id": user.id, "exp": datetime.utcnow() + timedelta(days=1)},
                               SECRET_KEY, algorithm="HS256")
            return JsonResponse({"token": token})
        return JsonResponse({"error": "用户名或密码错误"}, status=400)


@csrf_exempt
@login_required
def profile(request):
    """ 获取 & 更新用户信息 """
    if not request.user or request.user.is_anonymous:
        return JsonResponse({"error": "用户未认证"}, status=401)

    if request.method == "GET":
        return JsonResponse({
            "username": request.user.username,
            "email": request.user.email
        })

    elif request.method == "PUT":
        try:
            data = json.loads(request.body)
            old_password = data.get("old_password")
            new_password = data.get("password")

            # ✅ **如果要修改密码，必须提供 old_password**
            if new_password:
                if not old_password or not request.user.check_password(old_password):
                    return JsonResponse({"error": "旧密码错误"}, status=400)
                request.user.set_password(new_password)

            request.user.username = data.get("username", request.user.username)
            request.user.email = data.get("email", request.user.email)
            request.user.save()

            return JsonResponse({"message": "用户信息更新成功"}, status=200)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
@login_required
def modify_resume(request):
    """
    API: /api/modify_resume_and_generate_html/

    Method: POST

    Input:
        JSON body:
        {
            "resume_text": "用户输入的简历内容",
            "resume_file": 文件（二选一）
        }

    Output:
        JSON Response:
        {
            "html_content": "生成的 HTML 字符串"
        }

    Expected Behavior:
        - 接收简历文本或 PDF 文件
        - 解析 PDF 并提取文本（如果提供文件）
        - 通过 AI 进行优化
        - 解析 JSON Resume
        - 生成 HTML 并返回
    """
    if request.method == "POST":
        try:

            user_id = request.user.id  # 获取当前登录用户的 ID
            if not user_id:
                return JsonResponse({"error": "未登录用户"}, status=403)

            redis_client = request.redis_client
            if redis_client is None:
                return JsonResponse({"error": "Redis 连接失败"}, status=500)

            allowed, reason = check_rate_limit(user_id, redis_client)
            if not allowed:
                return JsonResponse({"error": reason}, status=429)

            resume_text = request.POST.get("resume_text", "").strip()
            resume_file = request.FILES.get("resume_file")
            theme = request.POST.get("theme", "flat").strip()
            customized_info = request.POST.get("")

            if not resume_text and resume_file:
                resume_text = parse_resume_file(resume_file)

            if not resume_text:
                return JsonResponse({"error": "请输入简历内容"}, status=400)

            # AI 处理简历
            modified_resume = modify_resume_with_chatgpt(resume_text, customized_info)
            json_resume = parse_modified_resume_to_json(modified_resume)
            if not json_resume:
                return JsonResponse({"error": "AI 解析简历失败"}, status=500)

            # 生成 HTML
            html_content = generate_html_from_json_resume(json_resume, theme)

            # 生成带模糊层的预览 HTML
            preview_html_content = f"""
                <html>
                <head>
                    <style>
                        .blur-overlay {{
                            position: fixed;
                            top: 0;
                            left: 0;
                            width: 100%;
                            height: 100%;
                            backdrop-filter: blur(2px);
                            background-color: rgba(255, 255, 255, 0.7);
                            z-index: 999;
                        }}
                    </style>
                </head>
                <body>
                    {html_content}
                    <div class="blur-overlay"></div>
                </body>
                </html>
                """

            # 生成带日期的文件路径
            current_date = datetime.utcnow().strftime("%Y/%m/%d")  # 按日期存储
            file_uuid = uuid.uuid4().hex
            file_name = f"resumes/{current_date}/{file_uuid}.html"
            preview_file_name = f"resumes/{current_date}/{file_uuid}_preview.html"
            json_file_name = f"resumes/{current_date}/{file_uuid}.json"

            temp_html_path = os.path.join("/tmp", file_name)  # 临时存储 HTML
            temp_preview_path = os.path.join("/tmp", preview_file_name)  # 预览 HTML
            temp_json_path = os.path.join("/tmp", json_file_name)  # JSON 文件路径

            # **确保目录存在**
            os.makedirs(os.path.dirname(temp_html_path), exist_ok=True)

            # **写入 HTML 文件**
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            with open(temp_preview_path, "w", encoding="utf-8") as f:
                f.write(preview_html_content)

            # **写入 JSON 文件**
            with open(temp_json_path, "w", encoding="utf-8") as f:
                json.dump(json_resume, f, ensure_ascii=False, indent=4)

            # **上传到 S3**
            s3_client.upload_file(temp_html_path, AWS_STORAGE_BUCKET_NAME, file_name,
                                  ExtraArgs={"ContentType": "text/html"})
            s3_client.upload_file(temp_preview_path, AWS_STORAGE_BUCKET_NAME, preview_file_name,
                                  ExtraArgs={"ContentType": "text/html"})
            s3_client.upload_file(temp_json_path, AWS_STORAGE_BUCKET_NAME, json_file_name,
                                  ExtraArgs={"ContentType": "application/json"})

            os.remove(temp_html_path)  # **删除临时文件**
            os.remove(temp_preview_path)  # **删除预览文件**
            os.remove(temp_json_path)

            html_url = f"{S3_BASE_URL}{file_name}"
            preview_html_url = f"{S3_BASE_URL}{preview_file_name}"
            json_url = f"{S3_BASE_URL}{json_file_name}"

            return JsonResponse({"html_url": html_url, "preview_html_url": preview_html_url, "json_resume":json_url, "theme":theme})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
@login_required
def download_pdf(request):
    """
    API: /api/download_pdf/

    Method: POST

    Input:
        JSON body:
        {
            "html_url": "简历 HTML url"
        }

    Output:
        JSON Response:
        {
            "pdf_url": "https://s3.amazonaws.com/your_bucket_name/xxx.pdf"
        }

    Expected Behavior:
        - 接收 HTML 内容
        - 转换 HTML → PDF
        - 存储 PDF 到 S3
        - 返回 PDF 下载 URL
    """
    # if request.method == "POST":
    #     try:
    #         html_url = request.POST.get("html_url", "").strip()
    #
    #         if not html_url:
    #             return JsonResponse({"error": "缺少 HTML URL"}, status=400)
    #
    #         # 下载 HTML 文件
    #         response = requests.get(html_url)
    #         if response.status_code != 200:
    #             return JsonResponse({"error": "无法下载 HTML 文件"}, status=400)
    #
    #         html_content = response.text  # 获取 HTML 内容
    #
    #         # 生成带日期的文件路径
    #         current_date = datetime.utcnow().strftime("%Y/%m/%d")  # 按日期存储
    #         pdf_key = f"resumes/{current_date}/{uuid.uuid4().hex}.pdf"
    #         temp_pdf_path = os.path.join("/tmp", pdf_key)
    #
    #         # 生成 PDF
    #         generate_pdf_from_html(html_content, temp_pdf_path)
    #
    #         # 上传 PDF 到 S3
    #         s3_client.upload_file(temp_pdf_path, AWS_STORAGE_BUCKET_NAME, pdf_key,
    #                               ExtraArgs={"ContentType": "application/pdf"})
    #
    #         os.remove(temp_pdf_path)  # 删除临时文件
    #
    #         pdf_url = f"{S3_BASE_URL}{pdf_key}"
    #         return JsonResponse({"pdf_url": pdf_url})
    #
    #     except Exception as e:
    #         return JsonResponse({"error": str(e)}, status=500)
    #
    # return JsonResponse({"error": "Invalid request method"}, status=405)
    # if request.method == "POST":
    #     try:
    #         json_resume_url = request.POST.get("json_resume", "").strip()  # S3 传来的 JSON Resume URL
    #         json_resume_url = json_resume_url.strip('"')
    #         theme = request.POST.get("theme", "flat").strip()
    #
    #         if not json_resume_url:
    #             return JsonResponse({"error": "缺少 JSON Resume 数据"}, status=400)
    #
    #         # 解析 S3 路径
    #         json_resume_key = json_resume_url.replace(S3_BASE_URL, "")  # 提取 S3 文件 Key
    #         temp_json = os.path.join(settings.BASE_DIR, "resume.json")
    #
    #         # 下载 JSON Resume 文件到本地
    #         s3_client.download_file(AWS_STORAGE_BUCKET_NAME, json_resume_key, temp_json)
    #
    #         # 读取 JSON 内容，确保是有效的 JSON 格式
    #         with open(temp_json, "r", encoding="utf-8") as f:
    #             json_resume = json.load(f)  # 确保 JSON 可用
    #
    #         # 生成 PDF 文件路径
    #         pdf_key = f"resume.pdf"
    #         temp_pdf = os.path.join(settings.BASE_DIR, "resume.pdf")  # 先获取目录路径
    #
    #         # 主题路径映射（保持不变）
    #         THEME_PATHS = {
    #             'flat': 'jsonresume-theme-flat',
    #             'kendall': 'jsonresume-theme-kendall',
    #             'macchiato': 'jsonresume-theme-macchiato',
    #             'relaxed': 'jsonresume-theme-relaxed',
    #             'stackoverflow': 'jsonresume-theme-stackoverflow',
    #             'professional': "./node_modules/jsonresume-theme-professional/build",
    #             'engineering': "./node_modules/jsonresume-theme-engineering"
    #         }
    #
    #         selected_theme_path = THEME_PATHS.get(theme, 'jsonresume-theme-flat')
    #         print(f"使用主题路径：{selected_theme_path}")
    #
    #         # 设置环境变量，确保 `resume-cli` 能找到 `node_modules`
    #         env = os.environ.copy()
    #         env["NODE_PATH"] = os.path.join(settings.BASE_DIR, "node_modules")
    #
    #         # 使用 `resume export` 生成 PDF
    #         cmd = [
    #             "resume", "export", temp_pdf,
    #             "--theme", selected_theme_path,
    #             "--format", "pdf",
    #             temp_json
    #         ]
    #
    #         try:
    #             print(f"执行命令: {' '.join(cmd)}")
    #
    #             result = subprocess.run(
    #                 cmd,
    #                 cwd=settings.BASE_DIR,
    #                 stdout=subprocess.PIPE,
    #                 stderr=subprocess.PIPE,
    #                 env=env,
    #                 check=True
    #             )
    #
    #             # **确保 PDF 生成**
    #             pdf_wait_time = 0
    #             max_wait_time = 20  # 最长等待 20 秒
    #             while not os.path.exists(temp_pdf) and pdf_wait_time < max_wait_time:
    #                 time.sleep(1)  # 每秒检查一次
    #                 pdf_wait_time += 1
    #
    #             if not os.path.exists(temp_pdf):
    #                 raise FileNotFoundError(f"resume export 失败，{max_wait_time} 秒后仍未生成 {temp_pdf}")
    #
    #             print(f"成功生成 PDF: {temp_pdf}，等待时间: {pdf_wait_time} 秒")
    #
    #         except subprocess.CalledProcessError as e:
    #             raise Exception(f"resume export 失败: {e.stderr.decode()}")
    #
    #         except Exception as e:
    #             raise Exception(f"未知错误: {str(e)}")
    #         # result = subprocess.run(cmd, cwd=settings.BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=30)
    #
    #         if result.returncode != 0:
    #             error_message = result.stderr.decode()
    #             raise Exception(f"resume CLI error: {error_message}")
    #
    #         # 上传 PDF 到 S3
    #         s3_client.upload_file(temp_pdf, AWS_STORAGE_BUCKET_NAME, pdf_key,
    #                               ExtraArgs={"ContentType": "application/pdf"})
    #
    #         # 清理临时文件
    #         os.remove(temp_json)
    #         os.remove(temp_pdf)
    #
    #         pdf_url = f"{S3_BASE_URL}{pdf_key}"
    #         return JsonResponse({"pdf_url": pdf_url})
    #
    #     except Exception as e:
    #         return JsonResponse({"error": str(e)}, status=500)
    #
    # return JsonResponse({"error": "Invalid request method"}, status=405)
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=405)

    try:
        json_resume_url = request.POST.get("json_resume", "").strip().strip('"')
        theme = request.POST.get("theme", "flat").strip()

        if not json_resume_url:
            return JsonResponse({"error": "缺少 JSON Resume 数据"}, status=400)

        # 解析 S3 路径
        json_resume_key = json_resume_url.replace(S3_BASE_URL, "")
        temp_json = os.path.join(settings.BASE_DIR, "resume.json")

        # 下载 JSON Resume 文件到本地
        s3_client.download_file(AWS_STORAGE_BUCKET_NAME, json_resume_key, temp_json)

        # 读取 JSON Resume 数据
        with open(temp_json, "r", encoding="utf-8") as f:
            json_resume = json.load(f)

        # 生成 PDF
        temp_pdf = generate_pdf_from_json_resume(json_resume, theme)

        # 生成带日期的文件路径
        current_date = datetime.utcnow().strftime("%Y/%m/%d")
        pdf_key = f"resumes/{current_date}/{uuid.uuid4().hex}.pdf"

        # 上传 PDF 到 S3
        s3_client.upload_file(temp_pdf, AWS_STORAGE_BUCKET_NAME, pdf_key, ExtraArgs={"ContentType": "application/pdf"})

        # 清理临时文件
        os.remove(temp_json)
        os.remove(temp_pdf)

        pdf_url = f"{S3_BASE_URL}{pdf_key}"
        return JsonResponse({"pdf_url": pdf_url})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
class AlipayViewSet(ModelViewSet):
    queryset = AlipayOrder.objects.all()
    serializer_class = AlipayOrderSerializer

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        order = self.get_object()
        url = generate_alipay_url(order.out_trade_no, order.total_amount)
        return Response({"pay_url": url})
@login_required
class WeChatViewSet(ModelViewSet):
    queryset = WeChatOrder.objects.all()
    serializer_class = WeChatOrderSerializer

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        order = self.get_object()
        qr_code = generate_wechat_qr(order.out_trade_no, order.total_fee)
        return Response({"qr_code": qr_code})
@login_required
class StripeViewSet(ModelViewSet):
    queryset = StripeOrder.objects.all()
    serializer_class = StripeOrderSerializer

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        order = self.get_object()
        charge = process_stripe_payment(order.charge_id, order.amount)
        return Response(charge)


class ExtractTextView(APIView):
    parser_classes = [JSONParser]  # 解析 application/json

    def post(self, request, *args, **kwargs):
        image_data_list = request.data.get("imageDataList", [])
        programming_language = request.data.get("language", "python")  # ✅ 这是编程语言，不影响 OCR

        if not image_data_list:
            return Response({"error": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)

        extracted_texts = []

        try:
            for image_base64 in image_data_list:
                # ✅ 解码 Base64 图片
                image_bytes = base64.b64decode(image_base64)
                image = Image.open(BytesIO(image_bytes))

                # ✅ 强制 OCR 解析语言为 "eng"（无论前端传什么）
                extracted_text = pytesseract.image_to_string(image, lang="eng")
                extracted_texts.append({
                    "code": extracted_text.strip(),  # 移除空白字符
                    "language": programming_language  # 保留前端传来的编程语言
                })

            return Response({"results": extracted_texts}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateCodeView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # ✅ 获取 "results" 作为 problem_info
            results = request.data.get("results", [])
            language = request.data.get("language", "python")

            # 确保 results 是一个列表
            if not isinstance(results, list) or not results:
                return Response({"error": "Invalid or missing 'results' list"}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ 只取 results 里的 code
            extracted_code = [item.get("code", "") for item in results]

            # 生成代码
            generated_code = self.leetcode_with_chatgpt(extracted_code, language)

            return Response(generated_code, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def leetcode_with_chatgpt(self, extracted_code_list, language):
        """调用 DeepSeek API 生成代码"""
        user_input = "\n".join(extracted_code_list)
        print("调用 Deepseek API 前，用户输入：", user_input)

        api_key = "sk-fa41fb37efaa4a64b126f7ad23456b9a"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        system_prompt = """你是一个精通算法的 LeetCode 选手，你的任务是优化代码并返回结构化信息。
       请按照以下 JSON 格式返回：
       {
           "code": "<优化后的代码>",
           "thoughts": "<优化的思路>",
           "time_complexity": "<时间复杂度分析>",
           "space_complexity": "<空间复杂度分析>"
       }"""

        user_prompt = f"请用 {language} 编程语言优化以下代码，并返回 **严格的 JSON 格式**（不包含 ```）：\n{user_input}"

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 5000
        }

        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
        print("DeepSeek API 返回状态码：", response.status_code)

        if response.status_code == 200:
            raw_response = response.json()
            generated_text = raw_response.get("choices", [{}])[0].get("message", {}).get("content", "")

            print("DeepSeek API 响应数据:", generated_text)

            # **✅ 解析 JSON，去掉可能的 ```json 代码块**
            try:
                cleaned_json = generated_text.strip("```json").strip("```").strip()
                parsed_data = json.loads(cleaned_json)  # **确保是 JSON 对象**

                # **✅ 处理 thoughts 字段，确保返回数组**
                if isinstance(parsed_data.get("thoughts"), str):
                    parsed_data["thoughts"] = parsed_data["thoughts"].split("。")  # 按句号拆分成数组
                    parsed_data["thoughts"] = [t.strip() for t in parsed_data["thoughts"] if t.strip()]  # 去除空字符串

                return parsed_data
            except Exception as e:
                print("⚠️ JSON 解析失败:", str(e))
                return {
                    "code": "解析失败",
                    "thoughts": ["DeepSeek 返回的数据无法解析，请检查格式"],
                    "time_complexity": "未知",
                    "space_complexity": "未知"
                }
        else:
            raise Exception(f"DeepSeek API 请求失败，状态码：{response.status_code}，响应：{response.text}")




class DebugView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            # ✅ 获取调试所需的参数
            image_data_list = request.data.get("imageDataList", [])
            language = request.data.get("language", "python")

            # 确保至少有截图
            if not isinstance(image_data_list, list) or not image_data_list:
                return Response({"error": "Invalid or missing 'imageDataList'"}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ 从截图中提取代码
            extracted_code_list = self.extract_code_from_images(image_data_list)

            if not extracted_code_list:
                return Response({"error": "无法从截图中提取代码"}, status=status.HTTP_400_BAD_REQUEST)

            # ✅ 生成调试后的优化代码
            debugged_code = self.leetcode_with_chatgpt(extracted_code_list, language)

            return Response(debugged_code, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def extract_code_from_images(self, image_data_list):
        """使用 OCR 解析图片，提取代码"""
        extracted_code_list = []

        for base64_image in image_data_list:
            try:
                # ✅ 解析 Base64 图片
                image_data = base64.b64decode(base64_image)
                image = Image.open(BytesIO(image_data))

                # ✅ 使用 Tesseract OCR 提取文本
                extracted_text = pytesseract.image_to_string(image)

                # ✅ 过滤出代码部分（只保留代码相关内容）
                extracted_code = self.clean_extracted_text(extracted_text)

                if extracted_code:
                    extracted_code_list.append(extracted_code)

            except Exception as e:
                print(f"⚠️ 图片解析失败: {e}")
                continue  # 跳过解析失败的图片

        return extracted_code_list

    def clean_extracted_text(self, text):
        """对 OCR 提取的文本进行处理，保留代码部分"""
        lines = text.split("\n")
        code_lines = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#") or ">>> " in line:  # 忽略注释和 `>>>`
                continue
            if "import " in line or "=" in line or "def " in line or "class " in line or "(" in line:
                code_lines.append(line)

        return "\n".join(code_lines)

    def leetcode_with_chatgpt(self, extracted_code_list, language):
        """调用 DeepSeek API 进行代码优化调试"""
        user_input = "\n".join(extracted_code_list)
        print("调用 DeepSeek API 前，用户输入：", user_input)

        api_key = "sk-fa41fb37efaa4a64b126f7ad23456b9a"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        system_prompt = """你是一个精通算法的 LeetCode 选手，我给你提供了老代码,现在需要你根据报错信息和老代码进行修改获取出新的代码. thoughts 写出你的改动部分,new code 写出新的代码。
        请按照以下 JSON 格式返回：
        {
            "new_code": "<优化后的代码>",
            "thoughts": "<优化的思路>",
            "time_complexity": "<时间复杂度分析>",
            "space_complexity": "<空间复杂度分析>"
        }"""

        user_prompt = f"请用 {language} 编程语言优化以下代码，并返回 **严格的 JSON 格式**（不包含 ```）：\n{user_input}"

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "temperature": 0.7,
            "max_tokens": 5000
        }

        response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
        print("DeepSeek API 返回状态码：", response.status_code)

        if response.status_code == 200:
            raw_response = response.json()
            generated_text = raw_response.get("choices", [{}])[0].get("message", {}).get("content", "")

            print("DeepSeek API 响应数据:", generated_text)

            # **✅ 解析 JSON，去掉可能的 ```json 代码块**
            try:
                cleaned_json = generated_text.strip("```json").strip("```").strip()
                parsed_data = json.loads(cleaned_json)  # **确保是 JSON 对象**

                # **✅ 处理 thoughts 字段，确保返回数组**
                if isinstance(parsed_data.get("thoughts"), str):
                    parsed_data["thoughts"] = parsed_data["thoughts"].split("。")  # 按句号拆分成数组
                    parsed_data["thoughts"] = [t.strip() for t in parsed_data["thoughts"] if t.strip()]  # 去除空字符串

                return parsed_data
            except Exception as e:
                print("⚠️ JSON 解析失败:", str(e))
                return {
                    "new_code": "解析失败",
                    "thoughts": ["DeepSeek 返回的数据无法解析，请检查格式"],
                    "time_complexity": "未知",
                    "space_complexity": "未知"
                }
        else:
            raise Exception(f"DeepSeek API 请求失败，状态码：{response.status_code}，响应：{response.text}")
