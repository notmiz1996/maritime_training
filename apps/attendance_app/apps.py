"""
attendance_app - 考勤管理模块
"""

from django.apps import AppConfig


class AttendanceAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.attendance_app'
    verbose_name = '考勤管理'
