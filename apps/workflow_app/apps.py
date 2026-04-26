from django.apps import AppConfig

class WorkflowAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.workflow_app'
    verbose_name = '工作流管理'
    verbose_name_plural = '工作流管理模块'