# -*- coding: utf-8 -*-
"""
organization_app - URL 配置
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    OrganizationViewSet,
    PersonnelViewSet,
    PositionViewSet,
    PersonnelPositionViewSet,
)

# 创建路由
router = DefaultRouter()

# 注册 ViewSet
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'personnels', PersonnelViewSet, basename='personnel')
router.register(r'positions', PositionViewSet, basename='position')
router.register(r'personnel-positions', PersonnelPositionViewSet, basename='personnel-position')

urlpatterns = [
    # 将 router URLs 包含进来
    # 最终 URL 格式：
    #   /api/organizations/
    #   /api/organizations/{pk}/
    #   /api/organizations/{pk}/tree/
    #   /api/organizations/{pk}/descendants/
    #   /api/organizations/{pk}/children/
    #   /api/personnels/
    #   /api/personnels/{pk}/
    #   /api/personnels/{pk}/assign-position/
    #   /api/personnels/{pk}/remove-position/
    #   /api/personnels/{pk}/positions/
    #   /api/positions/
    #   /api/positions/{pk}/
    #   /api/personnel-positions/
    #   /api/personnel-positions/{pk}/
    path('', include(router.urls)),
]