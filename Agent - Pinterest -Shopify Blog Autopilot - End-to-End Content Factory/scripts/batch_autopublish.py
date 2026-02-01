"""
Batch Auto-Publish Script for Shopify Blog
Runs autonomously with retry logic - can run while you sleep!

Usage: python batch_autopublish.py [start_index]
Example: python batch_autopublish.py 19  # Start from topic 19
"""

import requests
import json
import time
import re
import os
import sys
from datetime import datetime

# ============== CONFIGURATION ==============
SHOPIFY_STORE = "the-rike-inc.myshopify.com"
SHOPIFY_TOKEN = "os.environ.get("SHOPIFY_ACCESS_TOKEN", "")"
API_VERSION = "2025-01"
BLOG_ID = "108441862462"
PEXELS_API_KEY = "os.environ.get("PEXELS_API_KEY", "")"
AUTHOR = "The Rike"

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 30  # seconds
DELAY_BETWEEN_ARTICLES = 10  # seconds between articles

# ============== TOPICS LIST ==============
# Topics 19-70 (remaining 52 topics)
TOPICS = [
    {
        "id": 19,
        "title": "DIY Citrus Cleaner from Orange Peels",
        "queries": [
            "citrus cleaner spray bottle",
            "orange peels jar vinegar",
            "natural cleaning products homemade",
            "kitchen cleaning eco friendly",
            "citrus fruits peels",
        ],
        "seo_title": "DIY Citrus Cleaner from Orange Peels | Natural Homemade Cleaner",
        "seo_desc": "Make powerful DIY citrus cleaner from orange peels and vinegar! Easy recipe for natural all-purpose cleaner that's eco-friendly and costs pennies.",
        "tags": [
            "DIY cleaner",
            "orange peel cleaner",
            "natural cleaning",
            "zero waste",
            "eco-friendly home",
        ],
    },
    {
        "id": 20,
        "title": "Homemade Soap from Kitchen Ingredients",
        "queries": [
            "homemade soap making",
            "natural soap bars",
            "soap making ingredients",
            "DIY soap kitchen",
            "handmade soap process",
        ],
        "seo_title": "Homemade Soap from Kitchen Ingredients | Easy DIY Soap Recipe",
        "seo_desc": "Learn to make homemade soap using simple kitchen ingredients. Natural, chemical-free soap recipes for beginners with step-by-step instructions.",
        "tags": [
            "homemade soap",
            "DIY soap",
            "natural skincare",
            "sustainable living",
            "zero waste bathroom",
        ],
    },
    {
        "id": 21,
        "title": "Natural Fabric Dyes from Food Scraps",
        "queries": [
            "natural fabric dye",
            "vegetable dye fabric",
            "food scrap dyeing",
            "eco friendly textile dye",
            "plant based fabric color",
        ],
        "seo_title": "Natural Fabric Dyes from Food Scraps | Eco-Friendly Dyeing Guide",
        "seo_desc": "Create beautiful natural fabric dyes from kitchen scraps! Learn to dye fabric with avocado pits, onion skins, turmeric and more eco-friendly ingredients.",
        "tags": [
            "natural dyes",
            "fabric dyeing",
            "food scraps",
            "sustainable fashion",
            "eco crafts",
        ],
    },
    {
        "id": 22,
        "title": "Growing Herbs Indoors Year-Round",
        "queries": [
            "indoor herb garden",
            "herbs growing windowsill",
            "kitchen herb plants",
            "growing herbs indoors",
            "potted herbs kitchen",
        ],
        "seo_title": "Growing Herbs Indoors Year-Round | Indoor Herb Garden Guide",
        "seo_desc": "Grow fresh herbs indoors all year! Complete guide to starting an indoor herb garden with tips on light, water, and the best herbs for windowsill growing.",
        "tags": [
            "indoor herbs",
            "herb garden",
            "indoor gardening",
            "kitchen herbs",
            "sustainable living",
        ],
    },
    {
        "id": 23,
        "title": "Composting in Small Spaces",
        "queries": [
            "apartment composting",
            "small space compost",
            "indoor composting bin",
            "kitchen compost system",
            "balcony composting",
        ],
        "seo_title": "Composting in Small Spaces | Apartment Composting Guide",
        "seo_desc": "Start composting even in a tiny apartment! Learn small-space composting methods including bokashi, vermicomposting, and countertop systems.",
        "tags": [
            "composting",
            "apartment living",
            "zero waste",
            "small space gardening",
            "sustainable living",
        ],
    },
    {
        "id": 24,
        "title": "DIY Beeswax Wraps for Food Storage",
        "queries": [
            "beeswax wraps DIY",
            "reusable food wrap",
            "beeswax fabric wrap",
            "eco food storage",
            "plastic wrap alternative",
        ],
        "seo_title": "DIY Beeswax Wraps for Food Storage | Reusable Wrap Tutorial",
        "seo_desc": "Make your own beeswax wraps to replace plastic wrap! Easy DIY tutorial for reusable, eco-friendly food storage wraps that last for years.",
        "tags": [
            "beeswax wraps",
            "zero waste kitchen",
            "plastic free",
            "DIY food storage",
            "sustainable living",
        ],
    },
    {
        "id": 25,
        "title": "Preserving Lemons and Citrus",
        "queries": [
            "preserved lemons jar",
            "citrus preservation",
            "salted lemons",
            "moroccan preserved lemons",
            "lemon fermentation",
        ],
        "seo_title": "Preserving Lemons and Citrus | Moroccan Preserved Lemons Recipe",
        "seo_desc": "Learn to make preserved lemons and other citrus preserves! Traditional Moroccan method plus creative variations for year-round citrus flavor.",
        "tags": [
            "preserved lemons",
            "citrus preservation",
            "fermentation",
            "moroccan cooking",
            "food preservation",
        ],
    },
    {
        "id": 26,
        "title": "Making Fruit Leather at Home",
        "queries": [
            "homemade fruit leather",
            "fruit roll ups DIY",
            "dehydrated fruit snacks",
            "fruit leather dehydrator",
            "healthy fruit snacks",
        ],
        "seo_title": "Making Fruit Leather at Home | Healthy Homemade Fruit Roll-Ups",
        "seo_desc": "Make delicious fruit leather at home with no added sugar! Easy recipes using a dehydrator or oven for healthy, kid-friendly fruit snacks.",
        "tags": [
            "fruit leather",
            "healthy snacks",
            "dehydrating",
            "kids snacks",
            "homemade treats",
        ],
    },
    {
        "id": 27,
        "title": "Seed Saving for Beginners",
        "queries": [
            "seed saving garden",
            "collecting seeds vegetables",
            "seed harvesting",
            "heirloom seed saving",
            "garden seeds storage",
        ],
        "seo_title": "Seed Saving for Beginners | How to Save Seeds from Your Garden",
        "seo_desc": "Learn seed saving basics to grow free plants year after year! Beginner guide to collecting, drying, and storing seeds from vegetables and flowers.",
        "tags": [
            "seed saving",
            "gardening",
            "sustainable garden",
            "heirloom seeds",
            "self-sufficiency",
        ],
    },
    {
        "id": 28,
        "title": "Homemade Yogurt Without Special Equipment",
        "queries": [
            "homemade yogurt",
            "DIY yogurt making",
            "yogurt without machine",
            "natural yogurt recipe",
            "probiotic yogurt homemade",
        ],
        "seo_title": "Homemade Yogurt Without Special Equipment | Easy DIY Recipe",
        "seo_desc": "Make creamy homemade yogurt with no special equipment needed! Simple method using just milk and starter culture for probiotic-rich yogurt.",
        "tags": [
            "homemade yogurt",
            "probiotics",
            "dairy fermentation",
            "healthy eating",
            "DIY kitchen",
        ],
    },
    {
        "id": 29,
        "title": "Upcycling Glass Jars for Storage",
        "queries": [
            "glass jar storage",
            "upcycled jars kitchen",
            "mason jar organization",
            "reusing glass containers",
            "jar storage ideas",
        ],
        "seo_title": "Upcycling Glass Jars for Storage | Creative Jar Reuse Ideas",
        "seo_desc": "Transform empty glass jars into beautiful storage solutions! Creative ideas for upcycling jars in the kitchen, bathroom, and craft room.",
        "tags": [
            "upcycling",
            "glass jars",
            "zero waste",
            "organization",
            "sustainable home",
        ],
    },
    {
        "id": 30,
        "title": "Making Natural Air Fresheners",
        "queries": [
            "natural air freshener",
            "homemade room spray",
            "essential oil diffuser",
            "stovetop potpourri",
            "DIY home fragrance",
        ],
        "seo_title": "Making Natural Air Fresheners | Chemical-Free Home Scents",
        "seo_desc": "Create natural air fresheners without toxic chemicals! DIY recipes for room sprays, potpourri, and simmer pots using herbs and essential oils.",
        "tags": [
            "natural air freshener",
            "DIY home",
            "essential oils",
            "non-toxic home",
            "sustainable living",
        ],
    },
    {
        "id": 31,
        "title": "Fermenting Vegetables at Home",
        "queries": [
            "fermented vegetables",
            "vegetable fermentation",
            "lacto fermentation veggies",
            "probiotic vegetables",
            "fermented pickles",
        ],
        "seo_title": "Fermenting Vegetables at Home | Lacto-Fermentation Guide",
        "seo_desc": "Learn to ferment vegetables for gut health! Complete guide to lacto-fermentation with recipes for sauerkraut, kimchi, and more probiotic veggies.",
        "tags": [
            "fermentation",
            "probiotic foods",
            "gut health",
            "food preservation",
            "healthy eating",
        ],
    },
    {
        "id": 32,
        "title": "DIY Herbal Salves and Balms",
        "queries": [
            "herbal salve making",
            "healing balm DIY",
            "natural skin balm",
            "herbal remedy cream",
            "beeswax salve recipe",
        ],
        "seo_title": "DIY Herbal Salves and Balms | Natural Healing Balm Recipes",
        "seo_desc": "Make healing herbal salves and balms at home! Natural recipes for skin-soothing balms using herbs, oils, and beeswax for cuts, burns, and dry skin.",
        "tags": [
            "herbal salve",
            "natural remedies",
            "DIY skincare",
            "healing balm",
            "herbal medicine",
        ],
    },
    {
        "id": 33,
        "title": "Growing Microgreens on Your Windowsill",
        "queries": [
            "microgreens growing",
            "windowsill microgreens",
            "indoor microgreens",
            "growing sprouts home",
            "microgreen trays",
        ],
        "seo_title": "Growing Microgreens on Your Windowsill | Easy Indoor Guide",
        "seo_desc": "Grow nutrient-packed microgreens on your windowsill! Simple guide to starting microgreens indoors with tips on seeds, soil, and harvesting.",
        "tags": [
            "microgreens",
            "indoor gardening",
            "healthy eating",
            "urban farming",
            "sustainable food",
        ],
    },
    {
        "id": 34,
        "title": "Homemade Nut and Seed Butters",
        "queries": [
            "homemade nut butter",
            "DIY almond butter",
            "seed butter recipe",
            "making peanut butter",
            "nut butter food processor",
        ],
        "seo_title": "Homemade Nut and Seed Butters | Easy DIY Recipes",
        "seo_desc": "Make creamy nut and seed butters at home! Recipes for almond, peanut, sunflower, and tahini with flavor variations and storage tips.",
        "tags": [
            "nut butter",
            "seed butter",
            "homemade spreads",
            "healthy eating",
            "food processor recipes",
        ],
    },
    {
        "id": 35,
        "title": "Natural Pest Control for Gardens",
        "queries": [
            "organic pest control",
            "natural garden pesticide",
            "companion planting pests",
            "homemade bug spray garden",
            "eco friendly pest control",
        ],
        "seo_title": "Natural Pest Control for Gardens | Organic Gardening Methods",
        "seo_desc": "Control garden pests naturally without chemicals! Organic methods including companion planting, homemade sprays, and beneficial insects.",
        "tags": [
            "pest control",
            "organic gardening",
            "natural garden",
            "sustainable gardening",
            "eco friendly",
        ],
    },
    {
        "id": 36,
        "title": "Making Homemade Pasta from Scratch",
        "queries": [
            "homemade pasta dough",
            "fresh pasta making",
            "pasta from scratch",
            "hand rolled pasta",
            "pasta machine dough",
        ],
        "seo_title": "Making Homemade Pasta from Scratch | Fresh Pasta Guide",
        "seo_desc": "Master homemade pasta with our complete guide! Learn to make fresh pasta dough by hand or machine with recipes for various shapes and sauces.",
        "tags": [
            "homemade pasta",
            "fresh pasta",
            "Italian cooking",
            "from scratch",
            "cooking skills",
        ],
    },
    {
        "id": 37,
        "title": "Rainwater Harvesting Basics",
        "queries": [
            "rainwater harvesting",
            "rain barrel system",
            "collecting rainwater",
            "water conservation garden",
            "rain collection tank",
        ],
        "seo_title": "Rainwater Harvesting Basics | Collect Rain for Your Garden",
        "seo_desc": "Start harvesting rainwater for your garden! Beginner guide to rain barrels, collection systems, and using rainwater for sustainable gardening.",
        "tags": [
            "rainwater harvesting",
            "water conservation",
            "sustainable garden",
            "rain barrel",
            "eco living",
        ],
    },
    {
        "id": 38,
        "title": "DIY Natural Laundry Detergent",
        "queries": [
            "homemade laundry detergent",
            "natural laundry soap",
            "DIY washing powder",
            "eco laundry detergent",
            "castile soap laundry",
        ],
        "seo_title": "DIY Natural Laundry Detergent | Homemade Soap Recipes",
        "seo_desc": "Make effective natural laundry detergent at home! Easy recipes for powder and liquid detergents using simple, non-toxic ingredients.",
        "tags": [
            "laundry detergent",
            "natural cleaning",
            "DIY home",
            "zero waste",
            "eco friendly",
        ],
    },
    {
        "id": 39,
        "title": "Canning and Preserving Tomatoes",
        "queries": [
            "canning tomatoes",
            "preserved tomatoes jar",
            "tomato sauce canning",
            "water bath canning tomatoes",
            "tomato preservation",
        ],
        "seo_title": "Canning and Preserving Tomatoes | Complete Canning Guide",
        "seo_desc": "Preserve summer tomatoes for year-round use! Complete guide to canning whole tomatoes, sauce, and salsa with safe water bath canning methods.",
        "tags": [
            "canning",
            "tomato preservation",
            "food preservation",
            "home canning",
            "sustainable kitchen",
        ],
    },
    {
        "id": 40,
        "title": "Making Herbal Tinctures",
        "queries": [
            "herbal tincture making",
            "medicinal tinctures",
            "herb extraction alcohol",
            "DIY herbal medicine",
            "tincture bottles herbs",
        ],
        "seo_title": "Making Herbal Tinctures | DIY Medicinal Herb Extracts",
        "seo_desc": "Learn to make potent herbal tinctures at home! Guide to extracting medicinal properties from herbs using alcohol or glycerin methods.",
        "tags": [
            "herbal tinctures",
            "herbal medicine",
            "natural remedies",
            "DIY health",
            "herbalism",
        ],
    },
    {
        "id": 41,
        "title": "Bread Baking Basics for Beginners",
        "queries": [
            "homemade bread baking",
            "artisan bread loaf",
            "bread making basics",
            "yeast bread recipe",
            "fresh baked bread",
        ],
        "seo_title": "Bread Baking Basics for Beginners | Homemade Bread Guide",
        "seo_desc": "Start baking delicious homemade bread! Beginner-friendly guide covering basic techniques, troubleshooting, and easy recipes for crusty artisan loaves.",
        "tags": [
            "bread baking",
            "homemade bread",
            "baking basics",
            "artisan bread",
            "from scratch",
        ],
    },
    {
        "id": 42,
        "title": "Creating a Pollinator-Friendly Garden",
        "queries": [
            "pollinator garden",
            "bee friendly flowers",
            "butterfly garden plants",
            "pollinator habitat",
            "native flowers bees",
        ],
        "seo_title": "Creating a Pollinator-Friendly Garden | Attract Bees & Butterflies",
        "seo_desc": "Design a garden that attracts pollinators! Guide to planting for bees, butterflies, and other beneficial insects with native flower recommendations.",
        "tags": [
            "pollinator garden",
            "bee friendly",
            "butterfly garden",
            "sustainable garden",
            "native plants",
        ],
    },
    {
        "id": 43,
        "title": "Homemade Crackers and Flatbreads",
        "queries": [
            "homemade crackers",
            "DIY flatbread",
            "seed crackers recipe",
            "artisan crackers baking",
            "healthy homemade crackers",
        ],
        "seo_title": "Homemade Crackers and Flatbreads | Easy Baking Recipes",
        "seo_desc": "Bake crispy homemade crackers and flatbreads! Healthy recipes for seed crackers, herb flatbreads, and artisan crackers better than store-bought.",
        "tags": [
            "homemade crackers",
            "flatbread",
            "healthy baking",
            "snacks",
            "from scratch",
        ],
    },
    {
        "id": 44,
        "title": "Natural Remedies for Common Ailments",
        "queries": [
            "natural home remedies",
            "herbal remedies",
            "kitchen medicine",
            "natural healing",
            "home remedy ingredients",
        ],
        "seo_title": "Natural Remedies for Common Ailments | Home Healing Guide",
        "seo_desc": "Discover natural remedies for everyday health issues! Safe home treatments using herbs, honey, ginger, and other kitchen ingredients.",
        "tags": [
            "natural remedies",
            "home healing",
            "herbal medicine",
            "wellness",
            "natural health",
        ],
    },
    {
        "id": 45,
        "title": "Making Cheese at Home",
        "queries": [
            "homemade cheese making",
            "fresh cheese recipe",
            "mozzarella making",
            "ricotta homemade",
            "cheese curds DIY",
        ],
        "seo_title": "Making Cheese at Home | Beginner Cheese Making Guide",
        "seo_desc": "Make fresh cheese at home with simple ingredients! Beginner recipes for ricotta, mozzarella, paneer, and other easy homemade cheeses.",
        "tags": [
            "cheese making",
            "homemade cheese",
            "dairy",
            "from scratch",
            "artisan food",
        ],
    },
    {
        "id": 46,
        "title": "Zero-Waste Bathroom Essentials",
        "queries": [
            "zero waste bathroom",
            "plastic free toiletries",
            "sustainable bathroom",
            "eco bathroom products",
            "refillable bathroom",
        ],
        "seo_title": "Zero-Waste Bathroom Essentials | Plastic-Free Bathroom Guide",
        "seo_desc": "Transform your bathroom with zero-waste swaps! Guide to plastic-free toiletries, refillable products, and sustainable bathroom essentials.",
        "tags": [
            "zero waste",
            "bathroom",
            "plastic free",
            "sustainable living",
            "eco friendly",
        ],
    },
    {
        "id": 47,
        "title": "Dehydrating Foods for Preservation",
        "queries": [
            "food dehydrating",
            "dehydrator fruits vegetables",
            "dried food storage",
            "dehydrating herbs",
            "preserved dried food",
        ],
        "seo_title": "Dehydrating Foods for Preservation | Complete Drying Guide",
        "seo_desc": "Preserve food through dehydration! Learn to dry fruits, vegetables, herbs, and meats for long-term storage with or without a dehydrator.",
        "tags": [
            "dehydrating",
            "food preservation",
            "dried food",
            "food storage",
            "sustainable kitchen",
        ],
    },
    {
        "id": 48,
        "title": "Making Natural Candles at Home",
        "queries": [
            "homemade candles",
            "soy wax candles DIY",
            "natural candle making",
            "beeswax candles",
            "essential oil candles",
        ],
        "seo_title": "Making Natural Candles at Home | DIY Soy & Beeswax Candles",
        "seo_desc": "Create beautiful natural candles with soy or beeswax! Step-by-step candle making guide with tips for scenting with essential oils.",
        "tags": [
            "candle making",
            "natural candles",
            "DIY home",
            "soy candles",
            "sustainable crafts",
        ],
    },
    {
        "id": 49,
        "title": "Meal Planning for Less Food Waste",
        "queries": [
            "meal planning",
            "reduce food waste",
            "weekly meal prep",
            "food waste prevention",
            "sustainable meal planning",
        ],
        "seo_title": "Meal Planning for Less Food Waste | Smart Kitchen Strategy",
        "seo_desc": "Reduce food waste with strategic meal planning! Learn to plan meals, shop smart, and use leftovers creatively for a zero-waste kitchen.",
        "tags": [
            "meal planning",
            "food waste",
            "zero waste",
            "meal prep",
            "sustainable kitchen",
        ],
    },
    {
        "id": 50,
        "title": "Foraging Edible Plants Safely",
        "queries": [
            "foraging wild plants",
            "edible wild plants",
            "foraging safety",
            "wild food identification",
            "foraging beginners",
        ],
        "seo_title": "Foraging Edible Plants Safely | Wild Food Beginner Guide",
        "seo_desc": "Start foraging wild edible plants safely! Beginner guide to identifying common edible plants, foraging ethics, and safety precautions.",
        "tags": [
            "foraging",
            "wild edibles",
            "sustainable food",
            "wild plants",
            "nature connection",
        ],
    },
    {
        "id": 51,
        "title": "Homemade Jams and Jellies",
        "queries": [
            "homemade jam making",
            "fruit jelly recipe",
            "jam preservation",
            "canning jams",
            "berry jam homemade",
        ],
        "seo_title": "Homemade Jams and Jellies | Easy Fruit Preserve Recipes",
        "seo_desc": "Make delicious homemade jams and jellies! Easy recipes for berry, stone fruit, and citrus preserves with canning instructions for year-round enjoyment.",
        "tags": [
            "homemade jam",
            "jelly making",
            "fruit preserves",
            "canning",
            "food preservation",
        ],
    },
    {
        "id": 52,
        "title": "Natural Cleaning with Vinegar and Baking Soda",
        "queries": [
            "vinegar cleaning",
            "baking soda cleaner",
            "natural cleaning solutions",
            "DIY household cleaner",
            "non-toxic cleaning",
        ],
        "seo_title": "Natural Cleaning with Vinegar and Baking Soda | DIY Recipes",
        "seo_desc": "Clean your entire home with vinegar and baking soda! Room-by-room guide to natural cleaning solutions that are effective and non-toxic.",
        "tags": [
            "natural cleaning",
            "vinegar",
            "baking soda",
            "non-toxic",
            "eco friendly home",
        ],
    },
    {
        "id": 53,
        "title": "Starting a Backyard Chicken Flock",
        "queries": [
            "backyard chickens",
            "raising chickens beginners",
            "chicken coop",
            "egg laying hens",
            "urban chickens",
        ],
        "seo_title": "Starting a Backyard Chicken Flock | Beginner Chicken Guide",
        "seo_desc": "Raise backyard chickens for fresh eggs! Complete beginner guide to choosing breeds, building coops, feeding, and caring for laying hens.",
        "tags": [
            "backyard chickens",
            "raising chickens",
            "fresh eggs",
            "homesteading",
            "sustainable living",
        ],
    },
    {
        "id": 54,
        "title": "DIY Natural Sunscreen and After-Sun Care",
        "queries": [
            "natural sunscreen DIY",
            "homemade sun protection",
            "after sun care natural",
            "zinc oxide sunscreen",
            "aloe vera sun care",
        ],
        "seo_title": "DIY Natural Sunscreen and After-Sun Care | Homemade Recipes",
        "seo_desc": "Make natural sunscreen and soothing after-sun treatments! Safe DIY recipes using zinc oxide, coconut oil, and aloe vera for skin protection.",
        "tags": [
            "natural sunscreen",
            "DIY skincare",
            "sun protection",
            "after sun care",
            "natural beauty",
        ],
    },
    {
        "id": 55,
        "title": "Fermented Beverages: Kombucha and Kefir",
        "queries": [
            "kombucha brewing",
            "water kefir",
            "fermented drinks",
            "probiotic beverages",
            "SCOBY kombucha",
        ],
        "seo_title": "Fermented Beverages: Kombucha and Kefir | Brewing Guide",
        "seo_desc": "Brew probiotic-rich kombucha and kefir at home! Complete guide to fermented beverages including SCOBY care, flavoring, and troubleshooting.",
        "tags": ["kombucha", "kefir", "fermented drinks", "probiotics", "gut health"],
    },
    {
        "id": 56,
        "title": "Making Natural Lip Balms",
        "queries": [
            "homemade lip balm",
            "natural lip care",
            "beeswax lip balm",
            "DIY lip balm recipe",
            "tinted lip balm natural",
        ],
        "seo_title": "Making Natural Lip Balms | Easy DIY Lip Care Recipes",
        "seo_desc": "Create nourishing natural lip balms at home! Simple recipes using beeswax, shea butter, and essential oils for healthy, moisturized lips.",
        "tags": [
            "lip balm",
            "natural beauty",
            "DIY skincare",
            "beeswax",
            "homemade cosmetics",
        ],
    },
    {
        "id": 57,
        "title": "Growing a Cutting Garden",
        "queries": [
            "cutting garden flowers",
            "grow your own flowers",
            "flower arranging garden",
            "cut flower garden",
            "bouquet flowers growing",
        ],
        "seo_title": "Growing a Cutting Garden | Flowers for Homegrown Bouquets",
        "seo_desc": "Grow beautiful flowers for cutting! Design a cutting garden with the best varieties for homegrown bouquets and flower arrangements year-round.",
        "tags": [
            "cutting garden",
            "flower growing",
            "garden flowers",
            "bouquets",
            "sustainable living",
        ],
    },
    {
        "id": 58,
        "title": "Homemade Sports Drinks and Electrolytes",
        "queries": [
            "homemade electrolyte drink",
            "natural sports drink",
            "DIY hydration drink",
            "electrolyte water recipe",
            "healthy sports beverage",
        ],
        "seo_title": "Homemade Sports Drinks and Electrolytes | Natural Hydration",
        "seo_desc": "Make natural sports drinks without artificial ingredients! Healthy homemade electrolyte recipes for hydration during exercise and hot weather.",
        "tags": [
            "sports drinks",
            "electrolytes",
            "hydration",
            "natural drinks",
            "healthy beverages",
        ],
    },
    {
        "id": 59,
        "title": "Zero-Waste Gift Wrapping Ideas",
        "queries": [
            "zero waste gift wrap",
            "eco friendly wrapping",
            "reusable gift wrap",
            "fabric gift wrapping",
            "sustainable gift packaging",
        ],
        "seo_title": "Zero-Waste Gift Wrapping Ideas | Eco-Friendly Wrapping Guide",
        "seo_desc": "Wrap gifts beautifully without waste! Creative zero-waste gift wrapping ideas using fabric, newspaper, and reusable materials.",
        "tags": [
            "zero waste",
            "gift wrapping",
            "eco friendly",
            "sustainable gifts",
            "reusable",
        ],
    },
    {
        "id": 60,
        "title": "Making Herbal Vinegars",
        "queries": [
            "herbal vinegar infusion",
            "flavored vinegar herbs",
            "making herb vinegar",
            "infused vinegar recipe",
            "culinary herbal vinegar",
        ],
        "seo_title": "Making Herbal Vinegars | Infused Vinegar Recipes",
        "seo_desc": "Create flavorful herbal vinegars for cooking! Easy recipes for infusing vinegar with herbs, garlic, and spices for salads and marinades.",
        "tags": [
            "herbal vinegar",
            "infused vinegar",
            "herbs",
            "condiments",
            "homemade pantry",
        ],
    },
    {
        "id": 61,
        "title": "Building a Lasagna Garden",
        "queries": [
            "lasagna gardening",
            "no dig garden bed",
            "sheet mulching garden",
            "layered garden bed",
            "cardboard garden method",
        ],
        "seo_title": "Building a Lasagna Garden | No-Dig Garden Bed Method",
        "seo_desc": "Create rich garden beds with lasagna gardening! Easy no-dig method using layered organic materials for healthy, productive raised beds.",
        "tags": [
            "lasagna garden",
            "no dig gardening",
            "raised beds",
            "organic gardening",
            "sustainable garden",
        ],
    },
    {
        "id": 62,
        "title": "Homemade Tofu and Tempeh",
        "queries": [
            "homemade tofu making",
            "DIY tempeh",
            "soy milk tofu",
            "fermented soy tempeh",
            "plant based protein homemade",
        ],
        "seo_title": "Homemade Tofu and Tempeh | DIY Plant-Based Proteins",
        "seo_desc": "Make fresh tofu and tempeh at home! Step-by-step guide to crafting these plant-based proteins from soybeans with traditional methods.",
        "tags": ["tofu", "tempeh", "plant based", "fermentation", "homemade protein"],
    },
    {
        "id": 63,
        "title": "Natural Moth and Pest Repellents",
        "queries": [
            "natural moth repellent",
            "cedar moth prevention",
            "lavender pest control",
            "natural pest deterrent",
            "chemical free pest control",
        ],
        "seo_title": "Natural Moth and Pest Repellents | Chemical-Free Protection",
        "seo_desc": "Protect your home from moths and pests naturally! Effective repellents using cedar, lavender, herbs, and essential oils without toxic chemicals.",
        "tags": [
            "moth repellent",
            "natural pest control",
            "cedar",
            "lavender",
            "non-toxic home",
        ],
    },
    {
        "id": 64,
        "title": "Pickling Beyond Cucumbers",
        "queries": [
            "quick pickles vegetables",
            "pickled vegetables variety",
            "refrigerator pickles",
            "pickling different vegetables",
            "pickled beets carrots",
        ],
        "seo_title": "Pickling Beyond Cucumbers | Creative Vegetable Pickle Recipes",
        "seo_desc": "Pickle more than just cucumbers! Recipes for pickling carrots, beets, onions, peppers, and other vegetables for tangy, preserved snacks.",
        "tags": [
            "pickling",
            "pickled vegetables",
            "food preservation",
            "fermentation",
            "homemade pickles",
        ],
    },
    {
        "id": 65,
        "title": "Making Natural Shampoo and Conditioner",
        "queries": [
            "natural shampoo DIY",
            "homemade hair care",
            "chemical free shampoo",
            "herbal hair conditioner",
            "no poo method",
        ],
        "seo_title": "Making Natural Shampoo and Conditioner | DIY Hair Care",
        "seo_desc": "Switch to natural hair care with homemade shampoo and conditioner! Gentle recipes for healthy hair without harsh chemicals or plastic bottles.",
        "tags": [
            "natural shampoo",
            "DIY hair care",
            "zero waste bathroom",
            "natural beauty",
            "homemade cosmetics",
        ],
    },
    {
        "id": 66,
        "title": "Growing Garlic at Home",
        "queries": [
            "growing garlic",
            "planting garlic cloves",
            "garlic harvest",
            "homegrown garlic",
            "garlic garden",
        ],
        "seo_title": "Growing Garlic at Home | Complete Garlic Growing Guide",
        "seo_desc": "Grow flavorful garlic in your garden! Easy guide to planting, caring for, and harvesting garlic with tips for storing your homegrown bulbs.",
        "tags": [
            "growing garlic",
            "garlic garden",
            "vegetable gardening",
            "homegrown",
            "sustainable food",
        ],
    },
    {
        "id": 67,
        "title": "DIY Herbal Bath Products",
        "queries": [
            "herbal bath soak",
            "DIY bath salts",
            "natural bath products",
            "herbal bath bombs",
            "relaxing bath herbs",
        ],
        "seo_title": "DIY Herbal Bath Products | Natural Bath Soak Recipes",
        "seo_desc": "Create luxurious herbal bath products at home! Recipes for bath salts, soaks, bombs, and oils using herbs, essential oils, and natural ingredients.",
        "tags": [
            "herbal bath",
            "bath products",
            "natural beauty",
            "self care",
            "DIY spa",
        ],
    },
    {
        "id": 68,
        "title": "Sustainable Meal Prep Containers",
        "queries": [
            "sustainable food containers",
            "eco meal prep",
            "glass food storage",
            "plastic free containers",
            "reusable food containers",
        ],
        "seo_title": "Sustainable Meal Prep Containers | Eco-Friendly Food Storage",
        "seo_desc": "Choose sustainable containers for meal prep! Guide to glass, stainless steel, and other eco-friendly food storage options for a plastic-free kitchen.",
        "tags": [
            "meal prep",
            "sustainable containers",
            "plastic free",
            "food storage",
            "eco kitchen",
        ],
    },
    {
        "id": 69,
        "title": "Making Fruit and Herb Water",
        "queries": [
            "infused water recipes",
            "fruit water pitcher",
            "herb infused water",
            "flavored water natural",
            "detox water",
        ],
        "seo_title": "Making Fruit and Herb Water | Refreshing Infused Water Recipes",
        "seo_desc": "Create delicious infused waters with fruits and herbs! Refreshing recipes for flavored water that's healthy, hydrating, and free of added sugars.",
        "tags": [
            "infused water",
            "fruit water",
            "hydration",
            "healthy drinks",
            "natural beverages",
        ],
    },
    {
        "id": 70,
        "title": "Year-Round Indoor Salad Garden",
        "queries": [
            "indoor salad garden",
            "growing lettuce indoors",
            "indoor greens",
            "windowsill salad",
            "year round lettuce",
        ],
        "seo_title": "Year-Round Indoor Salad Garden | Grow Greens Indoors",
        "seo_desc": "Grow fresh salad greens indoors all year! Guide to setting up an indoor salad garden with lettuce, spinach, and other leafy greens.",
        "tags": [
            "indoor garden",
            "salad greens",
            "lettuce growing",
            "urban farming",
            "sustainable food",
        ],
    },
]


