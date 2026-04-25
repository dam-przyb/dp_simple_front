from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('report/', views.report, name='report'),
    path('review/', views.review, name='review'),
    path('judgement/', views.judgement, name='judgement'),
    path('upload/', views.upload, name='upload'),
    path('upload/clean/', views.clean_files, name='clean_files'),
]
