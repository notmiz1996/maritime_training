#### -*- coding: utf-8 -*-
"""
organization_app - View 层

职责：
- 接收 HTTP 请求
- 调用 Serializer 做数据验证
- 调用 Service 层处理业务逻辑
- 返回 JSON 响应
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q

from .models import Organization, Personnel, Position, PersonnelPosition
from .serializers import (
    OrganizationSerializer,
    OrganizationTreeSerializer,
    PersonnelSerializer,
    PersonnelListSerializer,
    PositionSerializer,
    PersonnelPositionSerializer,
    AssignPositionSerializer,
)


#### ========== Organization ViewSet ==========

class OrganizationViewSet(viewsets.ModelViewSet):
    """
    组织架构 API

    权限：需要登录

    支持的查询参数：
    - ?parent=ID：查询某组织的直接子组织
    - ?ancestor=ID&depth=N：查询某组织的所有后代（最深N层）
    - ?search=关键词：搜索组织名称

    特殊动作：
    - GET /organizations/tree/：获取完整树形结构
    - GET /organizations/{id}/descendants/：获取后代组织
    """

    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """默认只返回未删除的组织"""
        queryset = Organization.objects.filter(is_deleted=False)

        # 按 parent 过滤
        parent_id = self.request.query_params.get('parent')
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)

        # 按 ancestor（祖先）过滤，获取后代组织
        ancestor_id = self.request.query_params.get('ancestor')
        if ancestor_id:
            try:
                ancestor = Organization.objects.get(id=ancestor_id, is_deleted=False)
                max_depth = int(self.request.query_params.get('depth', 10))
                # 使用 path 前缀匹配
                queryset = queryset.filter(
                    path__startswith=ancestor.path,
                    level__lte=ancestor.level + max_depth
                ).exclude(id=ancestor.id)
            except Organization.DoesNotExist:
                queryset = queryset.none()

        # 搜索名称
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset.order_by('path')

    def perform_destroy(self, instance):
        """软删除（禁止物理删除）"""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])

    @action(detail=False, methods=['get'], url_path='tree')
    def tree(self, request):
        """获取完整树形结构（仅根节点）"""
        # 获取所有根节点（parent 为 null）
        root_orgs = Organization.objects.filter(
            is_deleted=False,
            parent__isnull=True
        ).order_by('name')

        serializer = OrganizationTreeSerializer(root_orgs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='descendants')
    def descendants(self, request, pk=None):
        """获取指定组织的所有后代"""
        try:
            org = Organization.objects.get(id=pk, is_deleted=False)
        except Organization.DoesNotExist:
            return Response(
                {'detail': '组织不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        max_depth = int(request.query_params.get('depth', 10))

        descendants = Organization.objects.filter(
            path__startswith=org.path,
            level__gt=org.level,
            level__lte=org.level + max_depth,
            is_deleted=False
        ).order_by('path')

        serializer = OrganizationSerializer(descendants, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='children')
    def children(self, request, pk=None):
        """获取指定组织的直接子节点"""
        try:
            org = Organization.objects.get(id=pk, is_deleted=False)
        except Organization.DoesNotExist:
            return Response(
                {'detail': '组织不存在'},
                status=status.HTTP_404_NOT_FOUND
            )
        children = Organization.objects.filter(
            parent=org,
            is_deleted=False
        ).order_by('name')

        serializer = OrganizationSerializer(children, many=True)
        return Response(serializer.data)


class PersonnelViewSet(viewsets.ModelViewSet):
    """
    人员管理 API
    权限：需要登录
    支持的查询参数：
    - ?organization=ID：按组织过滤
    - ?search=关键词：搜索姓名或手机号
    特殊动作：
    - POST /personnels/{id}/assign-position/：分配职务
    - DELETE /personnels/{id}/remove-position/：移除职务
    """


    serializer_class = PersonnelSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)


    def get_queryset(self):
        queryset = Personnel.objects.filter(is_deleted=False)

        # 按组织过滤
        org_id = self.request.query_params.get('organization')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search)
            )

        return queryset.select_related('organization', 'user').order_by('-created_at')


    def get_serializer_class(self):
        """list 接口使用简化版 serializer"""
        if self.action == 'list':
            return PersonnelListSerializer
        return PersonnelSerializer


    def perform_destroy(self, instance):
        """软删除"""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])


    @action(detail=True, methods=['post'], url_path='assign-position')
    def assign_position(self, request, pk=None):
        """分配职务"""
        try:
            personnel = Personnel.objects.get(id=pk, is_deleted=False)
        except Personnel.DoesNotExist:
            return Response(
                {'detail': '人员不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AssignPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        position_id = serializer.validated_data['position_id']
        is_primary = serializer.validated_data.get('is_primary', False)

        try:
            position = Position.objects.get(id=position_id, is_deleted=False)
        except Position.DoesNotExist:
            return Response(
                {'detail': '职务不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 检查是否已存在关联
        exists = PersonnelPosition.objects.filter(
            personnel=personnel,
            position=position
        ).exists()

        if exists:
            return Response(
                {'detail': '该人员已有此职务'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 创建关联
        pp = PersonnelPosition.objects.create(
            personnel=personnel,
            position=position,
            is_primary=is_primary,
            is_active=True
        )

        return Response(
            PersonnelPositionSerializer(pp).data,
            status=status.HTTP_201_CREATED
        )


    @action(detail=True, methods=['delete'], url_path='remove-position')
    def remove_position(self, request, pk=None):
        """移除职务"""
        try:
            personnel = Personnel.objects.get(id=pk, is_deleted=False)
        except Personnel.DoesNotExist:
            return Response(
                {'detail': '人员不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        position_id = request.query_params.get('position_id')
        if not position_id:
            return Response(
                {'detail': '缺少 position_id 参数'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            pp = PersonnelPosition.objects.get(
                personnel=personnel,
                position_id=position_id
            )
            pp.is_active = False
            pp.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except PersonnelPosition.DoesNotExist:
            return Response(
                {'detail': '该人员没有此职务'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=['get'], url_path='positions')
    def positions(self, request, pk=None):
        """获取人员的所有职务"""
        try:
            personnel = Personnel.objects.get(id=pk, is_deleted=False)
        except Personnel.DoesNotExist:
            return Response(
                {'detail': '人员不存在'},
                status=status.HTTP_404_NOT_FOUND
            )

        pps = PersonnelPosition.objects.filter(
            personnel=personnel,
            is_active=True
        ).select_related('position')

        serializer = PersonnelPositionSerializer(pps, many=True)
        return Response(serializer.data)


class PositionViewSet(viewsets.ModelViewSet):
    """
    职务管理 API
    """


    serializer_class = PositionSerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        queryset = Position.objects.filter(is_deleted=False)

        # 按组织过滤
        org_id = self.request.query_params.get('organization')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)

        # 搜索
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )

        return queryset.select_related('organization').order_by('organization__path', 'code')


    def perform_destroy(self, instance):
        """软删除"""
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])


class PersonnelPositionViewSet(viewsets.ModelViewSet):
    """
    人员-职务关联管理 API
    """


    serializer_class = PersonnelPositionSerializer
    permission_classes = [IsAuthenticated]


    def get_queryset(self):
        queryset = PersonnelPosition.objects.filter(is_active=True)

        # 按人员过滤
        personnel_id = self.request.query_params.get('personnel')
        if personnel_id:
            queryset = queryset.filter(personnel_id=personnel_id)

        # 按职务过滤
        position_id = self.request.query_params.get('position')
        if position_id:
            queryset = queryset.filter(position_id=position_id)

        return queryset.select_related('personnel', 'position').order_by('-created_at')