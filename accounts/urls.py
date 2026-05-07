from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name='home'),

    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # ADMIN DASHBOARD
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/users/', views.admin_users, name='admin_users'),
    path('dashboard/users/<int:user_id>/role/', views.admin_change_role, name='admin_change_role'),
    path('dashboard/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),

    path('dashboard/orders/', views.admin_orders, name='admin_orders'),

    path('dashboard/restaurants/', views.admin_restaurants, name='admin_restaurants'),
    path('dashboard/restaurants/<int:rest_id>/toggle/', views.admin_toggle_restaurant, name='admin_toggle_restaurant'),

]
