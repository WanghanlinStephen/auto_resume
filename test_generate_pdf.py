import json
import os
import subprocess
from weasyprint import HTML

def generate_pdf_from_resume_json():
    # 定义 JSON Resume 数据（请根据需要修改）
    resume_json = {
      "basics": {
        "name": "Hanlin(Stephen) Wang",
        "label": "Software Engineer",
        "image": "",
        "email": "WangHanlinStephen@outlook.com",
        "phone": "(872) 271-5605",
        "url": "https://www.linkedin.com/in/wang-hanlin/",
        "summary": "I am a dedicated and skilled software engineer with experience in full-stack development, cloud computing, and E-commerce projects.",
        "location": {
          "address": "",
          "postalCode": "",
          "city": "",
          "countryCode": "",
          "region": ""
        },
        "profiles": [{
          "network": "Linkedin",
          "username": "wang-hanlin",
          "url": "https://www.linkedin.com/in/wang-hanlin/"
        }]
      },
      "work": [{
        "name": "Amazon Web Services",
        "position": "Software Engineer Intern",
        "url": "",
        "startDate": "2023-05-01",
        "endDate": "2023-08-01",
        "summary": "Directed UI/UX overhaul, implemented React-Rails integration, developed advanced features, and optimized performance for a provisioning service.",
        "highlights": [
          "Directed comprehensive UI/UX redesign",
          "Implemented React-Rails for enhanced user engagement",
          "Boosted search speed and reduced loading times"
        ]
      },
      {
        "name": "eBay Inc",
        "position": "Software Engineer Intern",
        "url": "",
        "startDate": "2022-03-01",
        "endDate": "2022-06-01",
        "summary": "Created regression scheduling feature, developed scheduling configuration mechanisms, and implemented rollout strategy for efficient batch job management.",
        "highlights": [
          "Created regression scheduling feature with Kubernetes",
          "Developed flexible scheduling configuration mechanisms",
          "Implemented gradual rollout strategy for system robustness"
        ]
      },
      {
        "name": "TikTok (ByteDance)",
        "position": "Software Engineer Intern",
        "url": "",
        "startDate": "2021-01-01",
        "endDate": "2021-08-01",
        "summary": "Engaged in E-commerce promotion projects, developed task system, and improved user experience through efficient API and RPC implementations.",
        "highlights": [
          "Developed task system for unified task management",
          "Improved user engagement and reduced malicious activities",
          "Handled promotion service with high QPS and DAU growth"
        ]
      }],
      "volunteer": [],
      "education": [{
        "institution": "University of Illinois Urbana-Champaign (UIUC)",
        "url": "",
        "area": "Computer Science",
        "studyType": "Master",
        "startDate": "2022-09-01",
        "endDate": "2024-05-01",
        "score": "",
        "courses": []
      },
      {
        "institution": "The University of Hong Kong (HKU)",
        "url": "",
        "area": "Computer Science, Minor in Finance",
        "studyType": "Bachelor",
        "startDate": "2018-09-01",
        "endDate": "2022-06-01",
        "score": "1st Class Honor",
        "courses": []
      }],
      "awards": [],
      "certificates": [],
      "publications": [],
      "skills": [{
        "name": "Programming Languages",
        "level": "Master",
        "keywords": [
          "Java",
          "Python",
          "JavaScript",
          "Go",
          "Ruby",
          "C++",
          "Typescript"
        ]
      },
      {
        "name": "Web Techniques",
        "level": "Master",
        "keywords": [
          "CSS",
          "HTML",
          "Javascript",
          "React",
          "Ruby on Rails",
          "Express.js",
          "Node",
          "Vue"
        ]
      },
      {
        "name": "Database System",
        "level": "Master",
        "keywords": [
          "SQL (MySQL)",
          "DynamoDB (AWS)",
          "MongoDB",
          "PostgreSQL",
          "Neo4j",
          "Redis",
          "Spark",
          "HBase",
          "Hive",
          "Hadoop"
        ]
      },
      {
        "name": "Tools",
        "level": "Master",
        "keywords": [
          "Web-based AR",
          "Git",
          "AWS (EC2, SQS)",
          "Docker",
          "K8S",
          "Postman",
          "MS",
          "TensorFlow",
          "PyTorch",
          "Maven",
          "VMware",
          "Polaris UI"
        ]
      }],
      "languages": [],
      "interests": [],
      "references": [],
      "projects": [{
        "name": "Autonomous Vehicle Person-Tracking System",
        "startDate": "2023-01-01",
        "endDate": "2023-05-01",
        "description": "Created simulation environment for real-world obstacle avoidance and integrated advanced object recognition for precise tracking.",
        "highlights": [
          "Integrated Dlib and ROS for vehicle control",
          "Utilized PID controllers and GPS for dynamic tracking"
        ],
        "url": ""
      },
      {
        "name": "AR Wayfinding (HKU Capstone)",
        "startDate": "2021-09-01",
        "endDate": "2022-06-01",
        "description": "Designed and implemented web-based AR way-finding service on AWS using Dijkstra algorithm and QR code technology for visitor guidance.",
        "highlights": [
          "Enhanced system maintenance and efficiency through infrastructure decoupling"
        ],
        "url": ""
      }]
    }

    # 定义临时文件路径（确保当前工作目录有写权限）
    base_dir = os.getcwd()
    resume_file = os.path.join(base_dir, "resume.json")
    temp_html = os.path.join(base_dir, "temp_resume.html")
    output_pdf = os.path.join(base_dir, "output_resume.pdf")

    # 将 JSON 数据写入文件
    with open(resume_file, "w", encoding="utf-8") as f:
        json.dump(resume_json, f, ensure_ascii=False, indent=2)

    # 构造主题的绝对路径
    theme_path = os.path.join(base_dir, "node_modules", "jsonresume-theme-flat")
    
    # 调用 JSON Resume CLI 生成 HTML
    cmd = [
        "resume", "export", temp_html,
        "--theme", theme_path,
        "--format", "html",
        resume_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        error_message = result.stderr.decode()
        raise Exception(f"resume CLI error: {error_message}")

    # 使用 WeasyPrint 将生成的 HTML 转换为 PDF
    HTML(filename=temp_html).write_pdf(output_pdf)
    print("PDF 已生成：", output_pdf)

    # 清理临时文件（可选）
    os.remove(resume_file)
    os.remove(temp_html)

if __name__ == '__main__':
    generate_pdf_from_resume_json()