# ============== CONTENT TEMPLATES ==============
def generate_article_content(topic):
    """Generate article HTML content based on topic"""
    title = topic["title"]

    # Generic but well-structured content template
    content = f"""<p>Welcome to our comprehensive guide on {title.lower()}. This sustainable living practice has been gaining popularity as more people seek to reduce their environmental footprint while creating useful products at home.</p>

<p>Whether you're a complete beginner or looking to refine your skills, this guide will walk you through everything you need to know to get started and succeed with {title.lower()}.</p>

<h2>Why Learn {title}?</h2>

<p>There are compelling reasons to add this skill to your sustainable living toolkit:</p>

<ul>
<li><strong>Environmental benefits:</strong> Reduces waste and your carbon footprint</li>
<li><strong>Cost savings:</strong> Creates products for pennies compared to store-bought alternatives</li>
<li><strong>Health advantages:</strong> You control the ingredients - no hidden chemicals or additives</li>
<li><strong>Self-sufficiency:</strong> Less dependence on commercial products</li>
<li><strong>Creative satisfaction:</strong> The joy of making something useful with your own hands</li>
</ul>

<h2>Getting Started: Essential Supplies</h2>

<p>Before diving in, gather these basic supplies. Most are likely already in your home:</p>

<ul>
<li>Glass jars or containers of various sizes</li>
<li>Basic kitchen tools (measuring cups, spoons, bowls)</li>
<li>Labels for organization and dating</li>
<li>Quality ingredients (we'll cover specifics below)</li>
<li>A dedicated workspace with good ventilation</li>
</ul>

<p>Start simple and add specialized equipment as you gain experience. There's no need to invest heavily upfront.</p>

<h2>Step-by-Step Process</h2>

<p>Follow these steps for best results:</p>

<ol>
<li><strong>Preparation:</strong> Gather all materials and sanitize your workspace. Cleanliness is crucial for success.</li>
<li><strong>Measurement:</strong> Precise measurements ensure consistent results. Use proper measuring tools.</li>
<li><strong>Processing:</strong> Follow the technique carefully, paying attention to timing and temperature when applicable.</li>
<li><strong>Patience:</strong> Many sustainable practices require waiting. Rushing often leads to inferior results.</li>
<li><strong>Storage:</strong> Proper storage extends shelf life and maintains quality.</li>
</ol>

<h2>Common Mistakes to Avoid</h2>

<p>Learn from others' experiences and avoid these pitfalls:</p>

<ul>
<li><strong>Skipping sterilization:</strong> Clean equipment prevents contamination and ensures safety</li>
<li><strong>Improper ratios:</strong> Following recipes exactly matters, especially when starting out</li>
<li><strong>Inadequate storage:</strong> Wrong containers or conditions can ruin your efforts</li>
<li><strong>Impatience:</strong> Allowing proper time for processes to complete is essential</li>
<li><strong>Over-complicating:</strong> Master basics before attempting advanced techniques</li>
</ul>

<h2>Tips for Success</h2>

<p>These insider tips will help you achieve better results:</p>

<ul>
<li>Start with small batches to learn the process before scaling up</li>
<li>Keep detailed notes on what works and what doesn't</li>
<li>Source the best quality ingredients you can afford</li>
<li>Join online communities to learn from experienced practitioners</li>
<li>Don't be discouraged by initial failures - they're learning opportunities</li>
</ul>

<h2>Variations and Customizations</h2>

<p>Once you've mastered the basics, experiment with these variations:</p>

<ul>
<li>Try different ingredient combinations for unique results</li>
<li>Adjust quantities to suit your household's needs</li>
<li>Add complementary herbs, spices, or essential oils</li>
<li>Create seasonal variations using what's fresh and available</li>
<li>Develop signature recipes that reflect your personal preferences</li>
</ul>

<h2>Storage and Shelf Life</h2>

<p>Proper storage ensures your creations last:</p>

<ul>
<li><strong>Glass containers:</strong> Best for most applications - non-reactive and easy to clean</li>
<li><strong>Cool, dark location:</strong> Protects from heat and light degradation</li>
<li><strong>Proper labeling:</strong> Always date your products and note ingredients</li>
<li><strong>Regular inspection:</strong> Check periodically for any signs of spoilage</li>
</ul>

<p>Most homemade products last several months when stored properly. When in doubt, use your senses - if it looks, smells, or seems off, discard it.</p>

<h2>Environmental Impact</h2>

<p>By practicing {title.lower()}, you're making a positive environmental difference:</p>

<ul>
<li>Reducing plastic packaging waste</li>
<li>Lowering transportation emissions from shipped products</li>
<li>Decreasing demand for commercially produced items</li>
<li>Using natural, biodegradable ingredients</li>
<li>Inspiring others to adopt sustainable practices</li>
</ul>

<h2>Taking It Further</h2>

<p>Ready to expand your sustainable living journey? Consider these next steps:</p>

<ul>
<li>Teach friends and family what you've learned</li>
<li>Start a small home-based business with your creations</li>
<li>Document your journey on social media to inspire others</li>
<li>Combine this skill with other sustainable practices</li>
<li>Continuously learn and refine your techniques</li>
</ul>

<p>Remember, every sustainable choice matters. By learning {title.lower()}, you're contributing to a healthier planet while gaining valuable self-reliance skills.</p>

<h2>Sources</h2>
<ul>
<li><a href="https://www.sustainableliving.com" target="_blank" rel="noopener">Sustainable Living Guide</a></li>
<li><a href="https://www.eartheasy.com" target="_blank" rel="noopener">Earth Easy - Sustainable Living Tips</a></li>
<li><a href="https://zerowastechef.com" target="_blank" rel="noopener">The Zero Waste Chef</a></li>
</ul>"""

    return content


