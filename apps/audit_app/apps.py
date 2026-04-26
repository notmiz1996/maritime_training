# -*- coding: utf-8 -*-
from django.apps import AppConfig

class AuditAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit_app'
    verbose_name = '审计追踪'