"""
training_app Django Admin 配置

包含：TrainingType、TrainingClass、TrainingClassStudent、CourseSchedule 的 Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import TrainingType, TrainingClass, TrainingClassStudent, CourseSchedule


# ==============================================================================
# TrainingType Admin
# ==============================================================================

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


# ==============================================================================
# TrainingClass Admin
# ==============================================================================

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


# ==============================================================================
# TrainingClassStudent Admin
# ==============================================================================

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


# ==============================================================================
# CourseSchedule Admin
# ==============================================================================

@admin.register(CourseSchedule)
class CourseScheduleAdmin(admin.ModelAdmin):
    """课程安排模型的后台管理配置"""

    # 列表页显示字段
    list_display = [
        'id', 'course_name', 'course_type_badge',
        'training_class_link', 'date', 'session_badge',
        'teacher', 'location', 'credit_hours', 'is_deleted'
    ]

    # 搜索框
    search_fields = [
        'course_name', 'teacher', 'location',
        'training_class__class_no', 'training_class__training_type__name'
    ]

    # 右侧过滤栏
    list_filter = [
        'course_type', 'session', 'date',
        'training_class__training_type', 'is_deleted'
    ]

    # 默认排序
    ordering = ['-date', 'start_time']

    # 每页数量
    list_per_page = 20

    # 日期层级导航
    date_hierarchy = 'date'

    # 字段分组展示
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'training_class', 'course_name', 'course_type')
        }),
        ('时间地点', {
            'fields': ('date', 'session', 'start_time', 'end_time', 'location')
        }),
        ('教师信息', {
            'fields': ('teacher', 'teacher_contact')
        }),
        ('容量与学分', {
            'fields': ('max_attendees', 'credit_hours')
        }),
        ('课程详情', {
            'fields': ('description', 'materials', 'prerequisite'),
            'classes': ('collapse',)
        }),
        ('备注', {
            'fields': ('remark',)
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # 只读字段
    readonly_fields = ['id', 'created_at', 'updated_at']

    # 列表页每行操作
    list_display_links = ['id', 'course_name']

    # 批量操作
    actions = ['soft_delete', 'restore', 'export_selected']

    def get_queryset(self, request):
        """优化查询，减少 N+1 问题"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'training_class',
            'training_class__training_type'
        )

    # -------------------
    # 自定义显示方法
    # -------------------

    @admin.display(description='课程类型', ordering='course_type')
    def course_type_badge(self, obj):
        """课程类型标签展示"""
        color_map = {
            'theory': '#3498db',      # 蓝色-理论课
            'practical': '#27ae60',   # 绿色-实操课
            'exam': '#e74c3c',         # 红色-考试
            'assessment': '#f39c12',  # 橙色-评估
        }
        color = color_map.get(obj.course_type, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_course_type_display()
        )

    @admin.display(description='场次', ordering='session')
    def session_badge(self, obj):
        """场次标签展示"""
        color_map = {
            'morning': '#f1c40f',     # 黄色-上午
            'afternoon': '#e67e22',   # 橙色-下午
            'evening': '#9b59b6',     # 紫色-晚上
            'full_day': '#1abc9c',    # 青色-全天
        }
        color = color_map.get(obj.session, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_session_display()
        )

    @admin.display(description='所属班级', ordering='training_class__class_no')
    def training_class_link(self, obj):
        """班级链接跳转"""
        return format_html(
            '<a href="/admin/training_app/trainingclass/{}/change/">{}</a>',
            obj.training_class.id,
            f"{obj.training_class.class_no} ({obj.training_class.training_type.name})"
        )

    # -------------------
    # 批量操作方法
    # -------------------

    @admin.action(description='软删除选中课程安排')
    def soft_delete(self, request, queryset):
        """批量软删除课程安排"""
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条课程安排记录')

    @admin.action(description='恢复选中课程安排')
    def restore(self, request, queryset):
        """批量恢复已删除的课程安排"""
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条课程安排记录')

    @admin.action(description='导出选中课程安排')
    def export_selected(self, request, queryset):
        """导出选中的课程安排（预留）"""
        self.message_user(request, f'已选中 {queryset.count()} 条课程安排待导出')

    # -------------------
    # 权限控制
    # -------------------

    def get_queryset(self, request):
        """非超级用户只能看到未删除的记录"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs

