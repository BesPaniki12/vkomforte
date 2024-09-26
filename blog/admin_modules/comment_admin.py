# blog/admin_modules/comment_admin.py

from django.contrib import admin
from blog.models import Comment

# Регистрация модели Comment в админке
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'post', 'created_at', 'approved', 'rating')
    list_filter = ('approved', 'created_at')
    search_fields = ('name', 'email', 'content')
    actions = ['approve_comments']

    def approve_comments(self, request, queryset):
        queryset.update(approved=True)
    approve_comments.short_description = "Одобрить выбранные комментарии"
