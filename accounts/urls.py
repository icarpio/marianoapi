from django.urls import path
from . import views

urlpatterns = [
    path('api/auth/register/', views.register, name='register'),
    path('api/auth/login/', views.login_view, name='login'),
    path('api/auth/logout/', views.logout_view, name='logout'),
    path('api/auth/user/', views.current_user, name='current_user'),
    path('api/auth/update-profile/', views.update_profile, name='update_profile'),
    path('api/auth/change-password/', views.change_password, name='change_password'),
]