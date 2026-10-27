"""Static definitions for donation categories."""

DEFAULT_CATEGORIES = [
    {
        "name": "E-Waste",
        "slug": "e-waste",
        "icon": "bi-cpu",
        "gradient": "grad-indigo",
        "order": 1,
        "description": "Give old laptops, phones and gadgets a second life or a safe, certified recycling.",
    },
    {
        "name": "Food",
        "slug": "food",
        "icon": "bi-basket2",
        "gradient": "grad-orange",
        "order": 2,
        "description": "Share surplus meals, grains and packaged food with community kitchens.",
    },
    {
        "name": "Clothes",
        "slug": "clothes",
        "icon": "bi-handbag",
        "gradient": "grad-rose",
        "order": 3,
        "description": "Donate clean, wearable clothing for children, families and winter relief drives.",
    },
    {
        "name": "Money",
        "slug": "money",
        "icon": "bi-currency-rupee",
        "gradient": "grad-emerald",
        "order": 4,
        "description": "Contribute to the Karisma General Fund (demo payment flow, no real money).",
    },
    {
        "name": "Education",
        "slug": "education",
        "icon": "bi-book",
        "gradient": "grad-sky",
        "order": 5,
        "description": "Books, stationery and learning kits for students who need them most.",
    },
    {
        "name": "Blood",
        "slug": "blood",
        "icon": "bi-droplet-half",
        "gradient": "grad-crimson",
        "order": 6,
        "description": "Register as a blood donor and help hospitals reach you in emergencies.",
    },
    {
        "name": "Household Items",
        "slug": "household-items",
        "icon": "bi-house-gear",
        "gradient": "grad-amber",
        "order": 7,
        "description": "Utensils, bedding, furniture and appliances for families rebuilding their homes.",
    },
    {
        "name": "Other",
        "slug": "other",
        "icon": "bi-gift",
        "gradient": "grad-violet",
        "order": 8,
        "description": "Something else that could help? Tell us what you would like to give.",
    },
]

MONEY_SLUG = "money"
MIN_DONATION = 10
MAX_DONATION = 1000000
