from datetime import timedelta
from decimal import Decimal

from django import forms
from django.core.validators import RegexValidator
from django.utils import timezone

from core.forms import BootstrapFormMixin

from .constants import MAX_DONATION, MIN_DONATION

PHONE_VALIDATOR = RegexValidator(
    r"^(\+91[\-\s]?)?[6-9]\d{9}$", "Enter a valid 10-digit Indian mobile number."
)

PAYMENT_METHODS = [
    ("upi", "UPI (demo)"),
    ("card", "Credit / Debit card (demo)"),
    ("netbanking", "Net banking (demo)"),
]


# ---------------------------------------------------------------------------
# Money donation flow
# ---------------------------------------------------------------------------
class AmountForm(BootstrapFormMixin, forms.Form):
    amount = forms.DecimalField(
        label="Donation amount (₹)",
        min_value=Decimal(MIN_DONATION),
        max_value=Decimal(MAX_DONATION),
        max_digits=9,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "1", "inputmode": "decimal", "placeholder": "Enter amount"}),
        error_messages={
            "min_value": f"The minimum donation is ₹{MIN_DONATION}.",
            "max_value": f"A single donation cannot exceed ₹{MAX_DONATION:,}.",
        },
    )


class DonorDetailsForm(BootstrapFormMixin, forms.Form):
    donor_name = forms.CharField(label="Full name", max_length=100)
    donor_email = forms.EmailField(label="Email address")
    donor_phone = forms.CharField(
        label="Mobile number (optional)", max_length=20, required=False, validators=[PHONE_VALIDATOR]
    )
    payment_method = forms.ChoiceField(
        label="Demo payment method", choices=PAYMENT_METHODS, initial="upi",
        help_text="Nothing is charged. This only simulates the experience.",
    )
    message = forms.CharField(
        label="Message of support (optional)",
        max_length=300,
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    is_anonymous = forms.BooleanField(
        label="Hide my name from public supporter lists", required=False
    )


# ---------------------------------------------------------------------------
# Item donation forms (one per category)
# ---------------------------------------------------------------------------
class BaseItemDonationForm(BootstrapFormMixin, forms.Form):
    """Shared donor fields. Subclasses add the item-specific fields."""

    item_fields = ()      # field names shown first
    detail_fields = ()    # field names stored in Donation.details
    submit_label = "Submit donation"
    intro = ""

    donor_name = forms.CharField(label="Your name", max_length=100)
    donor_email = forms.EmailField(label="Email address")
    donor_phone = forms.CharField(label="Mobile number", max_length=20, validators=[PHONE_VALIDATOR])
    city = forms.CharField(label="City", max_length=80)
    pickup_address = forms.CharField(
        label="Pickup address", widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Our volunteers will collect the items from here.",
    )
    message = forms.CharField(
        label="Note for volunteers (optional)", required=False, max_length=300,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            list(self.item_fields)
            + ["donor_name", "donor_email", "donor_phone", "city", "pickup_address", "message"]
        )

    def get_quantity(self):
        return self.cleaned_data.get("quantity") or 1

    def get_details(self):
        details = {}
        for name in self.detail_fields:
            value = self.cleaned_data.get(name)
            if value in (None, ""):
                continue
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            details[name] = value
        return details


class FoodDonationForm(BaseItemDonationForm):
    item_fields = ("food_item", "food_type", "quantity", "unit", "expiry_date")
    detail_fields = ("food_item", "food_type", "unit", "expiry_date")
    submit_label = "Schedule food pickup"

    food_item = forms.CharField(label="What food are you donating?", max_length=100)
    food_type = forms.ChoiceField(
        label="Type",
        choices=[
            ("cooked", "Cooked meals"),
            ("packaged", "Packaged food"),
            ("staples", "Grains, pulses & staples"),
            ("produce", "Fruits & vegetables"),
        ],
    )
    quantity = forms.IntegerField(label="Quantity", min_value=1, max_value=5000)
    unit = forms.ChoiceField(
        label="Unit", choices=[("kg", "kg"), ("meals", "meals / plates"), ("packets", "packets")]
    )
    expiry_date = forms.DateField(
        label="Best before / expiry date", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )

    def clean_expiry_date(self):
        expiry = self.cleaned_data.get("expiry_date")
        if expiry and expiry < timezone.localdate():
            raise forms.ValidationError("Expired food cannot be donated.")
        return expiry


class ClothesDonationForm(BaseItemDonationForm):
    item_fields = ("clothing_type", "quantity", "condition", "size_range")
    detail_fields = ("clothing_type", "condition", "size_range")
    submit_label = "Schedule clothes pickup"

    clothing_type = forms.ChoiceField(
        label="Clothing type",
        choices=[
            ("men", "Men's wear"),
            ("women", "Women's wear"),
            ("kids", "Children's wear"),
            ("winter", "Winter wear / blankets"),
            ("mixed", "Mixed"),
        ],
    )
    quantity = forms.IntegerField(label="Number of pieces", min_value=1, max_value=2000)
    condition = forms.ChoiceField(
        label="Condition", choices=[("new", "New with tags"), ("good", "Gently used, clean")]
    )
    size_range = forms.CharField(label="Sizes (optional)", required=False, max_length=60)


class EWasteDonationForm(BaseItemDonationForm):
    item_fields = ("device_type", "brand", "quantity", "working_condition", "data_wiped")
    detail_fields = ("device_type", "brand", "working_condition", "data_wiped")
    submit_label = "Schedule e-waste pickup"

    device_type = forms.ChoiceField(
        label="Device type",
        choices=[
            ("laptop", "Laptop / computer"),
            ("phone", "Mobile phone"),
            ("tablet", "Tablet"),
            ("tv", "TV / monitor"),
            ("accessories", "Chargers, cables, batteries"),
            ("appliance", "Small electronic appliance"),
        ],
    )
    brand = forms.CharField(label="Brand / model (optional)", required=False, max_length=80)
    quantity = forms.IntegerField(label="Number of devices", min_value=1, max_value=500)
    working_condition = forms.ChoiceField(
        label="Condition",
        choices=[("working", "Working"), ("repairable", "Needs minor repair"), ("scrap", "Not working (recycle)")],
    )
    data_wiped = forms.BooleanField(
        label="I have erased personal data from this device", required=False
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("device_type") in {"laptop", "phone", "tablet"} and not cleaned.get("data_wiped"):
            self.add_error("data_wiped", "Please erase your personal data before donating this device.")
        return cleaned


class EducationDonationForm(BaseItemDonationForm):
    item_fields = ("item_type", "quantity", "grade_level", "language")
    detail_fields = ("item_type", "grade_level", "language")
    submit_label = "Schedule education pickup"

    item_type = forms.ChoiceField(
        label="What are you donating?",
        choices=[
            ("textbooks", "Textbooks"),
            ("storybooks", "Story books"),
            ("notebooks", "Notebooks"),
            ("stationery", "Stationery kits"),
            ("bags", "School bags"),
        ],
    )
    quantity = forms.IntegerField(label="Number of items", min_value=1, max_value=5000)
    grade_level = forms.ChoiceField(
        label="Suitable for",
        choices=[
            ("primary", "Primary (Classes 1–5)"),
            ("middle", "Middle (Classes 6–8)"),
            ("secondary", "Secondary (Classes 9–12)"),
            ("college", "College"),
            ("all", "All levels"),
        ],
    )
    language = forms.CharField(label="Language (optional)", required=False, max_length=40)


class BloodDonationForm(BaseItemDonationForm):
    item_fields = ("blood_group", "age", "weight_kg", "last_donated", "available_from", "health_confirmed")
    detail_fields = ("blood_group", "age", "weight_kg", "last_donated", "available_from")
    submit_label = "Register as blood donor"

    blood_group = forms.ChoiceField(
        label="Blood group",
        choices=[(g, g) for g in ("A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-")],
    )
    age = forms.IntegerField(label="Age", min_value=18, max_value=65,
                             error_messages={"min_value": "Blood donors must be at least 18 years old.",
                                             "max_value": "Blood donors must be 65 or younger."})
    weight_kg = forms.IntegerField(label="Weight (kg)", min_value=45,
                                   error_messages={"min_value": "A minimum weight of 45 kg is required to donate."})
    last_donated = forms.DateField(
        label="Last donated on (if ever)", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    available_from = forms.DateField(
        label="Available from", widget=forms.DateInput(attrs={"type": "date"})
    )
    health_confirmed = forms.BooleanField(
        label="I confirm I am in good health and have no active infections or restrictions on donating blood."
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("pickup_address")
        self.fields["message"].label = "Preferred hospital / notes (optional)"

    def clean_last_donated(self):
        last = self.cleaned_data.get("last_donated")
        today = timezone.localdate()
        if last:
            if last > today:
                raise forms.ValidationError("The date cannot be in the future.")
            if today - last < timedelta(days=90):
                raise forms.ValidationError("You need to wait at least 90 days between whole-blood donations.")
        return last

    def clean_available_from(self):
        available = self.cleaned_data["available_from"]
        if available < timezone.localdate():
            raise forms.ValidationError("Choose today or a future date.")
        return available

    def get_quantity(self):
        return 1


class HouseholdDonationForm(BaseItemDonationForm):
    item_fields = ("item_name", "item_group", "quantity", "condition")
    detail_fields = ("item_name", "item_group", "condition")
    submit_label = "Schedule household pickup"

    item_name = forms.CharField(label="Item description", max_length=120)
    item_group = forms.ChoiceField(
        label="Group",
        choices=[
            ("utensils", "Utensils & kitchenware"),
            ("bedding", "Bedding & blankets"),
            ("furniture", "Furniture"),
            ("appliance", "Appliances"),
            ("misc", "Other household items"),
        ],
    )
    quantity = forms.IntegerField(label="Quantity", min_value=1, max_value=1000)
    condition = forms.ChoiceField(
        label="Condition", choices=[("new", "New"), ("good", "Good"), ("fair", "Fair, usable")]
    )


class OtherDonationForm(BaseItemDonationForm):
    item_fields = ("item_description", "quantity")
    detail_fields = ("item_description",)
    submit_label = "Submit donation"

    item_description = forms.CharField(
        label="What would you like to donate?", widget=forms.Textarea(attrs={"rows": 3}), max_length=300
    )
    quantity = forms.IntegerField(label="Quantity", min_value=1, max_value=1000)


ITEM_FORMS = {
    "food": FoodDonationForm,
    "clothes": ClothesDonationForm,
    "e-waste": EWasteDonationForm,
    "education": EducationDonationForm,
    "blood": BloodDonationForm,
    "household-items": HouseholdDonationForm,
    "other": OtherDonationForm,
}
