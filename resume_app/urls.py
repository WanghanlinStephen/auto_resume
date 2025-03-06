from django.urls import path
from . import views

urlpatterns = [
    # 注册登陆
    path('register/',views.register, name='regsiter'),
    path('login/',views.login, name='login'),
    path("profile/", views.profile, name="profile"),

    path('result/',views.modify_resume, name='resume_result'),
    path("download_pdf/", views.download_pdf, name="download_pdf"),
]