from django.apps import AppConfig


class StudentAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.student_app'
    verbose_name = '学员信息'
