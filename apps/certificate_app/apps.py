from django.apps import AppConfig

class CertificateAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.certificate_app'
    verbose_name = '证书管理'
    verbose_name_plural = '证书管理模块'