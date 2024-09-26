import logging
import requests
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q
from django.urls import reverse
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
import pandas as pd
import markdown2
from .models import Post, Category, Tag, StaticPage, Comment, ArticleCategory, ArticlePost, ArticleTag
from .forms import CommentForm, GoogleSheetURLForm

logger = logging.getLogger(__name__)

# Общие контексты
def get_common_context():
    categories = Category.objects.all()
    tags = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')
    static_pages = StaticPage.objects.all()
    article_categories = ArticleCategory.objects.all()  # Для статей
    return {
        'categories': categories,
        'tags': tags,
        'static_pages': static_pages,
        'article_categories': article_categories,  # Для статей
    }

def get_common_article_context():
    # Подсчитываем количество статей в каждой категории
    categories = ArticleCategory.objects.annotate(article_post_count=Count('articles')).all()
    
    # Подсчитываем количество статей для каждого тега
    tags = ArticleTag.objects.annotate(article_post_count=Count('article_posts')).order_by('-article_post_count')
    
    return {
        'categories': categories,
        'tags': tags,
    }

# Функция пагинации
def handle_pagination(request, queryset, per_page=20):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj

# Функция для получения семантически похожих тегов (на основе постов в категории)
def get_semantically_similar_tags(category, limit=50):
    tags = Tag.objects.filter(posts__category=category).annotate(post_count=Count('posts')).order_by('-post_count')[:limit]
    return tags



# Представления для категорий с улучшенной логикой тегов
def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    post_list = category.posts.all()
    page_obj = handle_pagination(request, post_list)
    breadcrumbs = [{'name': category.h1}]

    # Получаем теги, сортированные по количеству постов, и разбиваем на первые 10 и дополнительные 40
    tags = get_semantically_similar_tags(category, limit=50)
    first_10_tags = tags[:10]
    extra_tags = tags[10:]

    context = get_common_context()
    context.update({
        'category': category,
        'page_obj': page_obj,
        'tags': first_10_tags,  # Первые 10 тегов для отображения
        'extra_tags': extra_tags,  # Следующие теги для разворачивания
        'category_tags_only': True,
        'breadcrumbs': breadcrumbs,
        'canonical_url': request.build_absolute_uri(),
        'next_url': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_url': reverse('category_detail', args=[slug]) if page_obj.number == 1 else page_obj.previous_page_number() if page_obj.has_previous() else None,
    })
    return render(request, 'category.html', context)






def index(request):
    post_list = Post.objects.all()
    page_obj = handle_pagination(request, post_list)

    # Получаем теги на основе всех постов (сортируем по количеству постов)
    tags = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:50]
    first_10_tags = tags[:10]
    extra_tags = tags[10:]

    context = get_common_context()
    context.update({
        'page_obj': page_obj,
        'tags': first_10_tags,  # Первые 10 тегов для отображения
        'extra_tags': extra_tags,  # Следующие теги для разворачивания
        'canonical_url': request.build_absolute_uri(),
        'next_url': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_url': reverse('index') if page_obj.number == 1 else page_obj.previous_page_number() if page_obj.has_previous() else None,
    })
    return render(request, 'index.html', context)





def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    comments = post.comments.filter(approved=True)
    related_posts = post.get_similar_posts()
    breadcrumbs = [
        {'name': post.category.h1, 'url': reverse('category_detail', args=[post.category.slug])},
        {'name': post.h1}
    ]

    logger.info(f"Original content: {post.content}")

    post.content = markdown2.markdown(post.content, extras=[
        "fenced-code-blocks",
        "tables",
        "break-on-newline",
        "header-ids",
        "code-friendly"
    ])

    logger.info(f"Converted content: {post.content}")

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.post = post
            new_comment.category = post.category
            new_comment.rating = request.POST.get('rating', 0)
            new_comment.save()
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success', 'message': 'Комментарий успешно добавлен'})
            return redirect('post_detail', slug=post.slug)
    else:
        comment_form = CommentForm()

    context = get_common_context()
    context.update({
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'breadcrumbs': breadcrumbs,
        'related_posts': related_posts,
        'canonical_url': post.get_absolute_url()
    })
    return render(request, 'post.html', context)




