from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', include('accounts.urls')),      # put FIRST
    path('', include('orders.urls')),
    path('', include('restaurants.urls')),
]
