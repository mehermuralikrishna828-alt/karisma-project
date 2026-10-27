from django.contrib import admin

from .models import PhilanthropyCause


@admin.register(PhilanthropyCause)
class PhilanthropyCauseAdmin(admin.ModelAdmin):
    list_display = (
        "title", "category", "target_amount", "amount_raised",
        "supporters_count", "is_featured", "is_active",
    )
    list_editable = ("is_featured", "is_active")
    list_filter = ("category", "is_featured", "is_active", "created_at")
    search_fields = ("title", "description", "beneficiary_info")
    readonly_fields = ("slug", "amount_raised", "supporters_count", "created_at", "updated_at")
    filter_horizontal = ("followers",)
    ordering = ("title",)
