import json
import subprocess
import os
import requests

from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML

from .forms import ResumeUploadForm

# =======================
#  1. PROMPT & API 调用
# =======================

def generate_resume_prompt(user_input):
    """
    根据用户提供的简历信息，生成用于 ChatGPT 的提示，要求输出完整 JSON Resume。
    """
    prompt = f'''
你是一位专业的简历生成助手。请根据下面的用户提供信息，生成一份符合以下 JSON Resume 模板格式的简历。
输出的 JSON 必须严格遵循下面的格式，不要添加任何额外的解释或说明。如果某个字段没有数据，就不要那个字段。

模板格式如下：
{{
  "basics": {{
    "name": "John Doe",
    "label": "Programmer",
    "image": "",
    "email": "john@gmail.com",
    "phone": "(912) 555-4321",
    "url": "https://johndoe.com",
    "summary": "A summary of John Doe…",
    "location": {{
      "address": "2712 Broadway St",
      "postalCode": "CA 94115",
      "city": "San Francisco",
      "countryCode": "US",
      "region": "California"
    }},
    "profiles": [{{
      "network": "Twitter",
      "username": "john",
      "url": "https://twitter.com/john"
    }}]
  }},
  "work": [{{
    "name": "Company",
    "position": "President",
    "url": "https://company.com",
    "startDate": "2013-01-01",
    "endDate": "2014-01-01",
    "summary": "Description…",
    "highlights": [
      "Started the company"
    ]
  }}],
  "volunteer": [{{
    "organization": "Organization",
    "position": "Volunteer",
    "url": "https://organization.com/",
    "startDate": "2012-01-01",
    "endDate": "2013-01-01",
    "summary": "Description…",
    "highlights": [
      "Awarded 'Volunteer of the Month'"
    ]
  }}],
  "education": [{{
    "institution": "University",
    "url": "https://institution.com/",
    "area": "Software Development",
    "studyType": "Bachelor",
    "startDate": "2011-01-01",
    "endDate": "2013-01-01",
    "score": "4.0",
    "courses": [
      "DB1101 - Basic SQL"
    ]
  }}],
  "awards": [{{
    "title": "Award",
    "date": "2014-11-01",
    "awarder": "Company",
    "summary": "There is no spoon."
  }}],
  "certificates": [{{
    "name": "Certificate",
    "date": "2021-11-07",
    "issuer": "Company",
    "url": "https://certificate.com"
  }}],
  "publications": [{{
    "name": "Publication",
    "publisher": "Company",
    "releaseDate": "2014-10-01",
    "url": "https://publication.com",
    "summary": "Description…"
  }}],
  "skills": [{{
    "name": "Web Development",
    "level": "Master",
    "keywords": [
      "HTML",
      "CSS",
      "JavaScript"
    ]
  }}],
  "languages": [{{
    "language": "English",
    "fluency": "Native speaker"
  }}],
  "interests": [{{
    "name": "Wildlife",
    "keywords": [
      "Ferrets",
      "Unicorns"
    ]
  }}],
  "references": [{{
    "name": "Jane Doe",
    "reference": "Reference…"
  }}],
  "projects": [{{
    "name": "Project",
    "startDate": "2019-01-01",
    "endDate": "2021-01-01",
    "description": "Description...",
    "highlights": [
      "Won award at AIHacks 2016"
    ],
    "url": "https://project.com/"
  }}]
}}

下面是用户提供的简历信息：
{user_input}
    '''
    return prompt


def modify_resume_with_chatgpt(user_input):
    """
    调用 ChatGPT，使用上面的 prompt，将用户的文本转换为符合 JSON Resume 结构的字符串。
    """
    api_key = "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"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "你是一个专业的简历修改助手。"},
            {"role": "user", "content": generate_resume_prompt(user_input)}
        ],
        "temperature": 0.7,
        "max_tokens": 3000
    }
    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        modified_resume = result["choices"][0]["message"]["content"]
        return modified_resume
    else:
        raise Exception(f"ChatGPT API 请求失败，状态码：{response.status_code}，响应：{response.text}")

# =======================
#  2. 解析 PDF & JSON
# =======================

def parse_resume_file(file):
    """
    读取上传的 PDF 文件，使用 PyPDF2 提取文本并返回。
    """
    import PyPDF2
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        raise Exception("无法解析上传的文件：" + str(e))


def parse_modified_resume_to_json(modified_resume_text):
    """
    尝试将 ChatGPT 返回的字符串直接解析成 JSON。
    如果无法解析，则返回空字典，避免崩溃。
    """
    try:
        json_data = json.loads(modified_resume_text)
        return json_data
    except Exception:
        # 如果 ChatGPT 返回了一些额外说明文字，则这里会报错。
        # 也可改进 prompt 以强制其只输出 JSON。
        return {}

