from django.urls import path
from . import views

urlpatterns = [

    # Customer menu
    path('menu/', views.menu_list, name='menu'),

    # Owner dashboard
    path('owner-dashboard/', views.owner_dashboard, name='owner_dashboard'),

    # Owner creates a restaurant
    path('owner/add-restaurant/', views.add_restaurant, name='add_restaurant'),

    path('owner/add-category/', views.add_category, name='add_category'),

    # Owner adds menu items
    path('owner/add-item/', views.add_menu_item, name='add_menu_item'),

    # Owner enables / disables menu item
    path('owner/toggle-item/<int:item_id>/', views.toggle_item_availability, name='toggle_item'),

    # Owner updates order status
    path('owner/update-order/<int:order_id>/', views.update_order_status, name='update_order_status'),

]
