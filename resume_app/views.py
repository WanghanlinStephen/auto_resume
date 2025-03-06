
import requests
from datetime import datetime
import uuid
from .aws_config import s3_client, AWS_STORAGE_BUCKET_NAME, S3_BASE_URL
import os
from .utils import generate_pdf_from_html,generate_html_from_json_resume,modify_resume_with_chatgpt,parse_resume_file,parse_modified_resume_to_json
from django.contrib.auth.models import User
import jwt
import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib.auth import authenticate
from django.conf import settings

SECRET_KEY = settings.SECRET_KEY

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

        # **✅ 直接生成 JWT Token**
        token = jwt.encode({"id": user.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)}, SECRET_KEY, algorithm="HS256")

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
            token = jwt.encode({"id": user.id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=1)},
                               SECRET_KEY, algorithm="HS256")
            return JsonResponse({"token": token})
        return JsonResponse({"error": "用户名或密码错误"}, status=400)

@csrf_exempt
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
    # if request.method == "POST":
    #     try:
    #         resume_text = request.POST.get("resume_text", "").strip()
    #         resume_file = request.FILES.get("resume_file")
    #         theme = request.POST.get("theme","flat").strip()
    #         customized_info = request.POST.get("")
    #
    #         if not resume_text and resume_file:
    #             resume_text = parse_resume_file(resume_file)
    #
    #         if not resume_text:
    #             return JsonResponse({"error": "请输入简历内容"}, status=400)
    #
    #         # AI 处理简历
    #         modified_resume = modify_resume_with_chatgpt(resume_text,customized_info)
    #         json_resume = parse_modified_resume_to_json(modified_resume)
    #         if not json_resume:
    #             return JsonResponse({"error": "AI 解析简历失败"}, status=500)
    #
    #         # 生成 HTML
    #         html_content = generate_html_from_json_resume(json_resume,theme)
    #
    #         # 生成带日期的文件路径
    #         current_date = datetime.utcnow().strftime("%Y/%m/%d")  # 按日期存储
    #         file_name = f"resumes/{current_date}/{uuid.uuid4().hex}.html"
    #         temp_html_path = os.path.join("/tmp", file_name)  # 临时存储 HTML
    #
    #         # **确保目录存在**
    #         os.makedirs(os.path.dirname(temp_html_path), exist_ok=True)
    #
    #         # **写入 HTML 文件**
    #         with open(temp_html_path, "w", encoding="utf-8") as f:
    #             f.write(html_content)
    #
    #         # **上传到 S3**
    #         s3_client.upload_file(temp_html_path, AWS_STORAGE_BUCKET_NAME, file_name,
    #                               ExtraArgs={"ContentType": "text/html"})
    #
    #         os.remove(temp_html_path)  # **删除临时文件**
    #
    #         html_url = f"{S3_BASE_URL}{file_name}"
    #         return JsonResponse({"html_url": html_url})
    #
    #     except Exception as e:
    #         return JsonResponse({"error": str(e)}, status=500)
    #
    # return JsonResponse({"error": "Invalid request method"}, status=405)

    if request.method == "POST":
        try:
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

            temp_html_path = os.path.join("/tmp", file_name)  # 临时存储 HTML
            temp_preview_path = os.path.join("/tmp", preview_file_name)  # 预览 HTML

            # **确保目录存在**
            os.makedirs(os.path.dirname(temp_html_path), exist_ok=True)

            # **写入 HTML 文件**
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            with open(temp_preview_path, "w", encoding="utf-8") as f:
                f.write(preview_html_content)

            # **上传到 S3**
            s3_client.upload_file(temp_html_path, AWS_STORAGE_BUCKET_NAME, file_name,
                                  ExtraArgs={"ContentType": "text/html"})
            s3_client.upload_file(temp_preview_path, AWS_STORAGE_BUCKET_NAME, preview_file_name,
                                  ExtraArgs={"ContentType": "text/html"})

            os.remove(temp_html_path)  # **删除临时文件**
            os.remove(temp_preview_path)  # **删除预览文件**

            html_url = f"{S3_BASE_URL}{file_name}"
            preview_html_url = f"{S3_BASE_URL}{preview_file_name}"

            return JsonResponse({"html_url": html_url, "preview_html_url": preview_html_url})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

@csrf_exempt
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
    if request.method == "POST":
        try:
            html_url = request.POST.get("html_url", "").strip()

            if not html_url:
                return JsonResponse({"error": "缺少 HTML URL"}, status=400)

            # 下载 HTML 文件
            response = requests.get(html_url)
            if response.status_code != 200:
                return JsonResponse({"error": "无法下载 HTML 文件"}, status=400)

            html_content = response.text  # 获取 HTML 内容

            # 生成带日期的文件路径
            current_date = datetime.utcnow().strftime("%Y/%m/%d")  # 按日期存储
            pdf_key = f"resumes/{current_date}/{uuid.uuid4().hex}.pdf"
            temp_pdf_path = os.path.join("/tmp", pdf_key)

            # 生成 PDF
            generate_pdf_from_html(html_content, temp_pdf_path)

            # 上传 PDF 到 S3
            s3_client.upload_file(temp_pdf_path, AWS_STORAGE_BUCKET_NAME, pdf_key,
                                  ExtraArgs={"ContentType": "application/pdf"})

            os.remove(temp_pdf_path)  # 删除临时文件

            pdf_url = f"{S3_BASE_URL}{pdf_key}"
            return JsonResponse({"pdf_url": pdf_url})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request method"}, status=405)

