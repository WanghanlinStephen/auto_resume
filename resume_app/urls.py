from django.urls import path, include
from . import views
from rest_framework.routers import DefaultRouter
from .views import AlipayViewSet, WeChatViewSet, StripeViewSet, ExtractTextView, GenerateCodeView, DebugView

# DRF 视图集路由
router = DefaultRouter()
# router.register(r'alipay', AlipayViewSet, basename='alipay')
# router.register(r'wechat', WeChatViewSet, basename='wechat')
# router.register(r'stripe', StripeViewSet, basename='stripe')

urlpatterns = [
    # 用户相关
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path("profile/", views.profile, name="profile"),

    # 简历相关
    path('result/', views.modify_resume, name='resume_result'),
    path("download_pdf/", views.download_pdf, name="download_pdf"),

    # 支付相关
    path('alipay/<int:pk>/pay/', AlipayViewSet.as_view({'post': 'pay'}), name='alipay_pay'),
    path('wechat/<int:pk>/pay/', WeChatViewSet.as_view({'post': 'pay'}), name='wechat_pay'),
    path('stripe/<int:pk>/pay/', StripeViewSet.as_view({'post': 'pay'}), name='stripe_pay'),

    # auto-interview API
    path('extract/', ExtractTextView.as_view(), name='extract_text'),
    path('generate/', GenerateCodeView.as_view(), name='generate_code'),
    path('debug/', DebugView.as_view(), name='debug_code'),


    # REST API 路由
    path('', include(router.urls)),
]
