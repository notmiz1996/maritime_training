# apps/training_app/serializers.py

"""
training_app - 培训管理模块序列化器
包含：TrainingTypeSerializer, TrainingClassSerializer, TrainingClassStudentSerializer
"""
from rest_framework import serializers
from .models import TrainingType, TrainingClass, TrainingClassStudent


class TrainingTypeSerializer(serializers.ModelSerializer):
    """
    培训类型序列化器
    支持嵌套展示子类型列表
    """
    children = serializers.SerializerMethodField(help_text='子类型列表')
    parent_id = serializers.PrimaryKeyRelatedField(
        source='parent',
        queryset=TrainingType.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
        help_text='父类型ID'
    )
    parent_name = serializers.CharField(
        source='parent.name',
        read_only=True,
        help_text='父类型名称'
    )

    class Meta:
        model = TrainingType
        fields = [
            'id', 'name', 'category', 'parent', 'parent_id', 'parent_name',
            'is_deleted', 'children', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_children(self, obj):
        children = obj.children.filter(is_deleted=False)
        return TrainingTypeSerializer(children, many=True).data

    def validate_category(self, value):
        valid_categories = ['驾驶', '轮机', '其他']
        if value not in valid_categories:
            raise serializers.ValidationError(
                f'分类必须是以下值之一：{", ".join(valid_categories)}'
            )
        return value

    def validate(self, attrs):
        parent = attrs.get('parent')
        if parent and parent == self.instance:
            raise serializers.ValidationError({'parent': '不能将自身设为上级类型'})
        if parent and self.instance:
            ancestor = parent.parent
            while ancestor:
                if ancestor == self.instance:
                    raise serializers.ValidationError(
                        {'parent': '不能将下级类型设为上级类型'}
                    )
                ancestor = ancestor.parent
        return attrs


class TrainingClassSerializer(serializers.ModelSerializer):
    """
    培训班序列化器
    """
    training_type_name = serializers.CharField(
        source='training_type.name',
        read_only=True,
        help_text='培训类型名称'
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True,
        help_text='状态显示'
    )

    class Meta:
        model = TrainingClass
        fields = [
            'id', 'class_no', 'maritime_system_no', 'training_type', 'training_type_name',
            'start_date', 'end_date', 'total_days', 'status', 'status_display',
            'required_attendance_rate', 'created_by', 'is_deleted',
            'checkin_enabled', 'require_location', 'location_radius',
            'training_location_lat', 'training_location_lng',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'total_days', 'created_at', 'updated_at']


class TrainingClassStudentSerializer(serializers.ModelSerializer):
    """
    培训班-学员关联序列化器
    """
    student_name = serializers.CharField(
        source='student.name',
        read_only=True,
        help_text='学员姓名'
    )
    class_no = serializers.CharField(
        source='training_class.class_no',
        read_only=True,
        help_text='班级编号'
    )

    class Meta:
        model = TrainingClassStudent
        fields = [
            'id', 'training_class', 'class_no', 'student', 'student_name',
            'enrollment_status', 'attendance_rate', 'certificate_issued',
            'certificate_no', 'enrolled_at'
        ]
        read_only_fields = ['id', 'enrolled_at']