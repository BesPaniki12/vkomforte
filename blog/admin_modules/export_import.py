import os
import sqlite3
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render, redirect
from blog.models import Post, Category, Tag
from blog.utils import transliterate
from blog.forms import UploadFileWithFormatForm, ExportFormatForm

# Функция для импорта данных из DataFrame
def import_from_dataframe(df, model_class, category_model=None, tag_model=None):
    """
    Импорт данных из Pandas DataFrame для указанных моделей.
    
    :param df: DataFrame с данными для импорта
    :param model_class: Django модель, для которой осуществляется импорт
    :param category_model: Модель для категорий (если есть)
    :param tag_model: Модель для тегов (если есть)
    """
    for _, row in df.iterrows():
        # Если есть категория
        if category_model:
            category, _ = category_model.objects.get_or_create(name=row['category'], defaults={
                'title': row.get('category_title', f"{row['category']}"),
                'h1': row.get('category_h1', f"{row['category']}"),
                'description': row.get('category_description', f"{row['category']}")
            })
        else:
            category = None

        # Импорт основной модели
        obj, created = model_class.objects.get_or_create(
            id=row['id'],
            defaults={
                'name': row['name'],
                'title': row['title'],
                'h1': row['h1'],
                'content': row['content'],
                'category': category,
                'description': row['description'],
                'subject': row.get('subject', ''),
                'creation_date': row.get('creation_date', None),
                'pages': row.get('pages', None),
                'sources': row.get('sources', None),
                'price': row.get('price', None)
            }
        )
        
        # Если есть теги
        if tag_model and 'tags' in row:
            tags = row['tags'].split(',')
            for tag_name in tags:
                tag_name = tag_name.strip()
                # Проверяем существование тега
                tag, _ = tag_model.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': transliterate(tag_name)}
                )
                obj.tags.add(tag)

        obj.save()

# Импорт данных из SQLite
def import_from_sqlite(sqlite_file, model_class, category_model=None, tag_model=None, table_name="parsed_essays"):
    """
    Импорт данных из SQLite файла в указанную Django модель.

    :param sqlite_file: Файл SQLite для импорта
    :param model_class: Django модель, для которой осуществляется импорт
    :param category_model: Модель для категорий (если есть)
    :param tag_model: Модель для тегов (если есть)
    :param table_name: Имя таблицы в базе данных SQLite
    """
    upload_dir = 'uploads'
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, sqlite_file.name)
    
    with open(file_path, 'wb+') as destination:
        for chunk in sqlite_file.chunks():
            destination.write(chunk)

    conn = sqlite3.connect(file_path)
    cursor = conn.cursor()

    cursor.execute(f'SELECT * FROM {table_name}')
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]

    for row in rows:
        row_data = dict(zip(columns, row))
        
        # Если есть категория
        if category_model:
            category, _ = category_model.objects.get_or_create(name=row_data['category_name'], defaults={
                'title': row_data.get('category_title', f"{row_data['category_name']}"),
                'h1': row_data.get('category_h1', f"{row_data['category_name']}"),
                'description': row_data.get('category_description', f"{row_data['category_name']}")
            })
        else:
            category = None

        # Импорт основной модели
        obj, created = model_class.objects.update_or_create(
            id=row_data['id'],
            defaults={
                'name': row_data['name'],
                'title': row_data['title'],
                'h1': row_data['h1'],
                'content': row_data['content'],
                'category': category,
                'description': row_data['description'],
                'subject': row_data.get('subject', ''),
                'creation_date': row_data.get('creation_date', None),
                'pages': row_data.get('pages', None),
                'sources': row_data.get('sources', None),
                'price': row_data.get('price', None)
            }
        )

        # Если есть теги
        if tag_model and 'tags' in row_data:
            tags = row_data['tags'].split(',')
            obj.tags.clear()  # Очищаем существующие теги перед добавлением новых
            for tag_name in tags:
                tag_name = tag_name.strip()
                # Проверяем существование тега
                tag, _ = tag_model.objects.get_or_create(
                    name=tag_name,
                    defaults={'slug': transliterate(tag_name)}
                )
                obj.tags.add(tag)

        obj.save()

    conn.close()
    os.remove(file_path)

# Экспорт данных в Excel
def export_to_excel(model_class, fields, filename="data.xlsx"):
    """
    Экспорт данных из Django модели в Excel.

    :param model_class: Django модель, из которой осуществляется экспорт
    :param fields: Поля для экспорта
    :param filename: Имя файла для экспорта
    """
    data = model_class.objects.all().values(*fields)
    df = pd.DataFrame(data)

    # Если модель имеет теги, их нужно конкатенировать в строку
    if 'tags' in fields:
        df['tags'] = df.apply(
            lambda row: ','.join(model_class.objects.get(id=row['id']).tags.values_list('name', flat=True)),
            axis=1
        )

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    df.to_excel(response, index=False)
    return response

# Экспорт данных в SQLite
def export_to_sqlite(model_class, fields, table_name="parsed_data", filename="exported_data.sqlite"):
    """
    Экспорт данных из Django модели в SQLite файл.

    :param model_class: Django модель, из которой осуществляется экспорт
    :param fields: Поля для экспорта
    :param table_name: Имя таблицы в SQLite
    :param filename: Имя файла для экспорта
    """
    export_file_path = f'/tmp/{filename}'
    os.makedirs(os.path.dirname(export_file_path), exist_ok=True)
    conn = sqlite3.connect(export_file_path)
    cursor = conn.cursor()

    cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
    cursor.execute(f'''
        CREATE TABLE {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {', '.join(f'{field} TEXT' for field in fields)}
        )
    ''')

    for obj in model_class.objects.all():
        data = [getattr(obj, field) if field != 'tags' else ','.join(tag.name for tag in obj.tags.all()) for field in fields]
        cursor.execute(f'''
            INSERT INTO {table_name} ({', '.join(fields)})
            VALUES ({', '.join('?' for _ in fields)})
        ''', data)

    conn.commit()
    conn.close()

    with open(export_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/x-sqlite3')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
