# blog/admin_modules/staticpage_admin.py

from django.contrib import admin
from django import forms
from blog.models import StaticPage

# Админская форма для модели StaticPage
class StaticPageAdminForm(forms.ModelForm):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 30}))

    class Meta:
        model = StaticPage
        fields = '__all__'

    class Media:
        js = ('admin/js/custom_admin.js',)

# Регистрация модели StaticPage в админке
@admin.register(StaticPage)
class StaticPageAdmin(admin.ModelAdmin):
    form = StaticPageAdminForm
    prepopulated_fields = {"slug": ("title",)}
    list_display = ('title', 'h1', 'show_in_footer', 'show_in_header')
    search_fields = ('title', 'h1', 'content')
