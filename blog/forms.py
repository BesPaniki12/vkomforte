from django import forms
from .models import Post, Comment

class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'content', 'category', 'tags', 'slug']

class CommentForm(forms.ModelForm):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]
    rating = forms.ChoiceField(choices=RATING_CHOICES, widget=forms.RadioSelect)
    class Meta:
        model = Comment
        fields = ['name', 'email', 'content', 'rating']

class UploadFileForm(forms.Form):
    file = forms.FileField()

class GoogleSheetURLForm(forms.Form):
    url = forms.URLField(label='Google Sheet URL', required=True)

# Новые формы для импорта и экспорта
class UploadFileWithFormatForm(forms.Form):
    file = forms.FileField()
    file_format = forms.ChoiceField(
        choices=[('excel', 'Excel'), ('sqlite', 'SQLite')],
        label="Выберите формат файла"
    )

class ExportFormatForm(forms.Form):
    export_format = forms.ChoiceField(
        choices=[('excel', 'Excel'), ('sqlite', 'SQLite')],
        label="Выберите формат экспорта"
    )