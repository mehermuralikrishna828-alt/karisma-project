from datetime import timedelta

from django import forms
from django.utils import timezone

from core.forms import BootstrapFormMixin

from .models import Campaign, CampaignUpdate


class CampaignForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Campaign
        fields = (
            "title",
            "short_description",
            "category",
            "location",
            "beneficiary",
            "target_amount",
            "deadline",
            "description",
            "impact_info",
            "image",
        )
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 7}),
            "impact_info": forms.Textarea(attrs={"rows": 4}),
            "target_amount": forms.NumberInput(attrs={"min": "1000", "step": "100"}),
        }
        help_texts = {
            "short_description": "One line shown on campaign cards (max 200 characters).",
            "impact_info": "Explain what the funds will achieve, e.g. '₹500 feeds a family for a week'.",
            "beneficiary": "Who will benefit? e.g. 'Students of Govt. Primary School, Wayanad'.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        tomorrow = timezone.localdate() + timedelta(days=1)
        self.fields["deadline"].widget.attrs["min"] = tomorrow.isoformat()

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 10:
            raise forms.ValidationError("Please use a descriptive title (at least 10 characters).")
        return title

    def clean_description(self):
        description = self.cleaned_data["description"].strip()
        if len(description) < 80:
            raise forms.ValidationError("Tell your story in at least 80 characters.")
        return description

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "size") and image.size > 3 * 1024 * 1024:
            raise forms.ValidationError("Please upload an image smaller than 3 MB.")
        return image


class CampaignEditForm(CampaignForm):
    """Edit form: owners may also close or cancel a campaign."""

    class Meta(CampaignForm.Meta):
        fields = CampaignForm.Meta.fields + ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = [
            (Campaign.Status.ACTIVE.value, "Active"),
            (Campaign.Status.CLOSED.value, "Closed"),
            (Campaign.Status.CANCELLED.value, "Cancelled"),
        ]
        if self.instance.status == Campaign.Status.FUNDED:
            allowed.insert(1, (Campaign.Status.FUNDED.value, "Fully funded"))
        self.fields["status"].choices = allowed
        # The min date hint only makes sense when the deadline is being changed.
        self.fields["deadline"].widget.attrs.pop("min", None)


class CampaignUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = CampaignUpdate
        fields = ("title", "body")
        widgets = {"body": forms.Textarea(attrs={"rows": 4})}
