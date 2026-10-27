from django.contrib import admin

from .models import Campaign, CampaignUpdate, SavedCampaign


class CampaignUpdateInline(admin.TabularInline):
    model = CampaignUpdate
    extra = 0


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "title", "creator", "category", "target_amount", "amount_raised",
        "contributors_count", "deadline", "status", "is_verified", "is_featured",
    )
    list_editable = ("status", "is_verified", "is_featured")
    list_filter = ("status", "is_verified", "is_featured", "category", "deadline", "created_at")
    search_fields = ("title", "short_description", "description", "creator__username", "location")
    readonly_fields = ("slug", "amount_raised", "contributors_count", "created_at", "updated_at")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"
    inlines = [CampaignUpdateInline]
    actions = ["verify_campaigns", "unverify_campaigns", "close_campaigns", "reactivate_campaigns"]

    @admin.action(description="Verify selected campaigns")
    def verify_campaigns(self, request, queryset):
        queryset.update(is_verified=True)

    @admin.action(description="Remove verification from selected campaigns")
    def unverify_campaigns(self, request, queryset):
        queryset.update(is_verified=False)

    @admin.action(description="Close selected campaigns")
    def close_campaigns(self, request, queryset):
        queryset.exclude(status=Campaign.Status.CANCELLED).update(status=Campaign.Status.CLOSED)

    @admin.action(description="Re-activate closed campaigns")
    def reactivate_campaigns(self, request, queryset):
        queryset.filter(status=Campaign.Status.CLOSED).update(status=Campaign.Status.ACTIVE)


@admin.register(CampaignUpdate)
class CampaignUpdateAdmin(admin.ModelAdmin):
    list_display = ("title", "campaign", "created_at")
    search_fields = ("title", "body", "campaign__title")
    list_filter = ("created_at",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(SavedCampaign)
class SavedCampaignAdmin(admin.ModelAdmin):
    list_display = ("user", "campaign", "created_at")
    search_fields = ("user__username", "campaign__title")
    list_filter = ("created_at",)
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)