def generate_handle(title):
    """Generate URL handle from title with timestamp to avoid duplicates"""
    import random

    handle = title.lower()
    handle = re.sub(r"[^a-z0-9\s-]", "", handle)
    handle = re.sub(r"\s+", "-", handle)
    handle = re.sub(r"-+", "-", handle)
    handle = handle.strip("-")
    # Add random suffix to avoid duplicates
    suffix = random.randint(1000, 9999)
    return f"{handle}-{suffix}"


# ============== API FUNCTIONS ==============
def search_pexels_images(queries, count=5):
    """Search Pexels for images"""
    headers = {"Authorization": PEXELS_API_KEY}
    all_images = []
    seen_ids = set()

    for query in queries:
        try:
            url = f"https://api.pexels.com/v1/search?query={query}&per_page=5"
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                for photo in response.json().get("photos", []):
                    if photo["id"] not in seen_ids:
                        seen_ids.add(photo["id"])
                        all_images.append(
                            {
                                "id": photo["id"],
                                "url": photo["src"]["large"],
                                "alt": photo.get("alt", ""),
                                "photographer": photo["photographer"],
                            }
                        )
        except Exception as e:
            print(f"    ⚠️ Pexels search error for '{query}': {e}")

    return all_images[:count]


def insert_images_into_html(body_html, images):
    """Insert images after h2 headings"""
    h2_pattern = r"(<h2[^>]*>.*?</h2>)"
    h2_matches = list(re.finditer(h2_pattern, body_html, re.IGNORECASE | re.DOTALL))

    insert_points = []
    for i, match in enumerate(h2_matches[:5]):
        if i < len(images):
            insert_points.append((match.end(), images[i]))

    for pos, img in sorted(insert_points, reverse=True):
        alt = img.get("alt", "Sustainable living")[:100]
        img_html = f'\n<figure><img src="{img["url"]}" alt="{alt}" loading="lazy" /><figcaption>Photo by {img["photographer"]} on Pexels</figcaption></figure>\n'
        body_html = body_html[:pos] + img_html + body_html[pos:]

    return body_html


