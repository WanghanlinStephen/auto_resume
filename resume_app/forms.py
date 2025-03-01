from django import forms

THEME_CHOICES = [
    ('flat', 'Flat (默认)'),
    ('professional', 'Professional'),
]

class ResumeUploadForm(forms.Form):
    resume_file = forms.FileField(required=False, label="上传简历文件")
    resume_text = forms.CharField(widget=forms.Textarea, required=False, label="或者直接输入简历内容")
    theme = forms.ChoiceField(choices=THEME_CHOICES, required=False, label="选择主题")