# =======================
#  3. 生成 HTML & PDF
# =======================

def generate_html_from_json_resume(json_resume,theme='flat'):
    """
    调用 resume-cli 将 JSON Resume 转换为 HTML。
    这里使用 jsonresume-theme-flat，你也可切换到其他主题（若已编译）。
    """
    temp_json = os.path.join(settings.BASE_DIR, "resume.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(json_resume, f, ensure_ascii=False, indent=2)

    temp_html = os.path.join(settings.BASE_DIR, "temp_resume.html")

    THEME_PATHS = {
        'flat': 'jsonresume-theme-flat',  # npm 官方包
        'professional': os.path.join(
            settings.BASE_DIR,
            "node_modules",
            "jsonresume-theme-professional",
            'build'
        ),
    # 别的主题
    }

    selected_theme_path = THEME_PATHS.get(theme, 'jsonresume-theme-flat')

    cmd = [
        "resume", "export", temp_html,
        "--theme", selected_theme_path,  # 这里可换成编译后的 professional 主题路径
        "--format", "html",
        temp_json
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        error_message = result.stderr.decode()
        raise Exception(f"resume CLI error: {error_message}")

    with open(temp_html, "r", encoding="utf-8") as f:
        html_content = f.read()

    os.remove(temp_json)
    os.remove(temp_html)
    return html_content


def preview_resume_and_save(html_content):
    """
    将 HTML 内容写入到 MEDIA_ROOT 下的 preview_resume.html，然后返回可在浏览器中访问的 URL。
    """
    preview_path = os.path.join(settings.MEDIA_ROOT, "preview_resume.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Django 媒体访问地址
    preview_url = settings.MEDIA_URL + "preview_resume.html"
    return preview_url


# =======================
#  4. 视图函数
# =======================

def resume_modify_view(request):
    """
    用户提交简历文本或 PDF 后：
    1. 解析输入
    2. 调用 ChatGPT 得到字符串
    3. 转为 JSON
    4. 写入 session
    5. 重定向到 result
    """
    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # 获取输入
            resume_text = form.cleaned_data.get("resume_text", "").strip()
            resume_file = form.cleaned_data.get("resume_file")
            resume_theme = form.cleaned_data.get("theme")
            # 若没有文本但有文件，则解析 PDF
            if not resume_text and resume_file:
                resume_text = parse_resume_file(resume_file)
            if not resume_text:
                return render(request, "resume_form.html", {"form": form, "error": "请输入或上传简历内容"})

            try:
                # 调用 ChatGPT
                modified_resume = modify_resume_with_chatgpt(resume_text)
                json_resume = parse_modified_resume_to_json(modified_resume)

                # 将结果放入 session
                request.session["modified_resume"] = modified_resume
                request.session["json_resume"] = json_resume
                request.session["selected_theme"] = resume_theme

                # 重定向到结果页
                return redirect("resume_result")
            except Exception as e:
                return render(request, "resume_form.html", {"form": form, "error": str(e)})
        else:
            return render(request, "resume_form.html", {"form": form})
    else:
        form = ResumeUploadForm()
        return render(request, "resume_form.html", {"form": form})


def resume_result_view(request):
    """
    结果页面：
    1. 从 session 取 JSON Resume
    2. 生成 HTML 并写入 media/preview_resume.html
    3. iframe 预览
    4. 提供下载按钮指向 download_pdf_view
    """
    modified_resume = request.session.get("modified_resume")
    json_resume = request.session.get("json_resume")
    theme = request.session.get("selected_theme", "flat")
    if not (modified_resume and json_resume):
        return redirect("resume_form")

    try:
        # 生成 HTML
        html_content = generate_html_from_json_resume(json_resume,theme=theme)
        # 写入 preview_resume.html 并获取访问 URL
        preview_url = preview_resume_and_save(html_content)

        return render(request, "resume_result.html", {
            "modified_resume": modified_resume,
            "preview_url": preview_url
        })
    except Exception as e:
        return HttpResponse(f"生成预览出错：{e}", status=500)


def download_pdf_view(request):
    """
    提供下载 PDF 的视图：
    1. 从 session 获取 JSON
    2. 生成 HTML
    3. 用 WeasyPrint 转 PDF 并返回下载
    """
    json_resume = request.session.get("json_resume")
    theme = request.session.get("selected_theme", "flat")
    if not json_resume:
        return redirect("resume_form")
    try:
        html_content = generate_html_from_json_resume(json_resume,theme=theme)
        pdf = HTML(string=html_content).write_pdf()
    except Exception as e:
        return HttpResponse(f"生成 PDF 时出错：{e}", status=500)

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="modified_resume.pdf"'
    return response
