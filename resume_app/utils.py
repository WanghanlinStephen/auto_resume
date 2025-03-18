import subprocess
import requests
import asyncio
import re
from playwright.async_api import async_playwright
from pdf2docx import Converter  # 新增 pdf2docx
import time
import json
import os
import datetime
import redis
from django.conf import settings

def generate_resume_prompt(user_input,customized_info):
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
    下面是用户提供的客制化重点:
    {customized_info}
    '''
    return prompt


def modify_resume_with_chatgpt(user_input, customized_info):
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
            {"role": "user", "content": generate_resume_prompt(user_input,customized_info)}
        ],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 5000
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
    try:
        return json.loads(modified_resume_text)
    except Exception:
        pass

    cleaned_text = re.sub(r"^```(?:json)?\s*", "", modified_resume_text.strip())
    cleaned_text = re.sub(r"\s*```$", "", cleaned_text)

    try:
        return json.loads(cleaned_text)
    except Exception as e:
        print("最终解析失败:", e)
        return {}


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
        'kendall': 'jsonresume-theme-kendall',
        'macchiato': 'jsonresume-theme-macchiato',
        'relaxed': 'jsonresume-theme-relaxed',
        'stackoverflow': 'jsonresume-theme-stackoverflow',
        'professional': os.path.join(settings.BASE_DIR, "node_modules", "jsonresume-theme-professional", "build"),
        'engineering' : os.path.join(settings.BASE_DIR, "node_modules", "jsonresume-theme-engineering")
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


def generate_pdf_from_json_resume(json_resume, theme="flat"):
    """
    根据 JSON Resume 生成 PDF 文件
    """
    THEME_PATHS = {
        'flat': 'jsonresume-theme-flat',
        'kendall': 'jsonresume-theme-kendall',
        'macchiato': 'jsonresume-theme-macchiato',
        'relaxed': 'jsonresume-theme-relaxed',
        'stackoverflow': 'jsonresume-theme-stackoverflow',
        'professional': "./node_modules/jsonresume-theme-professional/build",
        'engineering': "./node_modules/jsonresume-theme-engineering"
    }
    selected_theme_path = THEME_PATHS.get(theme, 'jsonresume-theme-flat')
    print(f"使用主题路径：{selected_theme_path}")

    temp_json = os.path.join(settings.BASE_DIR, "resume.json")
    temp_pdf = os.path.join(settings.BASE_DIR, "resume.pdf")

    # 保存 JSON Resume 到临时文件
    with open(temp_json, "w", encoding="utf-8") as f:
        json.dump(json_resume, f, ensure_ascii=False, indent=4)

    # 设置环境变量，确保 `resume-cli` 能找到 `node_modules`
    env = os.environ.copy()
    env["NODE_PATH"] = os.path.join(settings.BASE_DIR, "node_modules")

    # 使用 `resume export` 生成 PDF
    cmd = [
        "resume", "export", temp_pdf,
        "--theme", selected_theme_path,
        "--format", "pdf",
        temp_json
    ]

    try:
        print(f"执行命令: {' '.join(cmd)}")
        subprocess.run(cmd, cwd=settings.BASE_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=True)

        # 确保 PDF 生成
        pdf_wait_time = 0
        max_wait_time = 20  # 最长等待 20 秒
        while not os.path.exists(temp_pdf) and pdf_wait_time < max_wait_time:
            time.sleep(1)
            pdf_wait_time += 1

        if not os.path.exists(temp_pdf):
            raise FileNotFoundError(f"resume export 失败，{max_wait_time} 秒后仍未生成 {temp_pdf}")

        print(f"成功生成 PDF: {temp_pdf}，等待时间: {pdf_wait_time} 秒")

    except subprocess.CalledProcessError as e:
        raise Exception(f"resume export 失败: {e.stderr.decode()}")

    except Exception as e:
        raise Exception(f"未知错误: {str(e)}")

    return temp_pdf
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


def convert_pdf_to_docx(pdf_path, docx_path):
    """
    使用 pdf2docx 将 PDF 转换为 DOCX。
    """
    cv = Converter(pdf_path)
    # start=0 表示从第一页开始转换，end=None 表示转换全部页面
    cv.convert(docx_path, start=0, end=None)
    cv.close()


# 限流配置（可修改）
RATE_LIMIT_HOURLY = settings.RATE_LIMIT_HOURLY if hasattr(settings, "RATE_LIMIT_HOURLY") else 10
RATE_LIMIT_DAILY = settings.RATE_LIMIT_DAILY if hasattr(settings, "RATE_LIMIT_DAILY") else 30

def check_rate_limit(user_id, redis_client):
    """检查用户的限流情况"""
    current_hour = datetime.datetime.utcnow().strftime("%Y-%m-%d %H")
    current_day = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    hourly_key = f"user:{user_id}:requests:{current_hour}"
    daily_key = f"user:{user_id}:requests:{current_day}"


    # 获取当前请求次数
    hourly_requests = int(redis_client.get(hourly_key) or 0)
    daily_requests = int(redis_client.get(daily_key) or 0)

    # 如果超过限流，返回 False
    if hourly_requests >= RATE_LIMIT_HOURLY:
        return False, f"已达到每小时请求限制 - {RATE_LIMIT_HOURLY}/hour"
    if daily_requests >= RATE_LIMIT_DAILY:
        return False, f"已达到每日请求限制 - {RATE_LIMIT_DAILY}/day"

    # 更新 Redis 计数
    redis_client.incr(hourly_key, 1)
    redis_client.incr(daily_key, 1)

    # 设置过期时间（确保 key 自动过期）
    redis_client.expire(hourly_key, 3600)  # 1 小时
    redis_client.expire(daily_key, 86400)  # 24 小时

    return True, ""