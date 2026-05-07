from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from .models import UserProfile


# ───────────── HOME ─────────────
def home(request):

    if request.user.is_authenticated:

        if request.user.is_superuser:
            return redirect('admin_dashboard')

        try:
            role = request.user.userprofile.role

            if role == 'ADMIN':
                return redirect('admin_dashboard')

            elif role == 'OWNER':
                return redirect('owner_dashboard')

            else:
                return redirect('customer_dashboard')

        except:
            return redirect('customer_dashboard')

    return render(request, 'home.html')


# ───────────── REGISTER ─────────────
def register_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get('username').strip()
        password = request.POST.get('password')
        role = request.POST.get('role', 'CUSTOMER')
        phone = request.POST.get('phone', '').strip()

        if not username or not password:
            return render(request, 'register.html', {'error': 'Username and password required.'})

        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists.'})

        user = User.objects.create_user(
            username=username,
            password=password
        )

        profile = user.userprofile
        profile.role = role
        profile.phone = phone
        profile.save()

        login(request, user)

        messages.success(request, f'Welcome {username}!')

        if role == 'OWNER':
            return redirect('owner_dashboard')

        return redirect('customer_dashboard')

    return render(request, 'register.html')


# ───────────── LOGIN ─────────────
def login_view(request):

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':

        username = request.POST.get('username').strip()
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user:

            login(request, user)

            if user.is_superuser:
                return redirect('admin_dashboard')

            try:
                role = user.userprofile.role

                if role == 'ADMIN':
                    return redirect('admin_dashboard')

                elif role == 'OWNER':
                    return redirect('owner_dashboard')

                else:
                    return redirect('customer_dashboard')

            except:
                return redirect('customer_dashboard')

        return render(request, 'login.html', {'error': 'Invalid username or password'})

    return render(request, 'login.html')


# ───────────── LOGOUT ─────────────
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')


# ───────────── ADMIN PERMISSION CHECK ─────────────
def _admin_required(request):

    if request.user.is_superuser:
        return True

    try:
        return request.user.userprofile.role == 'ADMIN'
    except:
        return False


# ───────────── ADMIN DASHBOARD ─────────────
@login_required
def admin_dashboard(request):

    if not _admin_required(request):
        return redirect('home')

    from restaurants.models import Restaurant, MenuItem
    from orders.models import Order

    total_revenue = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    context = {

        'total_users': User.objects.count(),
        'total_restaurants': Restaurant.objects.count(),
        'total_orders': Order.objects.count(),
        'total_menu_items': MenuItem.objects.count(),
        'total_revenue': total_revenue,

        'pending_orders': Order.objects.filter(status='PENDING').count(),
        'confirmed_orders': Order.objects.filter(status='CONFIRMED').count(),
        'delivered_orders': Order.objects.filter(status='DELIVERED').count(),

        'recent_users': User.objects.order_by('-date_joined')[:8],

        'recent_orders': Order.objects.order_by('-created_at').select_related('user','restaurant')[:8],

        'recent_restaurants': Restaurant.objects.order_by('-id').select_related('owner')[:6],

        'all_menu_items': MenuItem.objects.order_by('-id').select_related('restaurant','category')[:10],
    }

    return render(request, 'admin_dashboard.html', context)


# ───────────── ADMIN USERS ─────────────
@login_required
def admin_users(request):

    if not _admin_required(request):
        return redirect('home')

    users = User.objects.select_related('userprofile').order_by('-date_joined')

    return render(request, 'admin_users.html', {'users': users})


# ───────────── CHANGE ROLE ─────────────
@login_required
def admin_change_role(request, user_id):

    if not _admin_required(request):
        return redirect('home')

    if request.method == 'POST':

        target = get_object_or_404(User, id=user_id)
        new_role = request.POST.get('role')

        if new_role in ['CUSTOMER','OWNER','ADMIN']:
            target.userprofile.role = new_role
            target.userprofile.save()

            messages.success(request, f'{target.username} role updated.')

    return redirect('admin_users')


# ───────────── DELETE USER ─────────────
@login_required
def admin_delete_user(request, user_id):

    if not _admin_required(request):
        return redirect('home')

    if request.method == 'POST':

        target = get_object_or_404(User, id=user_id)

        if target == request.user:
            messages.error(request, "You cannot delete yourself")

        else:
            target.delete()
            messages.success(request, "User deleted")

    return redirect('admin_users')


# ───────────── ADMIN ORDERS ─────────────
@login_required
def admin_orders(request):

    if not _admin_required(request):
        return redirect('home')

    from orders.models import Order

    status_filter = request.GET.get('status','')

    orders = Order.objects.order_by('-created_at').select_related('user','restaurant')

    if status_filter in ['PENDING','CONFIRMED','DELIVERED']:
        orders = orders.filter(status=status_filter)

    return render(request, 'admin_orders.html', {
        'orders': orders,
        'status_filter': status_filter
    })


# ───────────── ADMIN RESTAURANTS ─────────────
@login_required
def admin_restaurants(request):

    if not _admin_required(request):
        return redirect('home')

    from restaurants.models import Restaurant

    restaurants = Restaurant.objects.order_by('-id').select_related('owner')

    return render(request, 'admin_restaurants.html', {'restaurants': restaurants})


# ───────────── TOGGLE RESTAURANT ─────────────
@login_required
def admin_toggle_restaurant(request, rest_id):

    if not _admin_required(request):
        return redirect('home')

    from restaurants.models import Restaurant

    rest = get_object_or_404(Restaurant, id=rest_id)

    rest.is_active = not rest.is_active
    rest.save()

    return redirect('admin_restaurants')
