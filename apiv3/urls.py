from django.urls import path, include, re_path
from rest_framework import routers
# from django.views.decorators.cache import cache_page
from . import views

router = routers.DefaultRouter()
router.register('users', views.UserInfoViewSet)
router.register('contests', views.ContestInfoViewSet, basename="contest")
router.register('problems', views.ProblemViewSet)
router.register('problemgroups', views.ProblemGroupViewSet, basename="problemgroup")
router.register('problemtypes', views.ProblemTypeViewSet, basename="problemtype")
router.register('judges', views.JudgeViewSet, basename="judge")

app_name = 'apiv3'
urlpatterns = [
    path('changepassword/', views.UserPassword.as_view()),
    path('requestpasswordreset/', views.SendResetPasswordEmail.as_view()),
    path('passwordreset/', views.ResetPassword.as_view()),
    path('register/', views.AuthRegister.as_view()),
    path('submit/', views.SubmitData.as_view()),
    path('submitstatus/<int:pk>/', views.SubmissionStatus.as_view()),
    path('userstatus/', views.UserDetail.as_view()),
    path('selectedproblems/', views.SelectedProblems.as_view()),
    path('', include(router.urls)),
]
