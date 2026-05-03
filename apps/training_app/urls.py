# apps/training_app/urls.py

"""
training_app - 培训管理模块路由配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TrainingTypeViewSet, TrainingClassViewSet, TrainingClassStudentViewSet

app_name = 'training_app'

router = DefaultRouter()
router.register(r'training-types', TrainingTypeViewSet, basename='trainingtype')
router.register(r'training-classes', TrainingClassViewSet, basename='trainingclass')
router.register(r'training-class-students', TrainingClassStudentViewSet, basename='trainingclass_student')

urlpatterns = [
    path('', include(router.urls)),
]