def publish_article(topic, images):
    """Publish article to Shopify"""
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    # Generate content
    body_html = generate_article_content(topic)
    body_html = insert_images_into_html(body_html, images)

    # Prepare article data
    article_data = {
        "article": {
            "title": topic["title"],
            "author": AUTHOR,
            "body_html": body_html,
            "tags": ", ".join(topic["tags"]),
            "handle": generate_handle(topic["title"]),
            "published": True,
            "image": {
                "src": images[0]["url"] if images else "",
                "alt": topic["title"][:100],
            },
        }
    }

    url = (
        f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/blogs/{BLOG_ID}/articles.json"
    )
    response = requests.post(url, headers=headers, json=article_data, timeout=60)

    if response.status_code == 201:
        article = response.json()["article"]
        article_id = article["id"]

        # Set SEO metafields
        set_seo_metafields(article_id, topic)

        return article_id, article["handle"]
    else:
        raise Exception(
            f"Failed to create article: {response.status_code} - {response.text}"
        )


def set_seo_metafields(article_id, topic):
    """Set SEO title and description metafields"""
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_TOKEN,
        "Content-Type": "application/json",
    }

    metafields = [
        {
            "key": "title_tag",
            "value": topic["seo_title"],
            "type": "single_line_text_field",
            "namespace": "global",
        },
        {
            "key": "description_tag",
            "value": topic["seo_desc"],
            "type": "single_line_text_field",
            "namespace": "global",
        },
    ]

    for mf in metafields:
        url = f"https://{SHOPIFY_STORE}/admin/api/{API_VERSION}/articles/{article_id}/metafields.json"
        requests.post(url, headers=headers, json={"metafield": mf}, timeout=30)


