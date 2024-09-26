# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('page/<slug:slug>/', views.static_page, name='static_page'),
    path('tag/<slug:slug>/', views.tagged, name='tagged'),
    path('about/', views.about, name='about'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('search/', views.search, name='search'),
    path('article_post/<slug:slug>/', views.article_post_detail, name='article_post_detail'),
    path('article_category/<slug:slug>/', views.article_category_detail, name='article_category_detail'),
    path('tag/<slug:slug>/', views.article_tagged, name='article_tagged'),
    path('article_category/', views.all_articles, name='all_articles'),
    path('form/', views.form_view, name='form_view'),  # Настройка маршрута для отправки данных
    path('article_tagged/<slug:slug>/', views.article_tagged, name='article_tagged'),  # добавляем этот маршрут
]

