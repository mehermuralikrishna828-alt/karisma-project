"""Populate Karisma with realistic demo data.

Usage:
    python manage.py seed_demo_data            # skip if data already seeded
    python manage.py seed_demo_data --reset    # wipe previously seeded data and re-create
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import Notification
from accounts.utils import notify
from crowdfunding.models import Campaign, CampaignUpdate, SavedCampaign
from crowdfunding.services import check_deadline_notifications, notify_campaign_update
from donations.models import Donation, DonationCategory, DonationDrive
from donations.services import (
    DonationError,
    ensure_default_categories,
    record_item_donation,
    record_money_donation,
)
from philanthropy.models import PhilanthropyCause

User = get_user_model()
PASSWORD = "Karisma@123"

USERS = [
    # username, first, last, city, state
    ("demo", "Aarav", "Kapoor", "New Delhi", "Delhi"),
    ("priya.raman", "Priya", "Raman", "Chennai", "Tamil Nadu"),
    ("arjun.mehta", "Arjun", "Mehta", "Mumbai", "Maharashtra"),
    ("kavya.nair", "Kavya", "Nair", "Kochi", "Kerala"),
    ("rohan.deshmukh", "Rohan", "Deshmukh", "Pune", "Maharashtra"),
    ("ananya.iyer", "Ananya", "Iyer", "Bengaluru", "Karnataka"),
    ("faizan.shaikh", "Mohammed", "Faizan", "Hyderabad", "Telangana"),
    ("sneha.patil", "Sneha", "Patil", "Nashik", "Maharashtra"),
    ("vikram.singh", "Vikram", "Singh", "Jaipur", "Rajasthan"),
    ("lakshmi.narayanan", "Lakshmi", "Narayanan", "Madurai", "Tamil Nadu"),
    ("deepak.kumar", "Deepak", "Kumar", "Guwahati", "Assam"),
    ("meera.joshi", "Meera", "Joshi", "Ahmedabad", "Gujarat"),
    ("harpreet.kaur", "Harpreet", "Kaur", "Ludhiana", "Punjab"),
]

CAMPAIGNS = [
    {
        "creator": "priya.raman", "title": "Heart Surgery for Baby Aadhya", "category": "medical",
        "short": "Six-month-old Aadhya needs an urgent open-heart surgery at a Chennai hospital.",
        "location": "Chennai, Tamil Nadu", "beneficiary": "Baby Aadhya, daughter of an autorickshaw driver",
        "target": 650000, "days": 24, "age": 18, "ratio": 0.68, "verified": True, "featured": True,
        "description": (
            "Aadhya was born with a congenital heart defect (Tetralogy of Fallot). Doctors at the Institute of Child Health "
            "have advised surgery within the next two months before her condition worsens.\n\n"
            "Her father, Murugan, drives an autorickshaw and earns about ₹600 on a good day. The family has already spent "
            "their savings on tests and medication. The estimate for surgery, ICU care and follow-up is ₹6,50,000.\n\n"
            "Every rupee raised is paid directly to the hospital against the final invoice. Any unused amount will be "
            "donated to another child's cardiac fund."
        ),
        "impact": "₹10,000 covers one day of paediatric ICU care. ₹50,000 pays for the heart-lung machine and anaesthesia.",
        "updates": [("Pre-surgery tests completed", "All pre-operative tests were completed this week and the surgery date is tentatively set. Thank you to every supporter so far.")],
    },
    {
        "creator": "kavya.nair", "title": "Rebuild Our Village School in Wayanad", "category": "education",
        "short": "A landslide damaged the only school in Pulpally. Help 180 children return to a safe classroom.",
        "location": "Wayanad, Kerala", "beneficiary": "180 students of Government LP School, Pulpally",
        "target": 1200000, "days": 41, "age": 30, "ratio": 0.54, "verified": True, "featured": True,
        "description": (
            "Heavy monsoon rains caused a landslide that damaged three classrooms and the library of Government LP School, "
            "Pulpally. For two months, 180 children have studied in a community hall with no benches and no boards.\n\n"
            "We are a group of former students and teachers raising ₹12,00,000 to rebuild classrooms with reinforced "
            "retaining walls, set up a small library and buy furniture and learning kits.\n\n"
            "The reconstruction is supervised by the Panchayat engineer and a monthly progress report is shared here."
        ),
        "impact": "₹2,500 buys a bench-desk set for two students. ₹15,000 equips a classroom with boards and lighting.",
        "updates": [
            ("Foundation work begins", "The retaining wall design was approved by the Panchayat engineer. Work begins on Monday."),
            ("Library shelves donated", "A local carpenters' association has offered to build the library shelves free of cost."),
        ],
    },
    {
        "creator": "vikram.singh", "title": "Clean Water Borewell for Three Barmer Villages", "category": "community",
        "short": "Families walk 5 km for drinking water. A deep borewell and storage tank will change that.",
        "location": "Barmer, Rajasthan", "beneficiary": "About 420 residents of Dhani Kheta, Sawau and Lunu",
        "target": 450000, "days": 33, "age": 22, "ratio": 0.77, "verified": True, "featured": False,
        "description": (
            "In the dhanis around Barmer, women and children walk up to five kilometres every day to fetch water that is "
            "often brackish. Summer temperatures make the journey dangerous.\n\n"
            "Our village committee has surveyed a site and received hydrogeologist approval for a 600-ft borewell with a "
            "solar pump, a 10,000-litre storage tank and three community taps.\n\n"
            "The committee will maintain the system and collect a small monthly fee for repairs."
        ),
        "impact": "₹1,100 provides drinking water to one person for five years.",
        "updates": [("Hydrogeology survey cleared", "The survey confirmed a good water table at 580 ft. Drilling is scheduled for next month.")],
    },
    {
        "creator": "deepak.kumar", "title": "Flood Relief Kits for 300 Assam Families", "category": "disaster",
        "short": "Dhemaji has been flooded again. Dry rations, tarpaulins and medicines are needed now.",
        "location": "Dhemaji, Assam", "beneficiary": "300 flood-affected families in Dhemaji district",
        "target": 800000, "days": 12, "age": 9, "ratio": 0.46, "verified": True, "featured": True,
        "description": (
            "The Brahmaputra and its tributaries have breached embankments again, leaving hundreds of families stranded "
            "on raised highways and relief camps.\n\n"
            "Our volunteer group has partnered with local NGOs to assemble relief kits containing 15 kg of dry rations, a "
            "tarpaulin, water purification tablets, a first-aid pack and hygiene supplies.\n\n"
            "Each kit costs ₹2,650. Distribution is photographed and shared in campaign updates."
        ),
        "impact": "One relief kit (₹2,650) sustains a family of five for two weeks.",
        "updates": [("First 80 kits delivered", "Boats carried the first 80 kits to Jonai today. Volunteers are packing the next batch.")],
    },
    {
        "creator": "rohan.deshmukh", "title": "Shelter & Surgery Fund for Pune's Street Dogs", "category": "animal",
        "short": "Help us build a recovery shelter and fund sterilisation and surgery for injured street dogs.",
        "location": "Pune, Maharashtra", "beneficiary": "Around 120 injured and abandoned street dogs",
        "target": 250000, "days": 3, "age": 40, "ratio": 0.83, "verified": False, "featured": False,
        "description": (
            "Every week our small team of volunteers rescues dogs hit by vehicles or abandoned after injury. We currently "
            "treat them in rented space that is far too small.\n\n"
            "This campaign will fund a 20-kennel recovery shelter, an operating table, medicines and sterilisation "
            "drives in four wards of Pune.\n\n"
            "We are registered with the Animal Welfare Board and publish monthly expense reports."
        ),
        "impact": "₹3,500 funds one sterilisation. ₹12,000 covers fracture surgery for one dog.",
        "updates": [("Only 3 days left!", "We're ₹42,000 short of the target. Even a small contribution will help finish the shelter roof.")],
    },
    {
        "creator": "lakshmi.narayanan", "title": "Sewing Machines for 40 Women in Madurai", "category": "women",
        "short": "Give 40 women from low-income homes the tools to start tailoring businesses.",
        "location": "Madurai, Tamil Nadu", "beneficiary": "40 women from self-help groups",
        "target": 320000, "days": 52, "age": 14, "ratio": 0.31, "verified": True, "featured": False,
        "description": (
            "Our self-help group has trained 40 women in tailoring through a three-month certified course. Most cannot "
            "afford a machine of their own, so they cannot start earning.\n\n"
            "We are raising ₹3,20,000 to buy 40 semi-automatic sewing machines, fabric starter kits and a month of "
            "market-linkage support.\n\n"
            "A graduate earns between ₹7,000 and ₹12,000 per month, enough to keep her children in school."
        ),
        "impact": "₹8,000 gives one woman a sewing machine and starter kit - and a livelihood.",
        "updates": [],
    },
    {
        "creator": "ananya.iyer", "title": "Mangrove Restoration in the Sundarbans", "category": "environment",
        "short": "Plant 25,000 mangroves to protect coastal villages from cyclones and rising tides.",
        "location": "South 24 Parganas, West Bengal", "beneficiary": "Coastal communities of Gosaba block",
        "target": 900000, "days": 75, "age": 26, "ratio": 0.38, "verified": True, "featured": True,
        "description": (
            "Mangroves are the Sundarbans' first line of defence against cyclones. Erosion and salinity have destroyed "
            "large stretches of the green belt around Gosaba.\n\n"
            "Working with local fishing families and a forest-department-approved nursery, we will plant and maintain "
            "25,000 saplings over three monsoons and train villagers as paid mangrove guardians.\n\n"
            "Survival rates are tracked by GPS tagging and shared on this page every quarter."
        ),
        "impact": "₹36 plants and protects one mangrove sapling for a year.",
        "updates": [("Nursery beds ready", "12,000 saplings are already growing in the nursery and will be planted when the tide allows.")],
    },
    {
        "creator": "faizan.shaikh", "title": "Kidney Transplant Support for Ramesh Naidu", "category": "medical",
        "short": "A 34-year-old father of two needs a kidney transplant. A donor from the family is ready.",
        "location": "Hyderabad, Telangana", "beneficiary": "Ramesh Naidu, a schoolteacher",
        "target": 1500000, "days": 60, "age": 6, "ratio": 0.12, "verified": False, "featured": False,
        "description": (
            "Ramesh has been on dialysis three times a week for 14 months. His wife is a matched donor and doctors at a "
            "Hyderabad transplant centre have confirmed that surgery is possible.\n\n"
            "The total cost of surgery, medicines and post-operative care is ₹15,00,000. Insurance covers only a small "
            "part of the cost.\n\n"
            "Medical records and the hospital estimate are available to verify on request."
        ),
        "impact": "₹5,000 pays for one week of post-transplant immunosuppressants.",
        "updates": [],
    },
    {
        "creator": "meera.joshi", "title": "Community Library on Wheels, Ahmedabad", "category": "education",
        "short": "A converted bus carrying 6,000 books will bring reading to slum neighbourhoods.",
        "location": "Ahmedabad, Gujarat", "beneficiary": "Children in 12 informal settlements",
        "target": 180000, "days": 9, "age": 55, "ratio": 1.0, "verified": True, "featured": False,
        "description": (
            "Many children in Ahmedabad's informal settlements have never owned a book. Our mobile library visits a new "
            "neighbourhood each day with story hours and homework help.\n\n"
            "Funds were raised to retrofit a donated bus with shelves, solar lighting and a reading corner."
        ),
        "impact": "₹300 buys three picture books for a child.",
        "updates": [("Fully funded!", "Thank you! The bus is at the workshop and will be on the road in three weeks.")],
    },
    {
        "creator": "lakshmi.narayanan", "title": "Musical Instruments for Rural Carnatic Students", "category": "arts",
        "short": "Veenas, violins and mridangams for talented children in Tirunelveli's government schools.",
        "location": "Tirunelveli, Tamil Nadu", "beneficiary": "60 children from government schools",
        "target": 200000, "days": 38, "age": 11, "ratio": 0.22, "verified": False, "featured": False,
        "description": (
            "Our weekend music school teaches Carnatic music free of cost to children from rural government schools. "
            "Students share just six instruments between sixty of them.\n\n"
            "We are raising ₹2,00,000 for twelve student-grade instruments and tuning accessories so every child can "
            "practise at home."
        ),
        "impact": "₹15,000 provides one student-grade violin or mridangam.",
        "updates": [],
    },
]

CAUSES = [
    {
        "title": "Clean Water for Every Village", "category": "water", "target": 5000000, "ratio": 0.42, "featured": True,
        "description": "We install community water purification systems, borewells and rain-water harvesting units in water-scarce districts of Rajasthan, Maharashtra and Odisha.",
        "beneficiary": "Rural families who currently depend on distant or unsafe water sources.",
        "stats": [("12,500", "people with safe drinking water"), ("84", "villages served"), ("6", "districts covered")],
        "note": "₹1,100 provides safe water to one person for five years.",
    },
    {
        "title": "One Crore Trees for India", "category": "trees", "target": 3000000, "ratio": 0.57, "featured": True,
        "description": "Native saplings planted and nurtured with local communities, from urban forests in Bengaluru to mangrove belts in the Sundarbans.",
        "beneficiary": "Communities that depend on forests, and cities that need cleaner air.",
        "stats": [("1,86,000", "saplings planted"), ("78%", "survival rate"), ("140", "villagers employed")],
        "note": "₹50 plants and protects one native sapling for a year.",
    },
    {
        "title": "Every Child Learns", "category": "education", "target": 4000000, "ratio": 0.33, "featured": True,
        "description": "Scholarships, bridge schools and digital learning labs for children from migrant, rural and low-income families.",
        "beneficiary": "First-generation learners aged 6 to 16.",
        "stats": [("3,200", "children supported"), ("45", "learning centres"), ("91%", "school retention")],
        "note": "₹6,000 sponsors a child's school year including books and uniform.",
    },
    {
        "title": "Zero Hunger Kitchens", "category": "hunger", "target": 2500000, "ratio": 0.61, "featured": False,
        "description": "Community kitchens serving nutritious cooked meals to daily-wage workers, elderly people living alone and children in shelters.",
        "beneficiary": "People without reliable access to a nutritious daily meal.",
        "stats": [("2,40,000", "meals served"), ("18", "kitchens running"), ("900", "meals every day")],
        "note": "₹40 serves one hot, nutritious meal.",
    },
    {
        "title": "Homes for the Homeless", "category": "housing", "target": 6000000, "ratio": 0.19, "featured": False,
        "description": "Affordable, flood-resistant homes and night shelters for families displaced by disasters or living on the streets.",
        "beneficiary": "Homeless families and disaster-affected households.",
        "stats": [("112", "homes built"), ("560", "people housed"), ("9", "night shelters")],
        "note": "₹25,000 provides a bed in a night shelter for a year.",
    },
    {
        "title": "Climate Action Now", "category": "climate", "target": 3500000, "ratio": 0.28, "featured": False,
        "description": "Solar lamps, clean cookstoves and climate-resilient farming training for communities most exposed to extreme weather.",
        "beneficiary": "Smallholder farmers and fisher families in climate-vulnerable regions.",
        "stats": [("8,900", "solar lamps distributed"), ("1,350", "farmers trained"), ("620 t", "CO₂ avoided yearly")],
        "note": "₹800 gives a family a solar lamp and clean cookstove.",
    },
    {
        "title": "Paws & Hearts Animal Care", "category": "animals", "target": 1500000, "ratio": 0.64, "featured": False,
        "description": "Rescue, vaccination, sterilisation and adoption support for street animals, plus rural livestock health camps.",
        "beneficiary": "Street dogs, cats and working animals across 14 cities.",
        "stats": [("7,400", "animals vaccinated"), ("2,100", "sterilisations"), ("860", "adoptions")],
        "note": "₹500 vaccinates five street dogs against rabies.",
    },
    {
        "title": "Health Without Hurdles", "category": "health", "target": 4500000, "ratio": 0.47, "featured": False,
        "description": "Free health camps, mobile clinics and subsidised surgeries for families who cannot afford quality healthcare.",
        "beneficiary": "Low-income families in remote districts.",
        "stats": [("21,000", "patients treated"), ("96", "health camps"), ("1,150", "surgeries funded")],
        "note": "₹1,500 funds a complete health check-up camp for 20 people.",
    },
]

DRIVES = [
    ("clothes", "Winter Warmth Drive 2026", "Collect blankets, sweaters and jackets for families sleeping outdoors this winter.", "Delhi NCR collection points", "Karisma Volunteers Delhi", 40, "pieces", 1500, 932),
    ("food", "Rice & Dal Ration Kits", "Dry rations for 500 families in Chennai's flood-prone neighbourhoods.", "Chennai - Velachery & Tondiarpet", "Anbu Food Bank", 25, "kg", 3000, 1840),
    ("e-waste", "E-Waste Recycling Week", "Bring old phones, laptops and chargers for certified recycling and refurbishment.", "Bengaluru - Indiranagar & HSR", "GreenLoop Recyclers", 14, "devices", 400, 187),
    ("education", "Books for Bridge Schools", "Story books and textbooks for evening bridge schools run in Mumbai's slums.", "Mumbai - Dharavi & Govandi", "Pratham Volunteers", 32, "books", 2500, 1210),
    ("blood", "Blood Donation Camp", "Register for the quarterly camp held with a leading government hospital's blood bank.", "Hyderabad - Gandhi Hospital", "Telangana Blood Donors Forum", 18, "donors", 250, 96),
    ("household-items", "Flood Recovery Home Essentials", "Utensils, bedding and stoves for families returning to damaged homes.", "Guwahati & Dhemaji", "Assam Relief Volunteers", 21, "sets", 600, 244),
]

AMOUNTS = [250, 500, 500, 1000, 1000, 1500, 2000, 2500, 5000, 5000, 10000, 21000]
MESSAGES = [
    "Wishing the family strength and good health.",
    "Every little bit counts - happy to help!",
    "Proud to support such a good cause.",
    "Praying for a speedy recovery.",
    "From all of us at the Iyer household.",
    "Keep up the amazing work.",
    "",
    "",
    "",
]


class Command(BaseCommand):
    help = "Seed the database with realistic demo users, campaigns, causes and donations."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete previously seeded data first.")

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()
        elif User.objects.filter(username="demo").exists():
            self.stdout.write(self.style.WARNING("Demo data already present. Use --reset to rebuild it."))
            return

        rng = random.Random(2026)
        now = timezone.now()
        today = timezone.localdate()

        ensure_default_categories()
        users = self._create_users()
        campaigns = self._create_campaigns(users, rng, now, today)
        causes = self._create_causes(users, rng, now)
        self._create_drives(today)
        self._create_item_donations(users, rng, now)
        self._create_demo_history(users, campaigns, causes, now)
        self._create_updates_and_saves(users, campaigns, causes, rng)
        check_deadline_notifications()
        self._create_extra_notifications(users)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} users, {len(campaigns)} campaigns, {len(causes)} causes, "
            f"{Donation.objects.count()} donations."
        ))
        self.stdout.write(f"Log in with username 'demo' and password '{PASSWORD}' (all demo users share it).")

    # ------------------------------------------------------------------
    def _reset(self):
        Donation.objects.all().delete()
        Campaign.objects.all().delete()
        PhilanthropyCause.objects.all().delete()
        DonationDrive.objects.all().delete()
        User.objects.filter(username__in=[u[0] for u in USERS]).delete()
        self.stdout.write("Previous demo data removed.")

    def _create_users(self):
        users = {}
        for username, first, last, city, state in USERS:
            user = User.objects.create_user(
                username=username,
                email=f"{username.replace('.', '')}@example.in",
                password=PASSWORD,
                first_name=first,
                last_name=last,
            )
            profile = user.profile
            profile.city, profile.state = city, state
            digit_rng = random.Random(username)
            profile.phone = "9" + "".join(str(digit_rng.randint(0, 9)) for _ in range(9))
            profile.bio = f"Believer in small acts of kindness. Based in {city}."
            profile.save()
            users[username] = user
        return users

    def _create_campaigns(self, users, rng, now, today):
        created = []
        donor_pool = list(users.values())
        for spec in CAMPAIGNS:
            campaign = Campaign.objects.create(
                creator=users[spec["creator"]],
                title=spec["title"],
                short_description=spec["short"],
                description=spec["description"],
                impact_info=spec["impact"],
                beneficiary=spec["beneficiary"],
                location=spec["location"],
                category=spec["category"],
                target_amount=Decimal(spec["target"]),
                deadline=today + timedelta(days=spec["days"]),
                is_verified=spec["verified"],
                is_featured=spec["featured"],
            )
            Campaign.objects.filter(pk=campaign.pk).update(created_at=now - timedelta(days=spec["age"]))
            campaign.refresh_from_db()
            self._fund_campaign(campaign, spec["ratio"], donor_pool, rng, now, spec["age"])
            campaign.refresh_from_db()
            created.append(campaign)
            notify(
                campaign.creator, Notification.Kind.CAMPAIGN, "Your campaign is live",
                f"“{campaign.title}” is now open for support.", campaign.get_absolute_url(),
            )
        return created

    def _fund_campaign(self, campaign, ratio, donors, rng, now, age_days):
        goal = campaign.target_amount * Decimal(str(ratio))
        guard = 0
        while campaign.amount_raised < goal and guard < 600:
            guard += 1
            donor = rng.choice(donors)
            if donor.pk == campaign.creator_id:
                continue
            amount = Decimal(rng.choice(AMOUNTS))
            if campaign.target_amount >= 800000 and rng.random() < 0.3:
                amount *= 2
            when = now - timedelta(days=rng.randint(0, max(age_days, 1)), hours=rng.randint(0, 20))
            try:
                record_money_donation(
                    user=donor, amount=amount,
                    donor_name=donor.get_full_name(), donor_email=donor.email,
                    message=rng.choice(MESSAGES), is_anonymous=rng.random() < 0.12,
                    campaign=campaign, payment_method=rng.choice(["upi", "card", "netbanking"]),
                    created_at=when,
                )
            except DonationError:
                break
            campaign.refresh_from_db()

    def _create_causes(self, users, rng, now):
        created, donors = [], list(users.values())
        for spec in CAUSES:
            cause = PhilanthropyCause.objects.create(
                title=spec["title"], category=spec["category"], description=spec["description"],
                beneficiary_info=spec["beneficiary"], target_amount=Decimal(spec["target"]),
                impact_stats=[{"value": v, "label": l} for v, l in spec["stats"]],
                impact_note=spec["note"], is_featured=spec["featured"],
            )
            goal = cause.target_amount * Decimal(str(spec["ratio"]))
            guard = 0
            while cause.amount_raised < goal and guard < 400:
                guard += 1
                donor = rng.choice(donors)
                amount = Decimal(rng.choice(AMOUNTS)) * rng.choice([1, 1, 2, 5])
                when = now - timedelta(days=rng.randint(0, 150), hours=rng.randint(0, 20))
                record_money_donation(
                    user=donor, amount=amount, donor_name=donor.get_full_name(),
                    donor_email=donor.email, message=rng.choice(MESSAGES),
                    is_anonymous=rng.random() < 0.1, cause=cause, created_at=when,
                    payment_method=rng.choice(["upi", "card", "netbanking"]),
                )
                cause.refresh_from_db()
            created.append(cause)
        return created

    def _create_drives(self, today):
        for slug, title, desc, location, organizer, days, unit, goal, collected in DRIVES:
            DonationDrive.objects.create(
                category=DonationCategory.objects.get(slug=slug), title=title, description=desc,
                location=location, organizer=organizer, start_date=today - timedelta(days=20),
                end_date=today + timedelta(days=days), unit=unit, goal_quantity=goal,
                collected_quantity=collected,
            )

    def _create_item_donations(self, users, rng, now):
        samples = [
            ("food", {"food_item": "Rice and toor dal", "food_type": "staples", "unit": "kg"}, (10, 50)),
            ("clothes", {"clothing_type": "winter", "condition": "good"}, (8, 40)),
            ("e-waste", {"device_type": "laptop", "working_condition": "repairable", "data_wiped": True}, (1, 4)),
            ("education", {"item_type": "textbooks", "grade_level": "middle"}, (15, 80)),
            ("blood", {"blood_group": "O+", "age": 29, "weight_kg": 68}, (1, 1)),
            ("household-items", {"item_name": "Steel utensil set", "item_group": "utensils", "condition": "good"}, (2, 12)),
            ("other", {"item_description": "Sports equipment for a school"}, (3, 10)),
        ]
        people = [u for u in users.values() if u.username != "demo"]
        for _ in range(26):
            slug, details, (low, high) = rng.choice(samples)
            user = rng.choice(people)
            category = DonationCategory.objects.get(slug=slug)
            drive = DonationDrive.objects.filter(category=category).first()
            record_item_donation(
                user=user, category=category, donor_name=user.get_full_name(),
                donor_email=user.email, donor_phone=user.profile.phone, city=user.profile.city,
                address="" if slug == "blood" else f"Flat {rng.randint(1, 40)}, Gandhi Nagar, {user.profile.city}",
                quantity=rng.randint(low, high), details=dict(details), drive=drive,
                created_at=now - timedelta(days=rng.randint(0, 120)),
                status=rng.choice([Donation.Status.COMPLETED, Donation.Status.COMPLETED, Donation.Status.PENDING]),
            )

    def _create_demo_history(self, users, campaigns, causes, now):
        """Give the 'demo' account a rich history so the dashboard charts look good."""
        demo = users["demo"]
        by_title = {c.title: c for c in campaigns}
        cause_by_cat = {c.category: c for c in causes}
        timeline = [
            (150, "campaign", "Rebuild Our Village School in Wayanad", 2500),
            (128, "cause", "water", 1100),
            (101, "campaign", "Heart Surgery for Baby Aadhya", 5000),
            (86, "general", None, 500),
            (74, "cause", "trees", 1000),
            (59, "campaign", "Clean Water Borewell for Three Barmer Villages", 2000),
            (47, "cause", "education", 3000),
            (33, "campaign", "Mangrove Restoration in the Sundarbans", 1500),
            (21, "cause", "hunger", 800),
            (12, "campaign", "Flood Relief Kits for 300 Assam Families", 5000),
            (4, "cause", "health", 1500),
        ]
        for days_ago, kind, ref, amount in timeline:
            record_money_donation(
                user=demo, amount=amount, donor_name=demo.get_full_name(), donor_email=demo.email,
                campaign=by_title.get(ref) if kind == "campaign" else None,
                cause=cause_by_cat.get(ref) if kind == "cause" else None,
                created_at=now - timedelta(days=days_ago), message="Happy to help!",
            )
        item_rows = [
            ("clothes", 95, 12, {"clothing_type": "winter", "condition": "good"}),
            ("food", 52, 20, {"food_item": "Packaged biscuits and rice", "food_type": "packaged", "unit": "kg"}),
            ("education", 28, 30, {"item_type": "storybooks", "grade_level": "primary"}),
            ("blood", 9, 1, {"blood_group": "B+", "age": 31, "weight_kg": 72}),
        ]
        for slug, days_ago, qty, details in item_rows:
            category = DonationCategory.objects.get(slug=slug)
            record_item_donation(
                user=demo, category=category, donor_name=demo.get_full_name(), donor_email=demo.email,
                donor_phone=demo.profile.phone, city="New Delhi",
                address="" if slug == "blood" else "B-12, Lajpat Nagar, New Delhi",
                quantity=qty, details=details, drive=DonationDrive.objects.filter(category=category).first(),
                created_at=now - timedelta(days=days_ago), status=Donation.Status.COMPLETED,
            )
        # A campaign created by the demo user
        campaign = Campaign.objects.create(
            creator=demo, title="Books and Benches for Anganwadi Centres in Gurugram",
            short_description="Furniture and picture books for 6 anganwadi centres serving 150 toddlers.",
            description=(
                "Anganwadi centres in the outskirts of Gurugram serve free meals and early learning to young "
                "children, but most lack seating, mats and books.\n\nWe are raising funds for child-sized benches, "
                "reading mats and 400 picture books so toddlers can learn in comfort."
            ),
            impact_info="₹1,200 equips a toddler's corner with a bench, mat and five books.",
            beneficiary="150 children in 6 anganwadi centres", location="Gurugram, Haryana",
            category="education", target_amount=Decimal("120000"),
            deadline=timezone.localdate() + timedelta(days=45), is_verified=True,
        )
        Campaign.objects.filter(pk=campaign.pk).update(created_at=now - timedelta(days=8))
        campaign.refresh_from_db()
        for username, amount in [("priya.raman", 2500), ("arjun.mehta", 1000), ("meera.joshi", 5000),
                                 ("harpreet.kaur", 1500), ("ananya.iyer", 3000)]:
            donor = users[username]
            record_money_donation(
                user=donor, amount=amount, donor_name=donor.get_full_name(), donor_email=donor.email,
                campaign=campaign, created_at=now - timedelta(days=random.Random(username).randint(0, 7)),
            )

    def _create_updates_and_saves(self, users, campaigns, causes, rng):
        spec_by_title = {s["title"]: s for s in CAMPAIGNS}
        for campaign in campaigns:
            spec = spec_by_title.get(campaign.title)
            if not spec:
                continue
            for title, body in spec["updates"]:
                update = CampaignUpdate.objects.create(campaign=campaign, title=title, body=body)
                CampaignUpdate.objects.filter(pk=update.pk).update(
                    created_at=timezone.now() - timedelta(days=rng.randint(0, 6))
                )
        # Saved campaigns and followed causes
        demo = users["demo"]
        for title in ("Heart Surgery for Baby Aadhya", "Sewing Machines for 40 Women in Madurai",
                      "Musical Instruments for Rural Carnatic Students"):
            SavedCampaign.objects.get_or_create(user=demo, campaign=next(c for c in campaigns if c.title == title))
        for cause in causes[:3]:
            cause.followers.add(demo)
        everyone = list(users.values())
        for campaign in campaigns:
            for user in rng.sample(everyone, k=rng.randint(1, 4)):
                if user.pk != campaign.creator_id:
                    SavedCampaign.objects.get_or_create(user=user, campaign=campaign)
        for cause in causes:
            for user in rng.sample(everyone, k=rng.randint(1, 5)):
                cause.followers.add(user)
        # Fire "campaign update" notifications now that savers exist
        for update in CampaignUpdate.objects.select_related("campaign").all():
            notify_campaign_update(update)

    def _create_extra_notifications(self, users):
        demo = users["demo"]
        notify(demo, Notification.Kind.SYSTEM, "Welcome to Karisma!",
               "Explore campaigns, donate items or support a cause. Payments on Karisma are simulated.", "/crowdfunding/")
        notify(demo, Notification.Kind.SAVED, "Saved campaign is gaining momentum",
               "“Heart Surgery for Baby Aadhya” has crossed 60% of its goal.", "/crowdfunding/")
