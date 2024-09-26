import re
from django.db import models
from django.utils.text import slugify
from unidecode import unidecode
from django_ckeditor_5.fields import CKEditor5Field
from django.urls import reverse

# Функция транслитерации
def transliterate(value):
    value = unidecode(value)
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    value = re.sub(r'[-\s]+', '-', value)
    return value

# Модель для тегов
class Tag(models.Model):
    name = models.CharField(max_length=1000, unique=True)
    slug = models.SlugField(unique=True, max_length=2550, blank=True)
    count = models.IntegerField(default=0)
    protected = models.BooleanField(default=False)
    title = models.CharField(max_length=2000, blank=True, null=True)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug or self.slug != transliterate(self.name):
            self.slug = transliterate(self.name)
        if not self.name and self.h1:
            self.name = self.h1
        super().save(*args, **kwargs)

    def post_count(self):
        return self.posts.count()

    def get_absolute_url(self):
        return reverse('tagged', args=[self.slug])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Теги работ"
        verbose_name_plural = "Теги работ"

# Модель для категорий
class Category(models.Model):
    name = models.CharField(max_length=1000, unique=True)
    slug = models.SlugField(unique=True, max_length=2550, blank=True)
    tags = models.ManyToManyField(Tag, related_name='categories', blank=True)
    title = models.CharField(max_length=2000, blank=True, null=True)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug or self.slug != transliterate(self.name):
            self.slug = transliterate(self.name)
        if not self.name and self.h1:
            self.name = self.h1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category_detail', args=[self.slug])

    def __str__(self):
        return self.name


    class Meta:
        verbose_name = "Категория работ"
        verbose_name_plural = "Категории работ"

# Модель для постов
class Post(models.Model):
    name = models.CharField(max_length=1000, unique=True)
    title = models.CharField(max_length=2000)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    content = CKEditor5Field('Content', config_name='extends', blank=True, null=True)  # Используем CKEditor5Field для редактирования контента
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, max_length=2550, blank=True)
    category = models.ForeignKey(Category, related_name='posts', on_delete=models.CASCADE, null=True)
    tags = models.ManyToManyField(Tag, related_name='posts', blank=True)
    description = models.TextField(blank=True, null=True)

    # Новые поля
    subject = models.CharField(max_length=2000, blank=True, null=True)  # Поле для предмета
    creation_date = models.CharField(max_length=1000, blank=True, null=True)  # Поле для даты создания
    pages = models.CharField(max_length=2000, blank=True, null=True)  # Поле для количества страниц
    sources = models.IntegerField(blank=True, null=True)  # Поле для источников
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Поле для цены

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = transliterate(self.name)
        super().save(*args, **kwargs)

    def average_rating(self):
        comments = self.comments.filter(approved=True)
        if comments:
            return sum(comment.rating for comment in comments) / len(comments)
        return 0

    def get_similar_posts(self):
        return Post.objects.filter(category=self.category).exclude(id=self.id)[:6]

    def get_absolute_url(self):
        return reverse('post_detail', args=[self.slug])

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Работы"
        verbose_name_plural = "Работы"

# Модель для статических страниц
class StaticPage(models.Model):
    title = models.CharField(max_length=2000)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    slug = models.SlugField(unique=True, max_length=2505)
    content = CKEditor5Field('Content', config_name='extends', blank=True, null=True)  # Используем CKEditor5Field
    show_in_footer = models.BooleanField(default=False)
    show_in_header = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug or self.slug != transliterate(self.title):
            self.slug = transliterate(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('static_page', args=[self.slug])

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Страницы"
        verbose_name_plural = "Страницы"

# Модель для комментариев
class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True)
    name = models.CharField(max_length=1000)
    email = models.EmailField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    rating = models.IntegerField(default=0)

    def __str__(self):
        return f"Comment by {self.name} on {self.post}"

    class Meta:
        verbose_name = "Комментарии"
        verbose_name_plural = "Комментарии"

# Новая модель для тегов статей
class ArticleTag(models.Model):
    name = models.CharField(max_length=1000, unique=True)
    slug = models.SlugField(unique=True, max_length=2505, blank=True)
    count = models.IntegerField(default=0)
    protected = models.BooleanField(default=False)
    title = models.CharField(max_length=2000, blank=True, null=True)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug or self.slug != transliterate(self.name):
            self.slug = transliterate(self.name)
        if not self.name and self.h1:
            self.name = self.h1
        super().save(*args, **kwargs)

    def post_count(self):
        return self.article_posts.count()

    def get_absolute_url(self):
        return reverse('article_tagged', args=[self.slug])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Теги для статей"
        verbose_name_plural = "Теги для статей"

# Новая модель для категорий статей
class ArticleCategory(models.Model):
    name = models.CharField(max_length=1000, unique=True)
    slug = models.SlugField(unique=True, max_length=2055, blank=True)
    tags = models.ManyToManyField(ArticleTag, related_name='article_categories', blank=True)
    title = models.CharField(max_length=2000, blank=True, null=True)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug or self.slug != transliterate(self.name):
            self.slug = transliterate(self.name)
        if not self.name and self.h1:
            self.name = self.h1
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('article_category_detail', args=[self.slug])

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория статей"
        verbose_name_plural = "Категории статей"

# Новая модель для постов статей
class ArticlePost(models.Model):
    name = models.CharField(max_length=1000, unique=True)
    title = models.CharField(max_length=2000)
    h1 = models.CharField(max_length=2000, blank=True, null=True)
    content = CKEditor5Field('Content', config_name='extends', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(unique=True, max_length=2505, blank=True)
    category = models.ForeignKey(ArticleCategory, related_name='articles', on_delete=models.CASCADE, null=True)
    tags = models.ManyToManyField(ArticleTag, related_name='article_posts', blank=True)
    description = models.TextField(blank=True, null=True)

    # Новые поля
    subject = models.CharField(max_length=2000, blank=True, null=True)  # Поле для предмета
    creation_date = models.CharField(max_length=1000, blank=True, null=True)  # Поле для даты создания
    pages = models.CharField(max_length=2000, blank=True, null=True)  # Поле для количества страниц
    sources = models.IntegerField(blank=True, null=True)  # Поле для источников
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # Поле```python
# для цены

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = transliterate(self.name)
        super().save(*args, **kwargs)

    def average_rating(self):
        if hasattr(self, 'comments') and self.comments is not None:
            comments = self.comments.filter(approved=True)
            if comments.exists():
                return sum(comment.rating for comment in comments) / len(comments)
        return 0

    def get_similar_posts(self):
        return ArticlePost.objects.filter(category=self.category).exclude(id=self.id)[:6]

    def get_absolute_url(self):
        return reverse('article_post_detail', args=[self.slug])

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Статьи"
        verbose_name_plural = "Статьи"
