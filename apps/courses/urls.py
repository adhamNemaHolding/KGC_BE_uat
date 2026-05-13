from django.urls import path

from . import views

urlpatterns = [
    path("", views.list_courses, name="list-courses"),
    path("create/", views.create_course, name="create-course"),
    path("sitecore/", views.list_sitecore_courses, name="sitecore-courses"),
    path("<uuid:course_id>/", views.get_course, name="get-course"),
    # Legacy synced data
    path("enrollments/", views.list_enrollments, name="list-enrollments"),
    path("ratings/", views.list_ratings, name="list-ratings"),
    path("candidates/", views.list_candidates, name="list-candidates"),
    # External MSSQL — customer course orders
    path("my-orders/", views.customer_orders, name="customer-orders"),
    path("orders/<uuid:customer_id>/", views.customer_orders_by_id, name="customer-orders-by-id"),
]
