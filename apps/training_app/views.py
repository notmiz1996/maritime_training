# apps/training_app/views.py

"""
training_app - 培训管理模块视图
包含：TrainingTypeViewSet, TrainingClassViewSet, TrainingClassStudentViewSet
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Prefetch

from .models import TrainingType, TrainingClass, TrainingClassStudent
from .serializers import TrainingTypeSerializer, TrainingClassSerializer, TrainingClassStudentSerializer
from apps.organization_app.permissions import MatrixPermission  # 复用 organization_app 的权限类


class TrainingTypeViewSet(viewsets.ModelViewSet):
    """
    培训类型 ViewSet

    支持的操作：
    - GET /api/training-types/ - 列出所有培训类型
    - POST /api/training-types/ - 创建培训类型
    - GET /api/training-types/{id}/ - 获取单个培训类型
    - PUT/PATCH /api/training-types/{id}/ - 更新培训类型
    - DELETE /api/training-types/{id}/ - 软删除培训类型
    - GET /api/training-types/tree/ - 获取树形结构

    过滤参数：
    - ?category=驾驶 - 按分类筛选
    - ?parent=1 - 按父类型筛选
    - ?is_deleted=false - 显示已删除的记录
    """
    serializer_class = TrainingTypeSerializer
    permission_classes = [IsAuthenticated, MatrixPermission]

    def get_queryset(self):
        """
        支持过滤查询
        """
        queryset = TrainingType.objects.all()

        # 按分类筛选
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # 按父类型筛选
        parent = self.request.query_params.get('parent')
        if parent:
            queryset = queryset.filter(parent_id=parent)

        # 默认不显示已删除的记录
        if not self.request.query_params.get('is_deleted'):
            queryset = queryset.filter(is_deleted=False)

        return queryset.order_by('category', 'name')

    def destroy(self, request, *args, **kwargs):
        """
        软删除：设置 is_deleted=True
        """
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """
        获取树形结构

        GET /api/training-types/tree/

        返回嵌套的 JSON 结构，示例：
        [
            {
                "id": 1,
                "name": "驾驶岗位",
                "category": "驾驶",
                "children": [
                    {"id": 2, "name": "一类船长", "children": []}
                ]
            }
        ]
        """
        # 获取所有根节点（没有父类型的顶级类型）
        root_types = TrainingType.objects.filter(
            parent__isnull=True,
            is_deleted=False
        ).order_by('category', 'name')

        # 递归构建树
        def build_tree(t_type):
            children = TrainingType.objects.filter(
                parent=t_type,
                is_deleted=False
            ).order_by('name')

            node = {
                'id': t_type.id,
                'name': t_type.name,
                'category': t_type.category,
                'children': [build_tree(child) for child in children]
            }
            return node

        tree_data = [build_tree(root) for root in root_types]
        return Response(tree_data)

"""
training_app - 培训管理模块视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import TrainingType, TrainingClass, TrainingClassStudent
from .serializers import (
    TrainingTypeSerializer,
    TrainingClassSerializer,
    TrainingClassStudentSerializer
)


class TrainingTypeViewSet(viewsets.ModelViewSet):
    """培训类型 ViewSet"""
    serializer_class = TrainingTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TrainingType.objects.all()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        parent = self.request.query_params.get('parent')
        if parent:
            queryset = queryset.filter(parent_id=parent)
        if not self.request.query_params.get('is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        return queryset.order_by('category', 'name')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        root_types = TrainingType.objects.filter(
            parent__isnull=True,
            is_deleted=False
        ).order_by('category', 'name')

        def build_tree(t_type):
            children = TrainingType.objects.filter(
                parent=t_type,
                is_deleted=False
            ).order_by('name')
            return {
                'id': t_type.id,
                'name': t_type.name,
                'category': t_type.category,
                'children': [build_tree(child) for child in children]
            }

        tree_data = [build_tree(root) for root in root_types]
        return Response(tree_data)


class TrainingClassViewSet(viewsets.ModelViewSet):
    """培训班 ViewSet"""
    serializer_class = TrainingClassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TrainingClass.objects.all()
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        training_type = self.request.query_params.get('training_type')
        if training_type:
            queryset = queryset.filter(training_type_id=training_type)
        if not self.request.query_params.get('is_deleted'):
            queryset = queryset.filter(is_deleted=False)
        return queryset.order_by('-created_at')

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted', 'updated_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class TrainingClassStudentViewSet(viewsets.ModelViewSet):
    """培训班-学员关联 ViewSet"""
    serializer_class = TrainingClassStudentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = TrainingClassStudent.objects.all()
        training_class = self.request.query_params.get('training_class')
        if training_class:
            queryset = queryset.filter(training_class_id=training_class)
        student = self.request.query_params.get('student')
        if student:
            queryset = queryset.filter(student_id=student)
        return queryset.order_by('-enrolled_at')