from django.urls import path, include, re_path
from rest_framework import routers
# from django.views.decorators.cache import cache_page
from . import views

router = routers.DefaultRouter()
router.register('users', views.UserInfoViewSet)
router.register('contests', views.ContestInfoViewSet, basename="Contest")
router.register('problems', views.ProblemViewSet, basename="Problem")
router.register('judges', views.JudgeViewSet, basename="Judge")

app_name = 'apiv3'
urlpatterns = [
    path('register/', views.AuthRegister.as_view()),
    path('submit/', views.SubmitData.as_view()),
    path('submitstatus/<int:pk>/', views.SubmissionStatus.as_view()),
    path('userstatus/', views.UserDetail.as_view()),
    path('', include(router.urls)),
]
