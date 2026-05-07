from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Cart, CartItem, Order, OrderItem, Favorite
from restaurants.models import MenuItem, Restaurant


@login_required
def add_to_cart(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id, available=True)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        menu_item=item
    )

    if not created:
        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, f'"{item.name}" added to cart.')
    return redirect('view_cart')


@login_required
def remove_from_cart(request, item_id):
    """NEW FEATURE: Remove a specific item from cart."""
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    name = cart_item.menu_item.name
    cart_item.delete()
    messages.success(request, f'"{name}" removed from cart.')
    return redirect('view_cart')


@login_required
def update_cart_quantity(request, item_id):
    """NEW FEATURE: Update quantity of a cart item."""
    cart = get_object_or_404(Cart, user=request.user)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'increase':
            cart_item.quantity += 1
            cart_item.save()
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()

    return redirect('view_cart')


@login_required
def view_cart(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart).select_related('menu_item')
    total = sum(i.total_price() for i in items)

    return render(request, 'cart.html', {
        'items': items,
        'total': total
    })


@login_required
def place_order(request):
    cart = get_object_or_404(Cart, user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('menu_item__restaurant')

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('view_cart')

    restaurant = cart_items.first().menu_item.restaurant
    total = sum(item.total_price() for item in cart_items)

    order = Order.objects.create(
        user=request.user,
        restaurant=restaurant,
        total_amount=total
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            menu_item=item.menu_item,
            quantity=item.quantity
        )

    cart_items.delete()
    messages.success(request, f'Order #{order.id} placed successfully!')
    return render(request, 'order_success.html', {'order': order})


@login_required
def customer_dashboard(request):
    # FIX: Now properly calls the recommender
    from recommendations.recommender import get_user_recommendations
    recommended_items = get_user_recommendations(request.user, limit=5)

    orders = Order.objects.filter(user=request.user).order_by('-created_at')[:10]
    favorites = Favorite.objects.filter(user=request.user).select_related('menu_item')

    return render(request, 'customer_dashboard.html', {
        'orders': orders,
        'favorites': favorites,
        'recommended_items': recommended_items,
    })


@login_required
def my_orders(request):
    """NEW: Dedicated order history page with status filter."""
    status_filter = request.GET.get('status', '')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    if status_filter in ['PENDING', 'CONFIRMED', 'DELIVERED']:
        orders = orders.filter(status=status_filter)

    return render(request, 'my_orders.html', {
        'orders': orders,
        'status_filter': status_filter,
    })


@login_required
def add_favorite(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id)
    _, created = Favorite.objects.get_or_create(user=request.user, menu_item=item)
    if created:
        messages.success(request, f'"{item.name}" added to favourites.')
    else:
        messages.info(request, f'"{item.name}" is already in your favourites.')
    return redirect('menu')


@login_required
def remove_favorite(request, item_id):
    """NEW FEATURE: Remove item from favourites."""
    fav = get_object_or_404(Favorite, id=item_id, user=request.user)
    name = fav.menu_item.name
    fav.delete()
    messages.success(request, f'"{name}" removed from favourites.')
    return redirect('favorites')


@login_required
def favorites_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('menu_item__category')
    return render(request, 'favorites.html', {'favorites': favorites})
