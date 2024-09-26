from django.contrib.sitemaps import Sitemap
from django.core.paginator import Paginator
from django.http import HttpResponse
from .models import Post, Category, ArticlePost, ArticleCategory

class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Post.objects.all()

    def lastmod(self, obj):
        return obj.created_at  # Убедитесь, что у вас есть это поле в модели Post

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Category.objects.all()

class ArticlePostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ArticlePost.objects.all()

    def lastmod(self, obj):
        return obj.created_at

class ArticleCategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return ArticleCategory.objects.all()

class PaginatorSitemap(Sitemap):
    def get_urls(self, page=1, site=None, protocol=None):
        paginator = Paginator(self.items(), 10000)  # 10 000 элементов на одну карту сайта
        urls = []

        for i in range(1, paginator.num_pages + 1):
            urls.extend(super().get_urls(page=i, site=site, protocol=protocol))

        return urls

class CustomSitemapIndex:
    def __init__(self, sitemaps):
        self.sitemaps = sitemaps

    def get_urls(self, page=1, site=None, protocol=None):
        urls = []
        for section, site in self.sitemaps.items():
            if isinstance(site, dict):
                site = site['sitemap']
            urls.extend(site().get_urls(page, site, protocol))
        for url in urls:
            url['location'] = url['location'].replace('sitemap.xml', 'custom_sitemap.xml')
        return urls

def custom_sitemap_view(request):
    sitemap_index = CustomSitemapIndex({
        'posts': PostSitemap(),
        'categories': CategorySitemap(),
        'article_posts': ArticlePostSitemap(),
        'article_categories': ArticleCategorySitemap(),
    })
    return HttpResponse(sitemap_index.get_urls(), content_type='application/xml')
