# blog/admin_modules/category_admin.py

from django.contrib import admin
from django import forms
from blog.models import Category
from blog.utils import transliterate
import os
import sqlite3
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import path
from blog.forms import UploadFileWithFormatForm, ExportFormatForm, GoogleSheetURLForm
from blog.google_sheets import get_google_sheets_data

# Админская форма для модели Category
class CategoryAdminForm(forms.ModelForm):
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 30}))

    class Meta:
        model = Category
        fields = '__all__'

    class Media:
        js = ('admin/js/custom_admin.js',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    form = CategoryAdminForm
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ('tags',)
    list_display = ('name', 'title', 'h1', 'description')
    search_fields = ('name', 'title', 'h1', 'description')

    # Добавление URL для кастомных действий (импорт/экспорт данных)
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.import_data, name='blog_category_import'),
            path('export/', self.export_data, name='blog_category_export'),
            path('import_google_sheets/', self.import_google_sheets, name='blog_category_import_google_sheets'),
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

        cursor.execute('SELECT id, name, title, h1, description FROM parsed_categories')
        rows = cursor.fetchall()

        for row in rows:
            category_id, name, title, h1, description = row
            Category.objects.update_or_create(
                id=category_id,
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
        categories = Category.objects.all().values('id', 'name', 'title', 'h1', 'description')
        df = pd.DataFrame(categories)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=categories.xlsx'
        df.to_excel(response, index=False)
        return response

    # Экспорт в SQLite
    def export_sqlite_data(self, request):
        export_file_path = '/tmp/exported_category_data.sqlite'
        os.makedirs(os.path.dirname(export_file_path), exist_ok=True)
        conn = sqlite3.connect(export_file_path)
        cursor = conn.cursor()

        cursor.execute('DROP TABLE IF EXISTS parsed_categories')
        cursor.execute('''
            CREATE TABLE parsed_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                title TEXT,
                h1 TEXT,
                description TEXT
            )
        ''')

        for category in Category.objects.all():
            cursor.execute('''
                INSERT INTO parsed_categories (id, name, title, h1, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                category.id,
                category.name,
                category.title,
                category.h1,
                category.description
            ))

        conn.commit()
        conn.close()

        with open(export_file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/x-sqlite3')
            response['Content-Disposition'] = f'attachment; filename="exported_category_data.sqlite"'
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
            Category.objects.update_or_create(
                id=row['id'],
                defaults={
                    'name': row['name'],
                    'title': row['title'],
                    'h1': row['h1'],
                    'description': row['description']
                }
            )
