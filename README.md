# AI-Powered Restaurant Food Ordering System

A full-stack Django web application with AI recommendations, 3-role dashboard system, and custom admin panel.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Apply migrations
python manage.py migrate

# 3. Create superuser
python manage.py createsuperuser

# 4. Run server
python manage.py runserver
```

Open http://127.0.0.1:8000/

## Roles
- **Customer** — Browse menu, cart, orders, AI recommendations, favourites
- **Owner**    — Manage menu items, view & update orders
- **Admin**    — Custom dark-theme dashboard: manage users, restaurants, all orders

## Run Tests
```bash
python manage.py test --verbosity=2
```
