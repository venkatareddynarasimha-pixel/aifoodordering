from django.urls import path
from . import views

urlpatterns = [
    path('cart/', views.view_cart, name='view_cart'),
    path('add-to-cart/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('place-order/', views.place_order, name='place_order'),
    path('dashboard/', views.customer_dashboard, name='customer_dashboard'),
    path('my-orders/', views.my_orders, name='my_orders'),
    path('favorite/<int:item_id>/', views.add_favorite, name='add_favorite'),
    path('favorite/remove/<int:item_id>/', views.remove_favorite, name='remove_favorite'),
    path('favorites/', views.favorites_list, name='favorites'),
]
