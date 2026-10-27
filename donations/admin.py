from django.contrib import admin

from .models import Donation, DonationCategory, DonationDrive


@admin.register(DonationCategory)
class DonationCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "icon", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("order", "name")


@admin.register(DonationDrive)
class DonationDriveAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "location", "start_date", "end_date",
                    "collected_quantity", "goal_quantity", "is_active")
    list_editable = ("is_active",)
    list_filter = ("category", "is_active", "end_date")
    search_fields = ("title", "description", "location", "organizer")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("end_date",)


@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("reference", "donor_name", "user", "category", "amount", "quantity",
                    "campaign", "cause", "status", "created_at")
    list_filter = ("status", "category", "created_at", "is_anonymous")
    search_fields = ("reference", "donor_name", "donor_email", "user__username",
                     "campaign__title", "cause__title")
    readonly_fields = ("reference", "is_demo", "created_at", "updated_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    list_select_related = ("user", "category", "campaign", "cause")
    actions = ["mark_completed", "mark_cancelled"]

    @admin.action(description="Mark selected item donations as completed")
    def mark_completed(self, request, queryset):
        queryset.filter(status=Donation.Status.PENDING).update(status=Donation.Status.COMPLETED)

    @admin.action(description="Mark selected pending donations as cancelled")
    def mark_cancelled(self, request, queryset):
        queryset.filter(status=Donation.Status.PENDING).update(status=Donation.Status.CANCELLED)
