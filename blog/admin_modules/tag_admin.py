# blog/admin_modules/tag_admin.py

from django.contrib import admin
from django import forms
from blog.models import Tag
from blog.utils import transliterate
import os
import sqlite3
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path
from blog.forms import UploadFileWithFormatForm, ExportFormatForm, GoogleSheetURLForm
from blog.google_sheets import get_google_sheets_data

# Админская форма для модели Tag
class TagAdminForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 30}))

    class Meta:
        model = Tag
        fields = '__all__'

    class Media:
        js = ('admin/js/custom_admin.js',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagAdminForm
    prepopulated_fields = {"slug": ("name",)}
    list_display = ('name', 'title', 'h1', 'description', 'count', 'protected')
    search_fields = ('name', 'title', 'h1', 'description')
    change_list_template = "admin/tag_changelist.html"  # Указываем кастомный шаблон для страницы списка тегов

    # Добавление URL для кастомных действий (импорт/экспорт данных)
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.import_data, name='blog_tag_import'),  # URL для импорта тегов
            path('export/', self.export_data, name='blog_tag_export'),  # URL для экспорта тегов
            path('import_google_sheets/', self.import_google_sheets, name='blog_tag_import_google_sheets'),  # URL для импорта из Google Sheets
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

                self.message_user(request, "Теги успешно импортированы!")
                return redirect("..")
        else:
            form = UploadFileWithFormatForm()
        return render(request, "admin/upload.html", {"form": form})

    # Импорт данных из DataFrame
    def import_from_dataframe(self, df):
        for _, row in df.iterrows():
            Tag.objects.update_or_create(
                id=row['id'],
                defaults={
                    'name': row['name'],
                    'title': row['title'],
                    'h1': row['h1'],
                    'description': row['description']
                }
            )

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

        cursor.execute('SELECT id, name, title, h1, description FROM parsed_tags')
        rows = cursor.fetchall()

        for row in rows:
            tag_id, name, title, h1, description = row
            Tag.objects.update_or_create(
                id=tag_id,
                defaults={
                    'name': name,
                    'title': title,
                    'h1': h1,
                    'description': description
                }
            )

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
        tags = Tag.objects.all().values('id', 'name', 'title', 'h1', 'description')
        df = pd.DataFrame(tags)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=tags.xlsx'
        df.to_excel(response, index=False)
        return response

    # Экспорт в SQLite
    def export_sqlite_data(self, request):
        export_file_path = '/tmp/exported_tag_data.sqlite'
        os.makedirs(os.path.dirname(export_file_path), exist_ok=True)
        conn = sqlite3.connect(export_file_path)
        cursor = conn.cursor()

        cursor.execute('DROP TABLE IF EXISTS parsed_tags')
        cursor.execute('''
            CREATE TABLE parsed_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                title TEXT,
                h1 TEXT,
                description TEXT
            )
        ''')

        for tag in Tag.objects.all():
            cursor.execute('''
                INSERT INTO parsed_tags (id, name, title, h1, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                tag.id,
                tag.name,
                tag.title,
                tag.h1,
                tag.description
            ))

        conn.commit()
        conn.close()

        with open(export_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/x-sqlite3')
            response['Content-Disposition'] = f'attachment; filename="exported_tag_data.sqlite"'
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
