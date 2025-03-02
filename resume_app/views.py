import json
import subprocess
import os
import requests
import asyncio
import re


from openai import OpenAI
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.template.loader import render_to_string

from playwright.async_api import async_playwright
from pdf2docx import Converter  # 新增 pdf2docx

from .forms import ResumeUploadForm


# =======================
#  1. PROMPT & API 调用
# =======================

def generate_resume_prompt(user_input):
    """
    根据用户提供的简历信息，生成用于 ChatGPT 的提示，要求输出完整 JSON Resume。
    """
    prompt = f'''
    你是一位专业的简历生成助手，专门帮助用户撰写符合国际标准的 JSON Resume 格式的简历。请根据用户提供的信息，生成一份高质量的简历。你的目标是确保简历具有清晰的结构、强有力的描述，并能有效突出候选人的专业技能和成就。

    要求：
    1. **严格遵循 JSON Resume 结构（见下方示例），仅输出 JSON，不要添加任何额外的解释或说明。**
    2. 基于 STAR 法则优化工作经历（Situation, Task, Action, Result）：
        * 开头总结核心成就（加粗）
        * 详细描述候选人在该岗位上的任务
        * 具体说明候选人的行动
        * 量化成果，展示影响力
    3. 提升内容质量，深挖用户的职业成就：
        * 如果用户的描述较为简单，请主动补充合理的背景信息，使内容更丰富、更有说服力。
        * 例如，如果用户仅提供“优化搜索速度”，应改写为：“优化搜索性能：通过集成 DynamoDB 缓存和 InfraDB API，将搜索速度提升 2 倍，加载时间减少 50%。”
    4. 确保简历语言专业、简洁、富有冲击力：
        * 使用行业标准术语，避免冗长的描述。
        * 使用主动动词（e.g., Led, Optimized, Developed, Spearheaded）。
        * 量化数据（e.g., 提高转化率 30%，减少错误率 50%）。
    5. 根据用户输入语言决定模型输出语言
        * 英文使用英文,中文就使用中文
    6. 确保简历内容为一页
    7. 注意profiles这个字段需要有,如果用户没有输入可以留空 
  

    严格遵循如下模板格式如下：
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
    print("调用 Deepseek API 前，用户输入：", user_input)

    api_key = "sk-fa41fb37efaa4a64b126f7ad23456b9a"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "deepseek-chat",  # 使用 DeepSeek-V3 模型，需要传入 deepseek-chat
        "messages": [
            {"role": "system", "content": "你是一个专业的简历修改助手。"},
            {"role": "user", "content": generate_resume_prompt(user_input)}
        ],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 3000
    }
    
    response = requests.post("https://api.deepseek.com/chat/completions", headers=headers, json=data)
    print("DeepSeek API 返回状态码：", response.status_code)
    if response.status_code == 200:
        result = response.json()
        modified_resume = result["choices"][0]["message"]["content"]
        print("DeepSeek 返回内容：", modified_resume[:200])
        return modified_resume
    else:
        raise Exception(f"DeepSeek API 请求失败，状态码：{response.status_code}，响应：{response.text}")

    # client = OpenAI(api_key="sk-fa41fb37efaa4a64b126f7ad23456b9a", base_url="https://api.deepseek.com")

    # response = client.chat.completions.create(
    #     model="deepseek-chat",
    #     messages=[
    #         {"role": "system", "content": "你是一个专业的简历修改助手。"},
    #         {"role": "user", "content": generate_resume_prompt(user_input)}
    #     ],
    #     stream=False
    # )
    # try:
    #     # 尝试直接从 response 中提取修改后的简历内容
    #     modified_resume = response.choices[0].message.content
    #     print("Deepseek is successful", modified_resume)
    #     print("Deepseek 返回内容：", modified_resume[:200])
    #     return modified_resume
    # except Exception as e:
    #     # 捕获异常并抛出带有错误信息的异常
    #     raise Exception(f"Deepseek API 请求失败，错误信息：{e}")

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
        print("PDF 解析后的文本长度：", len(text))
        return text
    except Exception as e:
        raise Exception("无法解析上传的文件：" + str(e))


def parse_modified_resume_to_json(modified_resume_text):
    """
    尝试将 ChatGPT 返回的字符串直接解析成 JSON。
    如果无法解析，则返回空字典，避免崩溃。
    """
    # try:
    #     json_data = json.loads(modified_resume_text)
    #     return json_data
    # except Exception:
    #     return {}
    try:
        return json.loads(modified_resume_text)
    except Exception:
        pass

        # 如果解析失败，可能是因为包含 Markdown 的 ``` 或 ```json 标记
        # 移除这些标记
    cleaned_text = re.sub(r"^```(?:json)?\s*", "", modified_resume_text.strip())
    cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

    try:
        return json.loads(cleaned_text)
    except Exception as e:
        print("最终解析失败:", e)
        return {}


# =======================
#  3. 生成 HTML & PDF（使用 Playwright）
# =======================

async def _generate_pdf_from_html(html_content, output_path):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.set_content(html_content, wait_until="networkidle")
        await page.pdf(path=output_path, format="A4", print_background=True)
        await browser.close()


def generate_pdf_from_html(html_content, output_path):
    asyncio.run(_generate_pdf_from_html(html_content, output_path))


def generate_html_from_json_resume(json_resume, theme="flat"):
    """
    调用 resume-cli 将 JSON Resume 转换为 HTML。
    支持 'flat' 与 'professional' 两种主题。
    """
    temp_json = os.path.join(settings.BASE_DIR, "resume.json")
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(json_resume, f, ensure_ascii=False, indent=2)

    temp_html = os.path.join(settings.BASE_DIR, "temp_resume.html")

    THEME_PATHS = {
        'flat': 'jsonresume-theme-flat',
        'professional': os.path.join(settings.BASE_DIR, "node_modules", "jsonresume-theme-professional", "build")
    }
    selected_theme_path = THEME_PATHS.get(theme, 'jsonresume-theme-flat')
    print("使用主题路径：", selected_theme_path)

    cmd = [
        "resume", "export", temp_html,
        "--theme", selected_theme_path,
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
    将生成的 HTML 内容写入到 MEDIA_ROOT 下的 preview_resume.html，
    返回一个可在模板中使用的 URL。
    """
    preview_path = os.path.join(settings.MEDIA_ROOT, "preview_resume.html")
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    preview_url = settings.MEDIA_URL + "preview_resume.html"
    return preview_url


# =======================
#  4. pdf2docx 转换函数
# =======================

def convert_pdf_to_docx(pdf_path, docx_path):
    """
    使用 pdf2docx 将 PDF 转换为 DOCX。
    """
    cv = Converter(pdf_path)
    # start=0 表示从第一页开始转换，end=None 表示转换全部页面
    cv.convert(docx_path, start=0, end=None)
    cv.close()


# =======================
#  5. 视图函数
# =======================

def resume_modify_view(request):
    """
    用户提交简历文本或 PDF 后：
    1. 解析输入
    2. 调用 ChatGPT 得到修改后的简历字符串
    3. 尝试解析为 JSON Resume 格式
    4. 将结果写入 session，重定向到结果页
    """
    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            resume_text = form.cleaned_data.get("resume_text", "").strip()
            resume_file = form.cleaned_data.get("resume_file")
            resume_theme = form.cleaned_data.get("theme", "flat")
            if not resume_text and resume_file:
                resume_text = parse_resume_file(resume_file)
            if not resume_text:
                return render(request, "resume_form.html", {"form": form, "error": "请输入或上传简历内容"})
            try:
                modified_resume = modify_resume_with_chatgpt(resume_text)
                json_resume = parse_modified_resume_to_json(modified_resume)
                request.session["modified_resume"] = modified_resume
                request.session["json_resume"] = json_resume
                request.session["selected_theme"] = resume_theme
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
    1. 从 session 获取 JSON Resume 与修改后的文本
    2. 根据所选主题生成 HTML，写入 media/preview_resume.html
    3. 通过 iframe 预览，同时提供下载 PDF 和 Word 按钮
    """
    modified_resume = request.session.get("modified_resume")
    json_resume = request.session.get("json_resume")
    selected_theme = request.session.get("selected_theme", "flat")
    if not (modified_resume and json_resume):
        return redirect("resume_form")
    try:
        html_content = generate_html_from_json_resume(json_resume, theme=selected_theme)
        print("生成的 HTML 内容长度：", len(html_content))
        preview_url = preview_resume_and_save(html_content)
        context = {
            "modified_resume": modified_resume,
            "preview_url": preview_url
        }
        return render(request, "resume_result.html", context)
    except Exception as e:
        return HttpResponse(f"生成预览出错：{e}", status=500)


def download_pdf_view(request):
    """
    PDF 下载视图：
    1. 从 session 获取 JSON Resume
    2. 根据所选主题生成 HTML
    3. 使用 Playwright 将 HTML 转换为 PDF
    4. 返回 PDF 文件作为附件
    """
    json_resume = request.session.get("json_resume")
    selected_theme = request.session.get("selected_theme", "flat")
    if not json_resume:
        return redirect("resume_form")
    try:
        html_content = generate_html_from_json_resume(json_resume, theme=selected_theme)
        output_pdf = os.path.join(settings.BASE_DIR, "output_resume.pdf")
        generate_pdf_from_html(html_content, output_pdf)
        with open(output_pdf, "rb") as f:
            pdf_data = f.read()
        os.remove(output_pdf)
    except Exception as e:
        return HttpResponse(f"生成 PDF 时出错：{e}", status=500)

    response = HttpResponse(pdf_data, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="modified_resume.pdf"'
    return response


def download_word_view(request):
    """
    Word 下载视图：
    1. 从 session 获取 JSON Resume
    2. 根据所选主题生成 HTML
    3. 使用 Playwright 生成 PDF，再通过 pdf2docx 将 PDF 转换为 Word (docx)
    4. 返回 Word 文件作为附件
    """
    json_resume = request.session.get("json_resume")
    selected_theme = request.session.get("selected_theme", "flat")
    if not json_resume:
        return redirect("resume_form")
    try:
        html_content = generate_html_from_json_resume(json_resume, theme=selected_theme)
        temp_pdf = os.path.join(settings.BASE_DIR, "temp_resume.pdf")
        output_word = os.path.join(settings.BASE_DIR, "output_resume.docx")

        # 先生成 PDF 文件
        generate_pdf_from_html(html_content, temp_pdf)
        # 使用 pdf2docx 将 PDF 转换为 DOCX
        convert_pdf_to_docx(temp_pdf, output_word)

        with open(output_word, "rb") as f:
            word_data = f.read()
        # 清理临时文件
        os.remove(temp_pdf)
        os.remove(output_word)
    except Exception as e:
        return HttpResponse(f"生成 Word 时出错：{e}", status=500)

    response = HttpResponse(word_data,
                            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    response["Content-Disposition"] = 'attachment; filename="modified_resume.docx"'
    return response
