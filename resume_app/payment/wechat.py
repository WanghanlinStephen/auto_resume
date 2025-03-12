import requests

APP_ID = "你的微信 APP ID"
MCH_ID = "你的商户号"
API_KEY = "你的 API Key"

def generate_wechat_qr(out_trade_no, total_fee):
    payload = {
        "appid": APP_ID,
        "mch_id": MCH_ID,
        "nonce_str": "随机字符串",
        "body": "订单支付",
        "out_trade_no": out_trade_no,
        "total_fee": total_fee,
        "notify_url": "你的回调地址"
    }
    response = requests.post("https://api.mch.weixin.qq.com/pay/unifiedorder", data=payload)
    return response.json().get("code_url")
