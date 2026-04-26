"""
attendance_app - 考勤管理模块 Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """考勤记录的后台管理配置"""

    list_display = [
        'id', 'student_link', 'training_class_link',
        'date', 'session_badge', 'status_badge',
        'check_in', 'check_out', 'duration_display',
        'created_at'
    ]
    search_fields = [
        'student__name', 'student__id_card',
        'student__student_no', 'training_class__class_no',
        'remark'
    ]
    list_filter = [
        'status', 'session', 'date',
        'training_class__training_type',
        ('check_in', admin.DateFieldListFilter),
    ]
    ordering = ['-date', '-created_at']
    list_per_page = 50
    date_hierarchy = 'date'

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'training_class', 'student', 'date', 'session')
        }),
        ('考勤信息', {
            'fields': ('course_schedule', 'status', 'remark')
        }),
        ('签到信息', {
            'fields': ('check_in', 'check_out'),
            'classes': ('collapse',)
        }),
        ('系统信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'created_at', 'updated_at']

    actions = [
        'mark_present',
        'mark_late',
        'mark_absent',
        'export_attendance',
    ]

    list_select_related = ['student', 'training_class', 'course_schedule']

    @admin.display(description='学员', ordering='student__name')
    def student_link(self, obj):
        if not obj.student:
            return '-'
        url = f'/admin/student_app/student/{obj.student.id}/change/'
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.student.name
        )

    @admin.display(description='班级', ordering='training_class__class_no')
    def training_class_link(self, obj):
        if not obj.training_class:
            return '-'
        url = f'/admin/training_app/trainingclass/{obj.training_class.id}/change/'
        return format_html(
            '<a href="{}">{}</a>',
            url, obj.training_class.name
        )

    @admin.display(description='场次')
    def session_badge(self, obj):
        colors = {'morning': '#1890ff', 'afternoon': '#52c41a'}
        color = colors.get(obj.session, '#999')
        return format_html(
            '<span style="background-color:{};color:white;padding:2px 8px;border-radius:4px;font-size:12px;">{}</span>',
            color, obj.get_session_display()
        )

    @admin.display(description='状态')
    def status_badge(self, obj):
        colors = {
            'present': '#52c41a',
            'late': '#faad14',
            'absent': '#f5222d',
            'leave': '#1890ff'
        }
        color = colors.get(obj.status, '#999')
        return format_html(
            '<span style="background-color:{};color:white;padding:2px 8px;border-radius:4px;font-size:12px;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description='时长')
    def duration_display(self, obj):
        minutes = obj.duration_minutes
        if minutes > 0:
            hours = minutes // 60
            mins = minutes % 60
            return f"{hours}h {mins}m"
        return '-'

    @admin.action(description='标记为正常签到')
    def mark_present(self, request, queryset):
        count = queryset.update(status='present')
        self.message_user(request, f'已更新 {count} 条记录为正常签到')

    @admin.action(description='标记为迟到')
    def mark_late(self, request, queryset):
        count = queryset.update(status='late')
        self.message_user(request, f'已更新 {count} 条记录为迟到')

    @admin.action(description='标记为缺勤')
    def mark_absent(self, request, queryset):
        count = queryset.update(status='absent')
        self.message_user(request, f'已更新 {count} 条记录为缺勤')

    @admin.action(description='导出考勤数据')
    def export_attendance(self, request, queryset):
        self.message_user(request, '导出功能开发中')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'student', 'training_class', 'course_schedule'
        ).filter(is_deleted=False)