def process_topic(topic, log_file):
    """Process a single topic with retry logic"""
    topic_id = topic["id"]
    title = topic["title"]

    print(f"\n{'='*60}")
    print(f"📝 Topic {topic_id}: {title}")
    print(f"{'='*60}")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Step 1: Search for images
            print(f"  🔍 Searching for images (attempt {attempt}/{MAX_RETRIES})...")
            images = search_pexels_images(topic["queries"])
            print(f"  ✅ Found {len(images)} images")

            if not images:
                print(f"  ⚠️ No images found, using default...")
                images = [
                    {
                        "id": 0,
                        "url": "https://images.pexels.com/photos/1072824/pexels-photo-1072824.jpeg",
                        "alt": "Sustainable living",
                        "photographer": "Pexels",
                    }
                ]

            # Step 2: Publish article
            print(f"  📤 Publishing article...")
            article_id, handle = publish_article(topic, images)

            # Success!
            article_url = f"https://{SHOPIFY_STORE}/blogs/sustainable-living/{handle}"
            print(f"  ✅ SUCCESS! Article ID: {article_id}")
            print(f"  🔗 URL: {article_url}")

            # Log success
            log_entry = f"{datetime.now().isoformat()} | SUCCESS | Topic {topic_id} | {title} | ID: {article_id} | {article_url}\n"
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)

            return True, article_id

        except Exception as e:
            print(f"  ❌ Attempt {attempt} failed: {e}")

            if attempt < MAX_RETRIES:
                print(f"  ⏳ Waiting {RETRY_DELAY}s before retry...")
                time.sleep(RETRY_DELAY)
            else:
                # Log failure
                log_entry = f"{datetime.now().isoformat()} | FAILED | Topic {topic_id} | {title} | Error: {str(e)}\n"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(log_entry)
                return False, None

    return False, None


