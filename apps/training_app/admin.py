from django.contrib import admin
from .models import *

@admin.register(TrainingType)
class TrainingTypeAdmin(admin.ModelAdmin):
    """培训类型模型的后台管理配置"""

    list_display = ['id', 'name', 'category', 'parent', 'children_count', 'is_deleted', 'created_at']
    search_fields = ['name', 'category']
    list_filter = ['category', 'is_deleted', 'created_at']
    ordering = ['category', 'name']
    list_per_page = 50

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'name', 'category')
        }),
        ('层级结构', {
            'fields': ('parent',),
            'description': '选择上级培训类型，支持多级分类'
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'created_at', 'updated_at']

    actions = ['soft_delete', 'restore']

    @admin.display(description='子类型数量')
    def children_count(self, obj):
        return obj.children.count()
    children_count.short_description = '子类型数'

    @admin.action(description='软删除选中类型')
    def soft_delete(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条记录')

    @admin.action(description='恢复选中类型')
    def restore(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条记录')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs


@admin.register(TrainingClass)
class TrainingClassAdmin(admin.ModelAdmin):
    """培训班模型的后台管理配置"""

    list_display = [
        'id', 'class_no', 'training_type', 'start_date', 'end_date',
        'total_days', 'status', 'required_attendance_rate',
        'checkin_enabled', 'is_deleted', 'created_at'
    ]
    search_fields = ['class_no', 'maritime_system_no', 'training_type__name']
    list_filter = ['status', 'training_type', 'is_deleted', 'checkin_enabled', 'created_at']
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'start_date'

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'class_no', 'maritime_system_no', 'training_type', 'created_by')
        }),
        ('时间安排', {
            'fields': ('start_date', 'end_date', 'total_days')
        }),
        ('状态与考勤', {
            'fields': ('status', 'required_attendance_rate', 'checkin_enabled', 'require_location')
        }),
        ('签到位置配置', {
            'fields': ('location_radius', 'training_location_lat', 'training_location_lng'),
            'description': '设置培训地点坐标和允许签到半径',
            'classes': ('collapse',)
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'total_days', 'created_at', 'updated_at']

    actions = ['soft_delete', 'restore']

    @admin.action(description='软删除选中班级')
    def soft_delete(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条记录')

    @admin.action(description='恢复选中班级')
    def restore(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条记录')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs


@admin.register(TrainingClassStudent)
class TrainingClassStudentAdmin(admin.ModelAdmin):
    """培训班-学员关联模型的后台管理配置"""

    list_display = [
        'id', 'student_link', 'training_class_link',
        'enrollment_status', 'attendance_rate',
        'certificate_issued', 'certificate_no', 'enrolled_at'
    ]
    search_fields = [
        'student__name', 'student__id_card',
        'training_class__class_no', 'certificate_no'
    ]
    list_filter = [
        'enrollment_status', 'certificate_issued',
        'training_class__training_type', 'enrolled_at'
    ]
    ordering = ['-enrolled_at']
    list_per_page = 50

    fieldsets = (
        ('关联信息', {
            'fields': ('id', 'training_class', 'student', 'enrollment_status')
        }),
        ('培训结果', {
            'fields': ('attendance_rate', 'certificate_issued', 'certificate_no')
        }),
        ('报名信息', {
            'fields': ('enrolled_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'enrolled_at']

    actions = ['confirm_enrollment', 'reject_enrollment']

    @admin.display(description='学员', ordering='student__name')
    def student_link(self, obj):
        return format_html(
            '<a href="/admin/student_app/student/{}/change/">{}</a>',
            obj.student.id, obj.student.name
        )

    @admin.display(description='培训班', ordering='training_class__class_no')
    def training_class_link(self, obj):
        return format_html(
            '<a href="/admin/training_app/trainingclass/{}/change/">{}</a>',
            obj.training_class.id, obj.training_class.class_no
        )

    @admin.action(description='确认选中学员报名')
    def confirm_enrollment(self, request, queryset):
        count = queryset.update(enrollment_status='confirmed')
        self.message_user(request, f'已确认 {count} 条报名记录')

    @admin.action(description='拒绝选中学员报名')
    def reject_enrollment(self, request, queryset):
        count = queryset.update(enrollment_status='rejected')
        self.message_user(request, f'已拒绝 {count} 条报名记录')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('student', 'training_class')