def tagged(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    post_list = Post.objects.filter(tags=tag)
    page_obj = handle_pagination(request, post_list)

    # Получаем теги, сортированные по количеству постов (с ограничением 50)
    tags = Tag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:50]
    first_10_tags = tags[:10]
    extra_tags = tags[10:]

    breadcrumbs = [{'name': 'Теги', 'url': reverse('tagged', args=[slug])}, {'name': tag.h1}]

    context = get_common_context()
    context.update({
        'page_obj': page_obj,
        'tag': tag,
        'tags': first_10_tags,  # Первые 10 тегов для отображения
        'extra_tags': extra_tags,  # Следующие теги для разворачивания
        'breadcrumbs': breadcrumbs,
        'canonical_url': request.build_absolute_uri(),
        'next_url': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_url': reverse('tagged', args=[slug]) if page_obj.number == 1 else page_obj.previous_page_number() if page_obj.has_previous() else None,
    })
    return render(request, 'tagged.html', context)








def static_page(request, slug):
    page = get_object_or_404(StaticPage, slug=slug)
    breadcrumbs = [{'name': page.h1}]

    logger.info(f"Original static page content: {page.content}")

    page.content = markdown2.markdown(page.content, extras=[
        "fenced-code-blocks",
        "tables",
        "break-on-newline",
        "header-ids",
        "code-friendly"
    ])

    logger.info(f"Converted static page content: {page.content}")

    context = get_common_context()
    context.update({
        'page': page,
        'breadcrumbs': breadcrumbs,
        'canonical_url': page.get_absolute_url()
    })
    return render(request, 'static_page.html', context)

def about(request):
    context = get_common_context()
    return render(request, 'about.html', context)

def privacy_policy(request):
    context = get_common_context()
    return render(request, 'privacy-policy.html', context)

def search(request):
    query = request.GET.get('q')

    post_results = Post.objects.filter(
        Q(title__icontains=query) |
        Q(content__icontains=query) |
        Q(category__name__icontains(query)) |
        Q(tags__name__icontains(query))
    ).distinct() if query else []

    article_results = ArticlePost.objects.filter(
        Q(title__icontains(query)) |
        Q(content__icontains(query)) |
        Q(category__name__icontains(query)) |
        Q(tags__name__icontains(query))
    ).distinct() if query else []

    context = get_common_context()
    context.update({
        'query': query,
        'post_results': post_results,
        'article_results': article_results
    })
    return render(request, 'search_results.html', context)

# Импорт и экспорт данных
def import_posts(request):
    if request.method == 'POST':
        file = request.FILES['file']
        df = pd.read_excel(file)

        for _, row in df.iterrows():
            category, _ = Category.objects.get_or_create(name=row['category'])
            post, created = Post.objects.get_or_create(
                id=row['id'],
                defaults={
                    'name': row['h1'],
                    'title': row['title'],
                    'h1': row['h1'],
                    'content': row['content'],
                    'category': category,
                    'description': row['description']
                }
            )
            if not created:
                post.name = row['h1']
                post.title = row['title']
                post.h1 = row['h1']
                post.content = row['content']
                post.category = category
                post.description = row['description']
                post.save()

            tags = row['tags'].split(',')
            post.tags.clear()
            for tag_name in tags:
                tag, _ = Tag.objects.get_or_create(name=tag_name.strip())
                post.tags.add(tag)

        return redirect('admin:blog_post_changelist')
    return render(request, 'admin/import.html')

def export_posts(request):
    posts = Post.objects.all().values('id', 'name', 'title', 'h1', 'content', 'category__name', 'description')
    df = pd.DataFrame(posts)
    df['tags'] = df.apply(
        lambda row: ','.join(Post.objects.get(id=row['id']).tags.values_list('name', flat=True)),
        axis=1
    )
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=posts.xlsx'
    df.to_excel(response, index=False)
    return response

def import_google_sheets(request):
    if request.method == 'POST':
        form = GoogleSheetURLForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data['url']
            data = get_google_sheets_data(url)
            df = pd.DataFrame(data[1:], columns=data[0])

            for _, row in df.iterrows():
                category, _ = Category.objects.get_or_create(name=row['category'])
                post, created = Post.objects.get_or_create(
                    id=row['id'],
                    defaults={
                        'name': row['h1'],
                        'title': row['title'],
                        'h1': row['h1'],
                        'content': row['content'],
                        'category': category,
                        'description': row['description']
                    }
                )
                if not created:
                    post.name = row['h1'],
                    post.title = row['title']
                    post.h1 = row['h1']
                    post.content = row['content']
                    post.category = category
                    post.description = row['description']
                    post.save()

                tags = row['tags'].split(',')
                post.tags.clear()
                for tag_name in tags:
                    tag, _ = Tag.objects.get_or_create(name=tag_name.strip())
                    post.tags.add(tag)

            return redirect('admin:blog_post_changelist')
    else:
        form = GoogleSheetURLForm()
    return render(request, "admin/import_google_sheets.html", {"form": form})

