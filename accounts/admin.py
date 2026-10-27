from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Notification, Profile

User = get_user_model()


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [ProfileInline]
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "city", "state", "created_at")
    search_fields = ("user__username", "user__email", "phone", "city")
    list_filter = ("state",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("user__username",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "kind", "is_read", "created_at")
    list_filter = ("kind", "is_read", "created_at")
    search_fields = ("title", "message", "user__username")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)
    actions = ["mark_read", "mark_unread"]

    @admin.action(description="Mark selected notifications as read")
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected notifications as unread")
    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)
