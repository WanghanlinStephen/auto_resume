from django.db import models

class BaseModel(models.Model):
    """基础模型"""
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否有效")

    class Meta:
        abstract = True

class AlipayOrder(BaseModel):
    """支付宝订单"""
    out_trade_no = models.CharField(max_length=64, unique=True, verbose_name="订单号")
    trade_no = models.CharField(max_length=64, blank=True, verbose_name="支付宝交易号")
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="支付金额")
    status = models.CharField(max_length=20, choices=[('pending', '待支付'), ('paid', '已支付')], default='pending')

class WeChatOrder(BaseModel):
    """微信订单"""
    out_trade_no = models.CharField(max_length=64, unique=True, verbose_name="订单号")
    transaction_id = models.CharField(max_length=64, blank=True, verbose_name="微信交易号")
    total_fee = models.IntegerField(verbose_name="支付金额（分）")
    status = models.CharField(max_length=20, choices=[('pending', '待支付'), ('paid', '已支付')], default='pending')

class StripeOrder(BaseModel):
    """信用卡订单"""
    charge_id = models.CharField(max_length=64, unique=True, verbose_name="Stripe 交易号")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="支付金额")
    status = models.CharField(max_length=20, choices=[('pending', '待支付'), ('paid', '已支付')], default='pending')
