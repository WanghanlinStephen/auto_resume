import boto3
import os
from dotenv import load_dotenv

load_dotenv()
# AWS 配置 (请替换为你的真实信息)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "your_access_key")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "your_secret_key")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "your_bucket_name")
AWS_REGION_NAME = os.getenv("AWS_REGION_NAME", "us-west-2")  # 替换为你的 AWS 区域
S3_BASE_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_REGION_NAME}.amazonaws.com/"

# 创建 S3 客户端
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION_NAME
)
