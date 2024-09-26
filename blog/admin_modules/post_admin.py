from django.contrib import admin
from django import forms
from blog.models import Post, Category, Tag
from blog.utils import transliterate
import os
import sqlite3
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path
from blog.forms import UploadFileWithFormatForm, ExportFormatForm, GoogleSheetURLForm
from blog.google_sheets import get_google_sheets_data

# Функция для генерации уникального slug
def generate_unique_slug(slug, model):
    original_slug = slug
    counter = 2

    # Проверяем, существует ли запись с таким же slug
    while model.objects.filter(slug=slug).exists():
        slug = f"{original_slug}-{counter}"
        counter += 1

    return slug

# Функция для генерации уникального имени
def generate_unique_name(name, model):
    original_name = name
    counter = 2

    # Проверка на существование поста с таким же именем
    while model.objects.filter(name=name).exists():
        name = f"{original_name}-{counter}"
        counter += 1

    return name

# Админская форма для модели Post
class PostAdminForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 30}))

    class Meta:
        model = Post
        fields = '__all__'

    class Media:
        js = ('admin/js/custom_admin.js',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    form = PostAdminForm
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('title', 'h1', 'created_at', 'category', 'description', 'average_rating', 'subject', 'creation_date', 'pages', 'sources', 'price')
    search_fields = ('title', 'h1', 'content', 'description', 'subject', 'creation_date', 'pages', 'sources', 'price')
    list_filter = ('category', 'tags')
    filter_horizontal = ('tags',)
    change_list_template = "admin/post_changelist.html"

    # Добавление URL для кастомных действий (импорт/экспорт данных)
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.import_data, name='blog_post_import'),
            path('export/', self.export_data, name='blog_post_export'),
            path('import_google_sheets/', self.import_google_sheets, name='blog_post_import_google_sheets'),
        ]
        return custom_urls + urls

    # Импорт данных
    def import_data(self, request):
        if request.method == 'POST':
            form = UploadFileWithFormatForm(request.POST, request.FILES)
            if form.is_valid():
                file = form.cleaned_data['file']
                file_format = form.cleaned_data['file_format']

                if file_format == 'excel':
                    df = pd.read_excel(file)
                    self.import_from_dataframe(df)
                elif file_format == 'sqlite':
                    self.import_from_sqlite(file)

                self.message_user(request, "Данные успешно импортированы!")
                return redirect("..")
        else:
            form = UploadFileWithFormatForm()
        return render(request, "admin/upload.html", {"form": form})

    # Импорт данных из SQLite
    def import_from_sqlite(self, sqlite_file):
        upload_dir = 'uploads'
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, sqlite_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in sqlite_file.chunks():
                destination.write(chunk)

        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()

        cursor.execute('SELECT id, name, title, h1, content, category_name, description, subject, creation_date, pages, sources, price, tags FROM parsed_essays')
        rows = cursor.fetchall()

        for row in rows:
            post_id, name, title, h1, content, category_name, description, subject, creation_date, pages, sources, price, tags_str = row
            category, _ = Category.objects.get_or_create(name=category_name)

            # Генерация уникального имени и slug
            name = generate_unique_name(name, Post)
            slug = transliterate(name)
            slug = generate_unique_slug(slug, Post)

            post, created = Post.objects.update_or_create(
                id=post_id,
                defaults={
                    'name': name,
                    'slug': slug,
                    'title': title,
                    'h1': h1,
                    'content': content,
                    'category': category,
                    'description': description,
                    'subject': subject,
                    'creation_date': creation_date,
                    'pages': pages,
                    'sources': sources,
                    'price': price,
                }
            )
            if tags_str:
                tags = tags_str.split(',')
                post.tags.clear()
                for tag_name in tags:
                    tag_name = tag_name.strip()
                    tag, created = Tag.objects.get_or_create(
                        slug=transliterate(tag_name),
                        defaults={'name': tag_name}
                    )
                    post.tags.add(tag)

        conn.close()
        os.remove(file_path)

    # Экспорт данных
    def export_data(self, request):
        if request.method == 'POST':
            form = ExportFormatForm(request.POST)
            if form.is_valid():
                export_format = form.cleaned_data['export_format']

                if export_format == 'excel':
                    return self.export_to_excel(request)
                elif export_format == 'sqlite':
                    return self.export_sqlite_data(request)

        else:
            form = ExportFormatForm()
        return render(request, "admin/export.html", {"form": form})

    # Экспорт в Excel
    def export_to_excel(self, request):
        posts = Post.objects.all().values('id', 'name', 'title', 'h1', 'content', 'category__name', 'description', 'subject', 'creation_date', 'pages', 'sources', 'price')
        df = pd.DataFrame(posts)
        df['tags'] = df.apply(
            lambda row: ','.join(Post.objects.get(id=row['id']).tags.values_list('name', flat=True)),
            axis=1
        )
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=posts.xlsx'
        df.to_excel(response, index=False)
        return response

    # Экспорт в SQLite
    def export_sqlite_data(self, request):
        export_file_path = '/tmp/exported_post_data.sqlite'
        os.makedirs(os.path.dirname(export_file_path), exist_ok=True)
        conn = sqlite3.connect(export_file_path)
        cursor = conn.cursor()

        cursor.execute('DROP TABLE IF EXISTS parsed_essays')
        cursor.execute('''
            CREATE TABLE parsed_essays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                title TEXT,
                h1 TEXT,
                content TEXT,
                category_name TEXT,
                description TEXT,
                subject TEXT,
                creation_date TEXT,
                pages TEXT,
                sources TEXT,
                price REAL,
                tags TEXT
            )
        ''')

        for post in Post.objects.all():
            tags = ','.join(tag.name for tag in post.tags.all())
            cursor.execute('''
                INSERT INTO parsed_essays (id, name, title, h1, content, category_name, description, subject, creation_date, pages, sources, price, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post.id,
                post.name,
                post.title,
                post.h1,
                post.content,
                post.category.name if post.category else '',
                post.description,
                post.subject,
                str(post.creation_date) if post.creation_date else '',
                post.pages,
                post.sources,
                float(post.price) if post.price else 0.0,
                tags
            ))

        conn.commit()
        conn.close()

        with open(export_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/x-sqlite3')
            response['Content-Disposition'] = f'attachment; filename="exported_post_data.sqlite"'
            return response

    # Импорт данных из Google Sheets
    def import_google_sheets(self, request):
        if request.method == 'POST':
            form = GoogleSheetURLForm(request.POST)
            if form.is_valid():
                sheet_url = form.cleaned_data['url']
                data = get_google_sheets_data(sheet_url)
                df = pd.DataFrame(data[1:], columns=data[0])
                self.import_from_dataframe(df)
                self.message_user(request, "Данные из Google Sheets успешно импортированы")
                return redirect("..")
        else:
            form = GoogleSheetURLForm()
        return render(request, "admin/import_google_sheets.html", {"form": form})

    # Импорт данных из DataFrame
    def import_from_dataframe(self, df):
        for _, row in df.iterrows():
            category, _ = Category.objects.get_or_create(name=row['category'], defaults={
                'title': row.get('category_title', f"{row['category']}"),
                'h1': row.get('category_h1', f"{row['category']}"),
                'description': row.get('category_description', f"{row['category']}")
            })

            # Генерация уникального имени и slug
            name = generate_unique_name(row['h1'], Post)
            slug = transliterate(name)
            slug = generate_unique_slug(slug, Post)

            post, created = Post.objects.get_or_create(
                id=row['id'],
                defaults={
                    'name': name,
                    'slug': slug,
                    'title': row['title'],
                    'h1': row['h1'],
                    'content': row['content'],
                    'category': category,
                    'description': row['description'],
                    'subject': row['subject'],
                    'creation_date': row['creation_date'],
                    'pages': row['pages'],
                    'sources': row['sources'],
                    'price': row['price']
                }
            )

            tags = row['tags'].split(',')
            for tag_name in tags:
                tag_name = tag_name.strip()
                tag, created = Tag.objects.get_or_create(
                    slug=transliterate(tag_name),
                    defaults={'name': tag_name}
                )
                post.tags.add(tag)
