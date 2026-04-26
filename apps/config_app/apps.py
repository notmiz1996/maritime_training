# -*- coding: utf-8 -*-
from django.apps import AppConfig


class ConfigAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.config_app'
    verbose_name = '系统配置'
