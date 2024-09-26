from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.contrib.sitemaps.views import sitemap
from blog.sitemaps import PostSitemap, CategorySitemap

sitemaps_dict = {
    'posts': PostSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    path('adminikus/', admin.site.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('', include('blog.urls')),
    path('custom_sitemap.xml', sitemap, {'sitemaps': sitemaps_dict}, name='custom_sitemap'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)