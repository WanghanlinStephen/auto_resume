from django.urls import path
from . import views

urlpatterns = [
    path('', views.resume_modify_view, name='resume_form'),
    path('result/', views.resume_result_view, name='resume_result'),
    path("download_pdf/", views.download_pdf_view, name="download_pdf"),
]