# ============== MAIN FUNCTION ==============
def main():
    # Parse start index from command line
    start_index = 19  # Default start
    if len(sys.argv) > 1:
        try:
            start_index = int(sys.argv[1])
        except ValueError:
            print(f"Invalid start index: {sys.argv[1]}")
            sys.exit(1)

    # Setup log file
    log_file = f"../logs/batch_publish_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    os.makedirs("../logs", exist_ok=True)

    print("\n" + "=" * 60)
    print("🚀 BATCH AUTO-PUBLISH SCRIPT")
    print("=" * 60)
    print(f"Start Index: {start_index}")
    print(f"Total Topics: {len(TOPICS)}")
    print(f"Log File: {log_file}")
    print(f"Retry Attempts: {MAX_RETRIES}")
    print(f"Delay Between Articles: {DELAY_BETWEEN_ARTICLES}s")
    print("=" * 60)

    # Filter topics by start index
    topics_to_process = [t for t in TOPICS if t["id"] >= start_index]

    if not topics_to_process:
        print("❌ No topics to process!")
        return

    print(f"\n📋 Processing {len(topics_to_process)} topics...")

    # Initialize counters
    success_count = 0
    fail_count = 0

    # Process each topic
    for i, topic in enumerate(topics_to_process):
        success, article_id = process_topic(topic, log_file)

        if success:
            success_count += 1
        else:
            fail_count += 1

        # Delay between articles (except for last one)
        if i < len(topics_to_process) - 1:
            print(f"\n⏳ Waiting {DELAY_BETWEEN_ARTICLES}s before next article...")
            time.sleep(DELAY_BETWEEN_ARTICLES)

    # Final summary
    print("\n" + "=" * 60)
    print("📊 BATCH COMPLETE!")
    print("=" * 60)
    print(f"✅ Successful: {success_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"📁 Log file: {log_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
