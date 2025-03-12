import os
from alipay import AliPay
from dotenv import load_dotenv

load_dotenv()

# 获取当前文件的目录，即 `alipay_payment.py` 所在的目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 构造 `keys` 目录的绝对路径
private_key_path = os.path.join(BASE_DIR, "keys/alipay_private_key.pem")
public_key_path = os.path.join(BASE_DIR, "keys/alipay_public_key.pem")

# 读取私钥
with open(private_key_path, "r") as f:
    private_key = f.read()

# 读取支付宝公钥
with open(public_key_path, "r") as f:
    alipay_public_key = f.read()

# 创建 `AliPay` 实例
alipay = AliPay(
    appid=os.getenv("ALIPAY_APP_ID"),
    app_notify_url=None,
    app_private_key_string=private_key,  # 替换 `app_private_key_path`
    alipay_public_key_string=alipay_public_key,  # 替换 `alipay_public_key_path`
    sign_type="RSA2",
    debug=True
)

def generate_alipay_url(out_trade_no, total_amount):
    """ 生成支付宝支付 URL """
    order_string = alipay.api_alipay_trade_page_pay(
        subject="订单支付",
        out_trade_no=out_trade_no,
        total_amount=total_amount,
        return_url="https://your-site.com/return",
        notify_url="https://your-site.com/notify"
    )
    return f"https://openapi.alipay.com/gateway.do?{order_string}"