# Новые представления для работы с категориями и постами статей
def article_category_detail(request, slug):
    category = get_object_or_404(ArticleCategory, slug=slug)
    article_list = category.articles.all()
    page_obj = handle_pagination(request, article_list)
    breadcrumbs = [{'name': category.h1}]

    context = get_common_article_context()
    context.update({
        'category': category,
        'page_obj': page_obj,
        'breadcrumbs': breadcrumbs,
        'canonical_url': request.build_absolute_uri(),
        'next_url': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_url': reverse('article_category_detail', args=[slug]) if page_obj.number == 1 else page_obj.previous_page_number() if page_obj.has_previous() else None,
    })
    return render(request, 'article_category.html', context)

def article_post_detail(request, slug):
    post = get_object_or_404(ArticlePost, slug=slug)
    related_posts = post.get_similar_posts()
    breadcrumbs = [
        {'name': post.category.h1, 'url': reverse('article_category_detail', args=[post.category.slug])},
        {'name': post.h1}
    ]

    post.content = markdown2.markdown(post.content, extras=[
        "fenced-code-blocks",
        "tables",
        "break-on-newline",
        "header-ids",
        "code-friendly"
    ])

    context = get_common_article_context()
    context.update({
        'post': post,
        'breadcrumbs': breadcrumbs,
        'related_posts': related_posts,
        'canonical_url': post.get_absolute_url()
    })
    return render(request, 'article_post.html', context)

def article_tagged(request, slug):
    tag = get_object_or_404(ArticleTag, slug=slug)
    article_list = ArticlePost.objects.filter(tags=tag)
    page_obj = handle_pagination(request, article_list)
    breadcrumbs = [{'name': 'Теги', 'url': reverse('article_tagged', args=[slug])}, {'name': tag.h1}]

    context = get_common_article_context()
    context.update({
        'page_obj': page_obj,
        'tag': tag,
        'breadcrumbs': breadcrumbs,
        'canonical_url': request.build_absolute_uri(),
        'next_url': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_url': reverse('article_tagged', args=[slug]) if page_obj.number == 1 else page_obj.previous_page_number() if page_obj.has_previous() else None,
    })
    return render(request, 'article_tagged.html', context)


def all_articles(request):
    article_list = ArticlePost.objects.all().order_by('-created_at')  # Получаем все статьи, сортированные по дате создания
    page_obj = handle_pagination(request, article_list)

    context = get_common_article_context()  # Используем get_common_article_context для получения категорий и тегов статей
    context.update({
        'page_obj': page_obj,
        'canonical_url': request.build_absolute_uri(),
        'next_url': page_obj.next_page_number() if page_obj.has_next() else None,
        'prev_url': page_obj.previous_page_number() if page_obj.has_previous() else None,
    })
    return render(request, 'all_articles.html', context)

def form_view(request):
    if request.method == 'POST':
        # Получение данных из формы
        partner_id = request.POST.get('PartnerId')
        work_type = request.POST.get('work_type')
        topic = request.POST.get('topic')
        email = request.POST.get('email')
        subject = request.POST.get('subject', '')  # Предмет может быть необязательным
        phone = request.POST.get('phone')
        
        # Подготовка данных для отправки на сервер партнера
        data = {
            'PartnerId': partner_id,
            'WorkType': work_type,
            'Topic': topic,
            'Email': email,
            'Subject': subject,
            'Phone': phone,
        }

        # Отправка POST-запроса на сервер партнера
        try:
            response = requests.post('https://www.homework.ru/order/form-partner/', data=data)
            
            # Проверка успешности запроса
            if response.status_code == 200:
                return HttpResponse("Данные успешно отправлены.")
            else:
                return HttpResponse(f"Ошибка при отправке данных: {response.status_code}.")
        except requests.exceptions.RequestException as e:
            return HttpResponse(f"Ошибка при отправке данных: {e}")

    return render(request, 'sidebar_form.html')
