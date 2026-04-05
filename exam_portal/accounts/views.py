from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        try:
            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                # Redirect based on user role
                if hasattr(user, 'role'):
                    if user.role == 'admin':
                        return redirect('/dashboard/')
                    elif user.role == 'faculty':
                        return redirect('/faculty/dashboard/')
                    elif user.role == 'student':
                        return redirect('/student/dashboard/')
                    elif user.role == 'hod':
                        return redirect('/hod/dashboard/')
                    elif user.role == 'dept_exam_controller':
                        return redirect('/dec/dashboard/')
                # Default fallback
                return redirect('/dashboard/')
            else:
                messages.error(request, "Invalid username or password")
        except Exception as e:
            # Handle database errors or other issues gracefully
            import logging
            logging.error(f"Login error: {str(e)}")
            messages.error(request, "An error occurred during login. Please try again later.")
            return render(request, "accounts/login.html")

    return render(request, "accounts/login.html")

def logout_view(request):
    logout(request)
    return redirect("accounts:login")

# AJAX endpoint for paginated, filtered user data
from django.http import JsonResponse
from .models import User
from django.core.paginator import Paginator
from django.db.models import Q

def ajax_users_list(request):

    # Get filter params
    filters = {}
    search_fields = ["username", "email", "first_name", "last_name", "role"]
    q = Q()
    for field in search_fields:
        value = request.GET.get(field, "").strip()
        if value:
            q &= Q(**{f"{field}__icontains": value})

    users = User.objects.filter(q).order_by("username")

    # Pagination
    page = int(request.GET.get("page", 1))
    paginator = Paginator(users, 25)
    page_obj = paginator.get_page(page)

    user_list = [
        {
            "username": u.username,
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role,
            "is_staff": u.is_staff,
            "is_active": u.is_active,
            "date_joined": u.date_joined.strftime('%Y-%m-%d %H:%M'),
            "last_login": u.last_login.strftime('%Y-%m-%d %H:%M') if u.last_login else "",
        }
        for u in page_obj
    ]

    return JsonResponse({
        "users": user_list,
        "num_pages": paginator.num_pages,
        "current_page": page_obj.number,
        "total_count": paginator.count,
    })
