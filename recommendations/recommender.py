from django.db.models import Count
from orders.models import OrderItem
from restaurants.models import MenuItem


def get_user_recommendations(user, limit=5):
    """
    Hybrid recommendation system:
    1. Items the user has ordered most (personalized)
    2. Most popular items across all users as fallback
    Returns only available items.
    """

    # 1️⃣ User-based: items ordered by this user, ranked by frequency
    user_item_ids = (
        OrderItem.objects
        .filter(order__user=user)
        .values('menu_item')
        .annotate(count=Count('menu_item'))
        .order_by('-count')
        .values_list('menu_item', flat=True)
    )

    # Preserve ordering and filter available only
    recommendations = list(
        MenuItem.objects.filter(id__in=user_item_ids, available=True)
    )

    # Re-sort by order frequency (queryset loses order from __in)
    id_order = {mid: idx for idx, mid in enumerate(user_item_ids)}
    recommendations.sort(key=lambda m: id_order.get(m.id, 999))

    # 2️⃣ Popular items fallback — FIX: use values_list + bulk fetch (no N+1 query)
    if len(recommendations) < limit:
        existing_ids = {m.id for m in recommendations}

        popular_ids = (
            OrderItem.objects
            .values('menu_item')
            .annotate(count=Count('menu_item'))
            .order_by('-count')
            .values_list('menu_item', flat=True)
        )

        needed_ids = [mid for mid in popular_ids if mid not in existing_ids][:limit]

        if needed_ids:
            popular_items = {
                m.id: m for m in MenuItem.objects.filter(id__in=needed_ids, available=True)
            }
            for mid in needed_ids:
                if mid in popular_items:
                    recommendations.append(popular_items[mid])
                if len(recommendations) >= limit:
                    break

    # 3️⃣ If still empty (brand new system), return newest available items
    if not recommendations:
        recommendations = list(
            MenuItem.objects.filter(available=True).order_by('-id')[:limit]
        )

    return recommendations[:limit]
