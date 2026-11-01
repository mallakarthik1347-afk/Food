import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'site.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def safe_add_column(cursor, table, column_def):
    col_name = column_def.split()[0]
    cursor.execute(f"PRAGMA table_info({table})")
    cols = [row[1] for row in cursor.fetchall()]
    if col_name not in cols:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")
        print(f"Added column {col_name} to {table}")

def migrate_and_seed():
    print("Starting database migration and seeding...")
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Safe ALTER TABLE on existing tables
    safe_add_column(cursor, "user", "is_owner BOOLEAN DEFAULT 0")
    safe_add_column(cursor, "menu_item", "image_url VARCHAR(500) DEFAULT ''")
    safe_add_column(cursor, "menu_item", "is_veg BOOLEAN DEFAULT 1")
    safe_add_column(cursor, "menu_item", "is_spicy BOOLEAN DEFAULT 0")
    safe_add_column(cursor, "menu_item", "rating FLOAT DEFAULT 4.5")
    safe_add_column(cursor, "menu_item", "restaurant_id INTEGER DEFAULT NULL")

    safe_add_column(cursor, '"order"', "restaurant_id INTEGER DEFAULT NULL")
    safe_add_column(cursor, '"order"', "delivery_address VARCHAR(500) DEFAULT 'Road No 36, Jubilee Hills, Hyderabad'")
    safe_add_column(cursor, '"order"', "phone VARCHAR(20) DEFAULT '+91 98765 43210'")

    safe_add_column(cursor, "order_item", "price_at_order FLOAT DEFAULT NULL")
    safe_add_column(cursor, "message", "date_sent DATETIME DEFAULT CURRENT_TIMESTAMP")

    # 2. Create tables if not present
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        address VARCHAR(500),
        phone VARCHAR(20),
        image_url VARCHAR(500) DEFAULT '',
        latitude FLOAT,
        longitude FLOAT,
        rating FLOAT DEFAULT 4.5,
        total_reviews INTEGER DEFAULT 0,
        is_veg BOOLEAN DEFAULT 0,
        cuisine_type VARCHAR(200) DEFAULT 'Multi-Cuisine',
        opening_hours VARCHAR(100) DEFAULT '9:00 AM - 11:00 PM',
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS restaurant_review (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        restaurant_id INTEGER NOT NULL,
        order_id INTEGER NOT NULL UNIQUE,
        rating FLOAT NOT NULL,
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user (id),
        FOREIGN KEY (restaurant_id) REFERENCES restaurant (id),
        FOREIGN KEY (order_id) REFERENCES "order" (id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_status_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        status VARCHAR(50) NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        note VARCHAR(200) DEFAULT '',
        FOREIGN KEY (order_id) REFERENCES "order" (id)
    )
    """)

    # 2b. Seed Users if fewer than 6 exist
    cursor.execute("SELECT COUNT(*) FROM user")
    user_count = cursor.fetchone()[0]

    # Pre-generated bcrypt hash for 'Password123'
    default_pw_hash = '$2b$12$cv/Qeq/Hr.H.FMkRBVHHYOKlChD033YlaqkukDMhATG7kNJSlJBvq'

    sample_users = [
        (1, 'Admin', 'Foodmato', 'foodmato@gmail.com', default_pw_hash, 1),
        (2, 'Hemanth', 'Varma', 'hemanthvarma@gmail.com', default_pw_hash, 0),
        (3, 'Priya', 'Sharma', 'priya.sharma@example.com', default_pw_hash, 0),
        (4, 'Rahul', 'Verma', 'rahul.verma@example.com', default_pw_hash, 0),
        (5, 'Ananya', 'Deshmukh', 'ananya.deshmukh@example.com', default_pw_hash, 0),
        (6, 'Karthik', 'Malla', 'karthik.malla@example.com', default_pw_hash, 0)
    ]

    for uid, fn, ln, em, pw, is_own in sample_users:
        cursor.execute("SELECT id FROM user WHERE id = ?", (uid,))
        if cursor.fetchone():
            cursor.execute("UPDATE user SET is_owner = ?, password = ? WHERE id = ?", (is_own, pw, uid))
        else:
            cursor.execute("""
            INSERT INTO user (id, first_name, last_name, email, password, is_owner, image_file)
            VALUES (?, ?, ?, ?, ?, ?, 'default.webp')
            """, (uid, fn, ln, em, pw, is_own))

    conn.commit()

    # 2c. Seed Orders if fewer than 9 exist
    cursor.execute('SELECT COUNT(*) FROM "order"')
    order_count = cursor.fetchone()[0]

    if order_count < 9:
        sample_orders = [
            (1, 2, 1, 29.98, 'Delivered', 'Road No 36, Jubilee Hills, Hyderabad', '+91 98765 43210'),
            (2, 2, 1, 16.99, 'Delivered', 'SD Road, Secunderabad', '+91 98765 43210'),
            (3, 2, 5, 24.98, 'Delivered', 'Road No 36, Jubilee Hills, Hyderabad', '+91 98765 43210'),
            (4, 3, 2, 21.48, 'Out for Delivery', 'Banjara Hills, Hyderabad', '+91 98765 11223'),
            (5, 3, 3, 25.98, 'Delivered', 'Sector 2, HITEC City, Hyderabad', '+91 98765 11223'),
            (6, 4, 3, 18.99, 'Preparing Food', 'Madhapur, Hyderabad', '+91 98765 33445'),
            (7, 4, 4, 31.48, 'Delivered', 'Jubilee Hills, Hyderabad', '+91 98765 33445'),
            (8, 5, 9, 19.98, 'Order Confirmed', 'Alandi Road, Dighi, Pune', '+91 98765 55667'),
            (9, 5, 11, 28.48, 'Delivered', 'Vishrantwadi, Pune', '+91 98765 55667')
        ]
        for oid, uid, rid, tot, stat, addr, ph in sample_orders:
            cursor.execute('SELECT id FROM "order" WHERE id = ?', (oid,))
            if not cursor.fetchone():
                cursor.execute("""
                INSERT INTO "order" (id, user_id, restaurant_id, total_price, status, delivery_address, phone)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (oid, uid, rid, tot, stat, addr, ph))

                # Insert corresponding order item
                cursor.execute("""
                INSERT OR IGNORE INTO order_item (order_id, menu_item_id, quantity, price_at_order)
                VALUES (?, 1, 1, ?)
                """, (oid, tot))

        conn.commit()
    cursor.execute("SELECT COUNT(*) FROM restaurant")
    rest_count = cursor.fetchone()[0]

    restaurants_data = [
        {
            "id": 1,
            "name": "Paradise Biryani & Kebabs",
            "description": "Legendary Hyderabadi dum biryani, tender seekh kebabs, and authentic Mughlai specialties crafted with secret royal spice blends.",
            "address": "SD Road, Secunderabad, Hyderabad, Telangana 500003",
            "phone": "+91 40 6666 5555",
            "image_url": "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4411,
            "longitude": 78.4870,
            "rating": 4.8,
            "total_reviews": 128,
            "is_veg": False,
            "cuisine_type": "Biryani, Mughlai, Kebabs",
            "opening_hours": "11:00 AM - 11:30 PM"
        },
        {
            "id": 2,
            "name": "Chutneys South Indian Cuisine",
            "description": "Famous for 7 authentic house-made chutneys, Guntur idlis, crispy dosas, filter coffee, and traditional regional thalis.",
            "address": "Road No 3, Banjara Hills, Hyderabad, Telangana 500034",
            "phone": "+91 40 2335 8484",
            "image_url": "https://images.unsplash.com/photo-1610192244261-3f33de3f55e4?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4239,
            "longitude": 78.4524,
            "rating": 4.6,
            "total_reviews": 94,
            "is_veg": True,
            "cuisine_type": "South Indian, Thali, Pure Veg",
            "opening_hours": "7:00 AM - 10:30 PM"
        },
        {
            "id": 3,
            "name": "Dhaba 1986 Delhi by Heart",
            "description": "Rich Punjabi flavors, Dal Makhani slow-cooked overnight, Amritsari kulchas, butter chicken, and tandoori sizzlers.",
            "address": "Sector 2, HITEC City, Madhapur, Hyderabad, Telangana 500081",
            "phone": "+91 40 4010 1986",
            "image_url": "https://images.unsplash.com/photo-1585937421612-70a008356fbe?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4401,
            "longitude": 78.3489,
            "rating": 4.7,
            "total_reviews": 112,
            "is_veg": False,
            "cuisine_type": "North Indian, Punjabi, Tandoori",
            "opening_hours": "12:00 PM - 11:00 PM"
        },
        {
            "id": 4,
            "name": "Rayalaseema Ruchulu",
            "description": "Fiery Andhra & Rayalaseema delicacies, spicy Gongura mutton, Kodi vepudu, and country-style seafood curries.",
            "address": "Plot 481, Road No 36, Jubilee Hills, Hyderabad, Telangana 500033",
            "phone": "+91 40 2355 4488",
            "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4334,
            "longitude": 78.4072,
            "rating": 4.5,
            "total_reviews": 85,
            "is_veg": False,
            "cuisine_type": "Andhra, Rayalaseema, Spicy Curries",
            "opening_hours": "11:30 AM - 11:00 PM"
        },
        {
            "id": 5,
            "name": "Little Italy Trattoria",
            "description": "Artisan wood-fired Neapolitan pizzas, handmade fresh pastas, creamy risottos, and decadent Italian tiramisu.",
            "address": "Opp. Peddamma Temple, Jubilee Hills, Hyderabad, Telangana 500033",
            "phone": "+91 40 2355 8000",
            "image_url": "https://images.unsplash.com/photo-1513104890138-7c749659a591?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4326,
            "longitude": 78.4116,
            "rating": 4.6,
            "total_reviews": 76,
            "is_veg": False,
            "cuisine_type": "Italian, Pizza, Pasta, European",
            "opening_hours": "12:00 PM - 11:00 PM"
        },
        {
            "id": 6,
            "name": "Mainland China & Asia Kitchen",
            "description": "Authentic Cantonese noodles, fiery Sichuan dishes, Thai aromatic curries, and hand-rolled dim sums.",
            "address": "GS Center Point, Road No 1, Banjara Hills, Hyderabad, Telangana 500034",
            "phone": "+91 40 2330 4500",
            "image_url": "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4285,
            "longitude": 78.4512,
            "rating": 4.7,
            "total_reviews": 104,
            "is_veg": False,
            "cuisine_type": "Chinese, Thai, Pan-Asian",
            "opening_hours": "12:30 PM - 11:00 PM"
        },
        {
            "id": 7,
            "name": "The Burger Club & Fries",
            "description": "Gourmet smashed beef burgers, crispy chicken tenders, peri peri loaded fries, and handcrafted creamy shakes.",
            "address": "Inorbit Mall Road, Madhapur, Hyderabad, Telangana 500081",
            "phone": "+91 40 4221 8899",
            "image_url": "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.4485,
            "longitude": 78.3742,
            "rating": 4.5,
            "total_reviews": 88,
            "is_veg": False,
            "cuisine_type": "Burgers, Fast Food, Fries, Shakes",
            "opening_hours": "11:00 AM - 12:00 AM"
        },
        {
            "id": 8,
            "name": "Mithai Mahal & Sweet Treats",
            "description": "Royal Indian mithai, pure ghee laddoos, melt-in-mouth kaju katli, Bengali rasgulla, and famous Mumbai street chaat.",
            "address": "Station Road, Abids, Hyderabad, Telangana 500001",
            "phone": "+91 40 2474 1234",
            "image_url": "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?q=80&w=1000&auto=format&fit=crop",
            "latitude": 17.3850,
            "longitude": 78.4867,
            "rating": 4.8,
            "total_reviews": 142,
            "is_veg": True,
            "cuisine_type": "Sweets, Desserts, Chaat, Pure Veg",
            "opening_hours": "8:00 AM - 10:30 PM"
        },
        {
            "id": 9,
            "name": "Dighi Darbar Family Restaurant",
            "description": "Popular local dining spot right near AIT campus known for flavorful dum biryanis, tender kebabs, butter chicken, and fresh tandoori breads.",
            "address": "Alandi Road, Near AIT Campus Gate, Dighi, Pune, Maharashtra 411015",
            "phone": "+91 20 2715 8899",
            "image_url": "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?q=80&w=1000&auto=format&fit=crop",
            "latitude": 18.6045,
            "longitude": 73.8720,
            "rating": 4.6,
            "total_reviews": 78,
            "is_veg": False,
            "cuisine_type": "North Indian, Biryani, Mughlai",
            "opening_hours": "11:00 AM - 11:00 PM"
        },
        {
            "id": 10,
            "name": "PK Biryani House",
            "description": "Renowned Pune biryani hotspot serving authentic spicy chicken and mutton dum biryani with signature aromatic rassa and tandoori specials.",
            "address": "Airport Road, Tingre Nagar, Vishrantwadi, Pune, Maharashtra 411015",
            "phone": "+91 20 2668 1234",
            "image_url": "https://images.unsplash.com/photo-1589302168068-964664d93dc0?q=80&w=1000&auto=format&fit=crop",
            "latitude": 18.5810,
            "longitude": 73.8790,
            "rating": 4.7,
            "total_reviews": 142,
            "is_veg": False,
            "cuisine_type": "Biryani, Maharashtrian, Tandoori",
            "opening_hours": "11:30 AM - 11:30 PM"
        },
        {
            "id": 11,
            "name": "Maratha Samrat",
            "description": "Celebrated destination for authentic Maharashtrian delicacies, royal mutton and chicken thalis, spicy Kolhapuri curries, and pandhra-tambda rassa.",
            "address": "Tingre Nagar Chowk, Airport Road, Vishrantwadi, Pune, Maharashtra 411015",
            "phone": "+91 20 2661 5566",
            "image_url": "https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?q=80&w=1000&auto=format&fit=crop",
            "latitude": 18.5778,
            "longitude": 73.8825,
            "rating": 4.8,
            "total_reviews": 198,
            "is_veg": False,
            "cuisine_type": "Authentic Maharashtrian, Thali, Kolhapuri",
            "opening_hours": "12:00 PM - 11:00 PM"
        },
        {
            "id": 12,
            "name": "Irani Cafe",
            "description": "Iconic Pune landmark serving hot aromatic Irani chai, freshly baked maska bun, bun omelette, mutton kheema pav, and classic bakery confectionery.",
            "address": "Datta Mandir Chowk, Viman Nagar, Pune, Maharashtra 411014",
            "phone": "+91 20 2663 8800",
            "image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?q=80&w=1000&auto=format&fit=crop",
            "latitude": 18.5679,
            "longitude": 73.9143,
            "rating": 4.7,
            "total_reviews": 215,
            "is_veg": False,
            "cuisine_type": "Parsi, Irani Chai, Snacks, Bakery",
            "opening_hours": "6:30 AM - 11:00 PM"
        },
        {
            "id": 13,
            "name": "The Burger Club & Cafe (Pune)",
            "description": "Gourmet smashed beef and crispy chicken burgers, peri-peri seasoned loaded fries, and handcrafted creamy thick milkshakes in a vibrant casual setting.",
            "address": "Central Avenue, Kalyani Nagar, Pune, Maharashtra 411006",
            "phone": "+91 20 4123 9900",
            "image_url": "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000&auto=format&fit=crop",
            "latitude": 18.5476,
            "longitude": 73.9022,
            "rating": 4.6,
            "total_reviews": 104,
            "is_veg": False,
            "cuisine_type": "Burgers, Fast Food, Fries, Shakes",
            "opening_hours": "11:00 AM - 12:00 AM"
        },
        {
            "id": 14,
            "name": "Vaishali South Indian Dining",
            "description": "Legendary Pune heritage restaurant famed for crispy Mysore masala dosas, steamed idlis, golden medu vadas, and authentic piping hot filter coffee.",
            "address": "Fergusson College Road, Shivajinagar, Pune, Maharashtra 411004",
            "phone": "+91 20 2553 1244",
            "image_url": "https://images.unsplash.com/photo-1610192244261-3f33de3f55e4?q=80&w=1000&auto=format&fit=crop",
            "latitude": 18.5204,
            "longitude": 73.8410,
            "rating": 4.8,
            "total_reviews": 340,
            "is_veg": True,
            "cuisine_type": "South Indian, Dosas, Pure Veg, Filter Coffee",
            "opening_hours": "7:00 AM - 11:00 PM"
        }
    ]

    for r in restaurants_data:
        cursor.execute("SELECT id FROM restaurant WHERE id = ?", (r["id"],))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("""
            UPDATE restaurant SET
                name=?, description=?, address=?, phone=?, image_url=?, latitude=?, longitude=?,
                rating=?, total_reviews=?, is_veg=?, cuisine_type=?, opening_hours=?
            WHERE id=?
            """, (r["name"], r["description"], r["address"], r["phone"], r["image_url"], r["latitude"],
                  r["longitude"], r["rating"], r["total_reviews"], r["is_veg"], r["cuisine_type"],
                  r["opening_hours"], r["id"]))
        else:
            cursor.execute("""
            INSERT INTO restaurant (id, name, description, address, phone, image_url, latitude, longitude,
                                    rating, total_reviews, is_veg, cuisine_type, opening_hours, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (r["id"], r["name"], r["description"], r["address"], r["phone"], r["image_url"],
                  r["latitude"], r["longitude"], r["rating"], r["total_reviews"], r["is_veg"],
                  r["cuisine_type"], r["opening_hours"]))

    conn.commit()

    # 3b. Seed all Menu Items if table is empty
    cursor.execute("SELECT COUNT(*) FROM menu_item")
    item_count = cursor.fetchone()[0]

    # Category -> Restaurant ID mapping (needed for seeding below)
    cat_to_restaurant_seed = {
        'biryani': 1, 'andhra': 4, 'tamilnadu': 2, 'kerala': 2, 'thali': 2,
        'punjabi': 3, 'rajasthani': 3, 'maharashtrian': 3,
        'pizza': 5, 'pasta': 5, 'european': 5, 'salad': 5,
        'chinese': 6, 'thai': 6,
        'burger': 7, 'fries': 7, 'latinamerican': 7, 'african': 7,
        'sweets': 8, 'dessert': 8, 'snacks': 8, 'drink': 8,
    }

    if item_count == 0:
        print("Seeding menu items from scratch...")
        # Full menu items dataset  — prices in USD
        menu_items_data = [
            # --- BIRYANI (restaurant 1: Paradise Biryani) ---
            ("Hyderabadi Chicken Biryani", 14.99, "Slow-cooked dum biryani with tender chicken, saffron, crispy onions, and royal Hyderabadi spices. Served with raita and mirchi ka salan.", "biryani", "https://images.pexels.com/photos/5410401/pexels-photo-5410401.jpeg?cs=srgb&dl=pexels-saveurs-secretes-5410401.jpg&fm=jpg"),
            ("Hyderabadi Mutton Biryani", 16.99, "Melt-in-mouth tender mutton cooked dum-style with aged basmati rice, fried onions, and aromatic whole spices.", "biryani", "/static/profile_pics/special_biryani.jpg"),
            ("Lucknowi Dum Biryani", 15.99, "Fragrant Awadhi-style dum biryani with kewra water, saffron strands, and succulent mutton pieces sealed in a handis pot.", "biryani", "/static/profile_pics/lucknowi_dum_biryani.jpg"),
            ("Kolkata Biryani", 13.99, "Unique Kolkata-style biryani with potato, egg, and aromatic meat cooked with a subtle, lightly spiced flavor.", "biryani", "/static/profile_pics/kolkata_biryani.jpg"),
            ("Paneer Biryani", 12.99, "Rich vegetarian biryani with paneer cubes marinated in yogurt and spices, slow-cooked with basmati rice and saffron.", "biryani", "/static/profile_pics/Paneer_Biryani.jpg"),
            ("Veg Dum Biryani", 11.99, "Colorful vegetable dum biryani with seasonal veggies, garden-fresh herbs, and fragrant basmati rice cooked in ghee.", "biryani", "/static/profile_pics/Vegetable-Dum-Biryani.jpg"),
            ("Egg Biryani", 12.49, "Protein-rich biryani with boiled eggs cooked in a spiced masala base, layered with fragrant basmati rice.", "biryani", "/static/profile_pics/Egg-Biryani.jpg"),

            # --- THALI (restaurant 2: Chutneys) ---
            ("North Indian Royal Thali", 18.99, "Complete North Indian thali: dal makhani, paneer sabzi, mix veggies, roti, rice, raita, pickle, papad, and gulab jamun.", "thali", "/static/profile_pics/north_thali.webp"),
            ("South Indian Traditional Thali", 14.99, "Traditional South Indian meals with sambar, rasam, kootu, rice, payasam, and 4 types of vegetables and pappad.", "thali", "/static/profile_pics/south_thali.avif"),
            ("Gujarati Thali", 16.99, "Unlimited Gujarati thali with dal, kadhi, shak, roti, rice, puri, papad, farsan, mithai, and traditional pickles.", "thali", "/static/profile_pics/gujarati_th.jpg"),
            ("Rajasthani Thali", 17.99, "Royal Rajasthani thali with dal baati churma, gatte ki sabzi, ker sangri, bajra roti, and sweet ghewar.", "thali", "/static/profile_pics/rajasthani_th.jpg"),
            ("Maharashtrian Thali", 15.99, "Authentic Maharashtra thali with varan bhaat, amti, bhaaji, bharli vangi, poli, sheera, and papad.", "thali", "/static/profile_pics/marathi_th.jpg"),
            ("Punjabi Special Thali", 17.49, "Hearty Punjabi thali with dal makhani, butter chicken, naan, tandoori roti, raita, salad, and kheer.", "thali", "/static/profile_pics/punjabi-th.webp"),

            # --- SWEETS (restaurant 8: Mithai Mahal) ---
            ("Gulab Jamun", 5.99, "Soft khoya milk dumplings deep fried golden and soaked in saffron-rose sugar syrup — the king of Indian sweets.", "sweets", "/static/profile_pics/gulab_jamun.webp"),
            ("Rasgulla", 5.49, "Spongy chenna balls cooked in light sugar syrup — the iconic Bengali mithai that melts in your mouth.", "sweets", "/static/profile_pics/rasgulla.jpg"),
            ("Kaju Katli", 8.99, "Premium cashew nut fudge rolled in silver vark — the most gifted Indian festive sweet, made with pure ghee.", "sweets", "/static/profile_pics/kaju_burfi.webp"),
            ("Jalebi", 4.99, "Crispy spiral-shaped fried sweet soaked in warm sugar syrup, best enjoyed fresh with rabdi or samosa.", "sweets", "/static/profile_pics/jalebi.webp"),
            ("Rasmalai", 6.99, "Soft chenna patties soaked in chilled saffron-cardamom rabdi with pistachio and rose petal garnish.", "sweets", "/static/profile_pics/rasamalai.webp"),
            ("Motichoor Laddu", 5.99, "Melt-in-mouth boondi laddus made with fine saffron-tinged besan pearls, ghee, and aromatic cardamom.", "sweets", "/static/profile_pics/MotichoorLaddu.webp"),
            ("Mysore Pak", 6.49, "Traditional Karnataka sweet made from pure ghee, chickpea flour, and sugar — crumbly, rich, and irresistible.", "sweets", "/static/profile_pics/MysorePak.webp"),

            # --- SNACKS (restaurant 8: Mithai Mahal) ---
            ("Samosa", 3.99, "Crispy triangular pastry stuffed with spiced potato and peas, served with tamarind chutney and mint chutney.", "snacks", "/static/profile_pics/samosa.jpg"),
            ("Aloo Tikki Chaat", 5.49, "Crispy potato patties topped with yogurt, tamarind, green chutney, chaat masala, and sev — a street-food classic.", "snacks", "/static/profile_pics/Chat.jpg"),
            ("Pani Puri", 4.99, "Hollow crispy puris filled with spiced mint water, chickpeas, potato, and tangy tamarind — the ultimate street food.", "snacks", "/static/profile_pics/Pani-Puri.webp"),
            ("Dahi Puri", 5.49, "Crispy puris topped with creamy yogurt, sweet tamarind, spicy chutneys, sev, and fresh pomegranate seeds.", "snacks", "/static/profile_pics/dahi-puri.jpg"),
            ("Pav Bhaji", 7.99, "Mumbai's iconic thick vegetable mash served with buttered pav rolls, raw onion, lime, and coriander garnish.", "snacks", "/static/profile_pics/pav_bhaji.webp"),
            ("Vada Pav", 4.99, "Mumbai's beloved street burger: spiced potato vada in a soft pav with dry garlic chutney and green chili.", "snacks", "/static/profile_pics/Vada-Pav.webp"),
            ("Masala Corn", 4.49, "Hot steamed corn kernels tossed with butter, lemon, chaat masala, red chili powder, and fresh herbs.", "snacks", "/static/profile_pics/MasalaCorn.jpg"),
            ("Bread Pakora", 4.49, "Thick bread slices stuffed with spiced potato, dipped in gram flour batter, and deep fried to golden crunch.", "snacks", "/static/profile_pics/bread-pakoda.jpg"),

            # --- PUNJABI (restaurant 3: Dhaba 1986) ---
            ("Butter Chicken", 14.99, "Iconic Punjabi curry with tandoori chicken simmered in rich tomato-cream gravy with butter, fenugreek, and spices.", "punjabi", "/static/profile_pics/butter-chicken.jpg"),
            ("Amritsari Kulcha", 9.99, "Leavened flatbread stuffed with spiced paneer or potato, baked in tandoor, served with chole and white butter.", "punjabi", "/static/profile_pics/amritsari-kulcha.avif"),
            ("Sarson da Saag with Makki di Roti", 12.99, "Classic Punjabi winter comfort food: mustard greens saag with makki (cornmeal) rotis and white butter.", "punjabi", "/static/profile_pics/sarson_ka_saag.webp"),
            ("Paneer Butter Masala", 12.99, "Tender paneer cubes in a luscious, velvety tomato-cashew-butter gravy — a vegetarian masterpiece.", "punjabi", "/static/profile_pics/paneer-butter-masala.jpg"),
            ("Dal Makhani", 10.99, "Black urad dal and kidney beans slow-cooked overnight with cream, butter, and tomatoes — deeply comforting.", "punjabi", "/static/profile_pics/dal-makhani.webp"),
            ("Chole Bhature", 11.99, "Spiced Punjab-style chickpea curry served with pillowy deep-fried bhatura bread — a weekend breakfast classic.", "punjabi", "/static/profile_pics/chole-bhature.png"),
            ("Tandoori Chicken", 13.99, "Whole chicken marinated in yogurt and spices, roasted in a clay tandoor for a smoky char with juicy interior.", "punjabi", "/static/profile_pics/tandoori.jpg"),
            ("Paneer Tikka", 11.99, "Chunks of paneer marinated in yogurt and spices, chargrilled in tandoor with capsicum and onion.", "punjabi", "/static/profile_pics/paneer-tikka.jpg"),
            ("Chicken Tikka", 12.99, "Boneless chicken pieces marinated in yogurt, lemon, and spices, skewered and grilled in a hot tandoor.", "punjabi", "/static/profile_pics/chicken-tikka.jpg"),
            ("Sweet Lassi", 4.99, "Chilled blended yogurt with sugar, cardamom, and rose water — the perfect cooling Punjabi drink.", "punjabi", "/static/profile_pics/lassi.webp"),

            # --- ANDHRA (restaurant 4: Rayalaseema Ruchulu) ---
            ("Andhra Chicken Curry", 13.99, "Fiery Andhra-style chicken curry with generous use of red chilies, tamarind, coconut, and fresh curry leaves.", "andhra", "/static/profile_pics/Andhra-Chicken-Curry.jpg"),
            ("Gongura Mutton", 15.99, "Tender mutton cooked with sour Gongura (sorrel leaves) — Andhra's signature dish with intense tanginess.", "andhra", "/static/profile_pics/gongura-mutton.jpg"),
            ("Andhra Fish Fry", 13.49, "Marinated fresh fish shallow-fried with Andhra spice paste of ginger, garlic, red chili, and turmeric.", "andhra", "/static/profile_pics/andhra-fish-curry.jpg"),
            ("Kodi Vepudu", 13.99, "Dry-fried Andhra chicken with onions, curry leaves, and a blend of fiery spices — crispy and deeply flavored.", "andhra", "/static/profile_pics/kodi-vepudu.jpg"),
            ("Andhra Prawn Curry", 15.49, "Juicy prawns cooked in a thick, spicy Andhra gravy with coconut, tamarind, and roasted spices.", "andhra", "/static/profile_pics/andhra-prawn-curry.jpg"),
            ("Royyala Iguru", 14.99, "Andhra prawn stir-fry cooked with green chilies, onions, tomatoes, and fresh curry leaves in minimal oil.", "andhra", "/static/profile_pics/royyala-iguru.webp"),
            ("Andhra Spicy Biryani", 14.49, "Super-spicy Andhra-style biryani with intense chili heat, aromatic whole spices, and tender meat pieces.", "andhra", "/static/profile_pics/andhra-spicy-biryani.jpg"),
            ("Tomato Pappu", 8.99, "Andhra toor dal cooked with ripe tomatoes, tamarind, and spices — comfort food served with hot white rice.", "andhra", "/static/profile_pics/tomato-pappu.jpg"),
            ("Andhra Rasam", 5.99, "Thin tangy Andhra pepper-tamarind soup loaded with tomatoes and aromatic spices — aids digestion and warms up.", "andhra", "/static/profile_pics/rasam.jpg"),
            ("Gutti Vankaya Curry", 11.99, "Baby eggplants stuffed with a ground peanut-sesame-coconut masala and slow-cooked in tamarind gravy.", "andhra", "/static/profile_pics/vankaya-curry.jpg"),

            # --- TAMILNADU (restaurant 2: Chutneys) ---
            ("Chettinad Chicken", 14.49, "Authentic Chettinad dry chicken curry with kalpasi, marathi mokku, stone flower, and intense spice blend.", "tamilnadu", "/static/profile_pics/Chicken-Chettinad.jpg"),
            ("Chicken Chettinad Biryani", 14.99, "Aromatic Chettinad biryani with seeraga samba rice, coconut milk, and fiery ground spice paste.", "tamilnadu", "/static/profile_pics/chettinad-biryani.webp"),
            ("Karaikudi Mutton Curry", 15.99, "Tender mutton in a thick Karaikudi-style gravy with freshly ground masala and coconut base.", "tamilnadu", "/static/profile_pics/Tamil-style-mutton-biryani.webp"),
            ("Idli with Sambar", 7.99, "Soft steamed rice and lentil idlis served with house-made sambar and 7 authentic chutneys.", "tamilnadu", "/static/profile_pics/idli_sambar.jpg"),
            ("Dosa with Chutney", 8.99, "Thin golden crispy rice-lentil crepe served with coconut chutney, tomato chutney, and piping hot sambar.", "tamilnadu", "/static/profile_pics/dosa.jpg"),
            ("Pongal", 7.49, "Comforting Tamil breakfast of rice and lentil cooked together with ghee, cumin, black pepper, and cashews.", "tamilnadu", "/static/profile_pics/pongal.jpg"),
            ("Lemon Rice", 8.49, "Tangy turmeric-tinted rice tossed with lemon juice, mustard seeds, curry leaves, and roasted peanuts.", "tamilnadu", "/static/profile_pics/lemon-rice.gif"),
            ("Tamarind Rice", 8.49, "Puliyodarai — tamarind rice with a complex spice powder of sesame, chana dal, peanuts, and dried chili.", "tamilnadu", "/static/profile_pics/tamarindrice.webp"),
            ("Medu Vada", 5.99, "Crispy golden urad dal donuts with a crunchy exterior, soft interior, served with sambar and coconut chutney.", "tamilnadu", "/static/profile_pics/medu-vada.webp"),
            ("Filter Coffee", 3.49, "Traditional South Indian devanagari-brewed filter coffee poured frothy between tumblers — aromatic perfection.", "tamilnadu", "/static/profile_pics/coffee.webp"),

            # --- KERALA (restaurant 2: Chutneys) ---
            ("Kerala Fish Curry", 14.49, "Meen Curry: fish simmered in a tangy coconut milk and kudampuli (Malabar tamarind) curry leaf broth.", "kerala", "/static/profile_pics/Kerala-Fish-Curry.jpg"),
            ("Malabar Chicken Biryani", 14.99, "Fragrant Thalassery biryani with jeerakasala rice, whole spices, coconut milk, and tender chicken pieces.", "kerala", "/static/profile_pics/malabar-chicken-biryani.jpg"),
            ("Appam with Vegetable Stew", 9.99, "Lacy, fermented rice crepes with a thin center, served with creamy coconut milk vegetable stew.", "kerala", "/static/profile_pics/appam.jpg"),
            ("Kerala Prawn Curry", 14.99, "Fresh tiger prawns cooked in a tangy coconut milk curry with raw mango and green chilies.", "kerala", "/static/profile_pics/Kerala-Prawn-Curry.jpg"),
            ("Kerala Beef Fry", 13.99, "Slow-cooked Kerala beef roast with coconut strips, curry leaves, and freshly ground spices — a classic.", "kerala", "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=1000&auto=format&fit=crop"),
            ("Kerala Parotta with Curry", 10.99, "Flaky, layered Malabar parotta (wheat flatbread) served with spicy chicken or egg curry.", "kerala", "https://images.unsplash.com/photo-1565557623262-b51c2513a641?q=80&w=1000&auto=format&fit=crop"),
            ("Avial", 9.99, "Kerala mixed vegetable curry in coconut-yogurt-coconut oil base — a traditional Onam Sadya staple.", "kerala", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=1000&auto=format&fit=crop"),
            ("Kerala Sadya", 19.99, "Grand festive meal served on banana leaf with 20+ dishes: avial, sambar, kootu, payasam, pappadam, and pickle.", "kerala", "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?q=80&w=1000&auto=format&fit=crop"),
            ("Banana Chips", 3.99, "Thinly sliced raw banana deep fried in coconut oil with turmeric and salt — a popular Kerala snack.", "kerala", "https://images.unsplash.com/photo-1621143386748-de75e60e67ea?q=80&w=1000&auto=format&fit=crop"),
            ("Payasam", 6.49, "Kerala rice or vermicelli pudding made with coconut milk, jaggery, cardamom, and cashews — sweet celebration.", "kerala", "https://images.unsplash.com/photo-1551024601-bec78aea704b?q=80&w=1000&auto=format&fit=crop"),

            # --- MAHARASHTRIAN (restaurant 3: Dhaba 1986) ---
            ("Misal Pav", 8.99, "Spicy sprouted matki bean curry topped with crunchy farsan, onion, tomato, lime, served with pav bread.", "maharashtrian", "https://images.unsplash.com/photo-1606491956689-2ea866880c84?q=80&w=1000&auto=format&fit=crop"),
            ("Puran Poli", 5.99, "Sweet Maharashtrian flatbread stuffed with jaggery-chana dal filling, served with pure ghee — festive delight.", "maharashtrian", "https://images.unsplash.com/photo-1601050690597-df0568f70950?q=80&w=1000&auto=format&fit=crop"),
            ("Sabudana Khichdi", 7.99, "Fasting-friendly sago pearls sautéed with peanuts, green chili, and cumin — crispy, chewy, and satisfying.", "maharashtrian", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=1000&auto=format&fit=crop"),
            ("Kanda Bhaji", 5.49, "Crispy fritters made with thinly sliced onions and besan batter spiced with chili and coriander — Mumbai's rain snack.", "maharashtrian", "https://images.unsplash.com/photo-1585238342024-78d387f4a707?q=80&w=1000&auto=format&fit=crop"),
            ("Thalipeeth", 7.49, "Multi-grain Maharashtra flatbread made from bhajni flour, spiced with onion, chili, and fresh coriander.", "maharashtrian", "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?q=80&w=1000&auto=format&fit=crop"),
            ("Kolhapuri Chicken", 14.49, "Fiery, dry Kolhapur-style chicken in a pungent red coconut masala — rated one of India's hottest preparations.", "maharashtrian", "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?q=80&w=1000&auto=format&fit=crop"),
            ("Kolhapuri Mutton", 15.49, "Tender mutton in the classic spicy Kolhapuri masala with dry coconut, sesame, poppy seeds, and red chilies.", "maharashtrian", "https://images.unsplash.com/photo-1547592166-23ac45744acd?q=80&w=1000&auto=format&fit=crop"),
            ("Modak", 6.99, "Sacred Ganesh festival sweet: steamed rice flour dumpling stuffed with jaggery-coconut filling — Lord Ganesha's favorite.", "maharashtrian", "https://images.unsplash.com/photo-1578985545062-69928b1d9587?q=80&w=1000&auto=format&fit=crop"),

            # --- RAJASTHANI (restaurant 3: Dhaba 1986) ---
            ("Dal Baati Churma", 13.99, "Rajasthani classic: baked wheat balls (baati) with thick dal and sweet churma — the ultimate desert kingdom meal.", "rajasthani", "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?q=80&w=1000&auto=format&fit=crop"),
            ("Gatte ki Sabzi", 9.99, "Besan (chickpea flour) dumplings in a tangy yogurt-based spiced curry — a Rajasthani vegetarian treasure.", "rajasthani", "https://images.unsplash.com/photo-1631452180539-96aca7d48617?q=80&w=1000&auto=format&fit=crop"),
            ("Laal Maas", 15.99, "Fiery Rajasthani mutton curry in a vivid red sauce of dried Mathania red chilies, garlic, and yogurt.", "rajasthani", "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?q=80&w=1000&auto=format&fit=crop"),
            ("Ker Sangri", 10.99, "Desert vegetable curry made from dried ker berries and sangri beans — a unique and earthy Rajasthani delicacy.", "rajasthani", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=1000&auto=format&fit=crop"),
            ("Rajasthani Kadhi", 8.99, "Tangy yogurt and chickpea flour curry with pakoda fritters, tempered with mustard, cumin, and curry leaves.", "rajasthani", "https://images.unsplash.com/photo-1631452180519-6b0e15f2a543?q=80&w=1000&auto=format&fit=crop"),
            ("Bajra Roti with Garlic Chutney", 5.99, "Rustic pearl millet flatbread served with pungent garlic chutney and churned white butter — rural Rajasthani delight.", "rajasthani", "https://images.unsplash.com/photo-1555939594-58d7cb561ad1?q=80&w=1000&auto=format&fit=crop"),
            ("Mawa Kachori", 7.99, "Deep-fried flaky pastry shells stuffed with sweet mawa (khoya), nuts, and dry fruits — Jodhpur's festive mithai.", "rajasthani", "https://images.unsplash.com/photo-1606491956689-2ea866880c84?q=80&w=1000&auto=format&fit=crop"),
            ("Mirchi Vada", 5.49, "Oversized green chili stuffed with spiced potato filling, dipped in besan batter, deep fried — Jodhpur street icon.", "rajasthani", "https://images.unsplash.com/photo-1548927249-9b90ce49f71f?q=80&w=1000&auto=format&fit=crop"),
            ("Ghewar", 6.99, "Round honeycomb-textured crispy sweet soaked in sugar syrup, topped with rabdi and dry fruits — Teej festival special.", "rajasthani", "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?q=80&w=1000&auto=format&fit=crop"),

            # --- CHINESE (restaurant 6: Mainland China) ---
            ("Veg Hakka Noodles", 9.99, "Stir-fried Hakka noodles with crisp vegetables, soy sauce, and sesame oil — light, healthy, and satisfying.", "chinese", "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?q=80&w=1000&auto=format&fit=crop"),
            ("Chicken Hakka Noodles", 11.99, "Wok-tossed noodles with juicy chicken strips, cabbage, carrots, capsicum, spring onions, and soy-garlic sauce.", "chinese", "https://images.unsplash.com/photo-1585032226651-759b368d7246?q=80&w=1000&auto=format&fit=crop"),
            ("Schezwan Fried Rice", 10.99, "Spicy Sichuan-style fried rice with Schezwan sauce, mixed vegetables, scrambled egg, and crispy garlic.", "chinese", "https://images.unsplash.com/photo-1603133872878-684f208fb84b?q=80&w=1000&auto=format&fit=crop"),
            ("Chicken Manchurian", 12.99, "Crispy golden chicken balls tossed in a tangy Indo-Chinese Manchurian sauce with spring onions and peppers.", "chinese", "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?q=80&w=1000&auto=format&fit=crop"),
            ("Veg Manchurian", 10.49, "Golden veggie dumplings in a dark, tangy, spiced Manchurian gravy — a popular Indo-Chinese favourite.", "chinese", "https://images.unsplash.com/photo-1512058564366-18510be2db19?q=80&w=1000&auto=format&fit=crop"),
            ("Spring Rolls", 7.99, "Crispy thin rolls stuffed with stir-fried cabbage, carrots, glass noodles, and seasoning — a dim sum classic.", "chinese", "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=1000&auto=format&fit=crop"),
            ("Hot and Sour Soup", 6.99, "Thick Chinese soup with mushrooms, tofu, bamboo shoots, vinegar, white pepper, and egg ribbons — warming and tangy.", "chinese", "https://images.unsplash.com/photo-1547592180-85f173990554?q=80&w=1000&auto=format&fit=crop"),
            ("Chili Chicken", 12.99, "Deep-fried chicken tossed in a fiery Indo-Chinese chili sauce with bell peppers, spring onions, and soy.", "chinese", "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?q=80&w=1000&auto=format&fit=crop"),
            ("Garlic Noodles", 9.49, "Tossed noodles with butter, minced garlic, parmesan cheese, and fresh parsley — simple, rich, and addictive.", "chinese", "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?q=80&w=1000&auto=format&fit=crop"),

            # --- THAI (restaurant 6: Mainland China) ---
            ("Pad Thai Noodles", 11.99, "Thailand's national dish: flat rice noodles stir-fried with tofu or shrimp, egg, bean sprouts, and peanuts.", "thai", "https://images.unsplash.com/photo-1559314809-0d155014e29e?q=80&w=1000&auto=format&fit=crop"),
            ("Thai Green Curry", 13.49, "Aromatic Thai green curry with lemongrass, kaffir lime, galangal, coconut milk, and your choice of protein.", "thai", "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?q=80&w=1000&auto=format&fit=crop"),
            ("Thai Red Curry", 13.49, "Rich Thai red curry paste cooked in coconut milk with bamboo shoots, Thai basil, and bell peppers.", "thai", "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=1000&auto=format&fit=crop"),
            ("Thai Basil Chicken", 12.99, "Minced chicken stir-fried with holy basil, fish sauce, oyster sauce, and bird's eye chili over jasmine rice.", "thai", "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?q=80&w=1000&auto=format&fit=crop"),
            ("Mango Sticky Rice", 7.99, "Sweet glutinous rice cooked with coconut milk, served warm with chilled ripe mango slices — Thai dessert royalty.", "thai", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=1000&auto=format&fit=crop"),
            ("Thai Fried Rice", 10.99, "Jasmine rice stir-fried with egg, veggies, fish sauce, lime, and coriander — a quick, flavourful Thai classic.", "thai", "https://images.unsplash.com/photo-1603133872878-684f208fb84b?q=80&w=1000&auto=format&fit=crop"),
            ("Tom Yum Soup", 8.99, "Iconic Thai hot-and-sour clear soup with lemongrass, galangal, kaffir lime leaves, mushrooms, and fresh chili.", "thai", "https://images.unsplash.com/photo-1547592180-85f173990554?q=80&w=1000&auto=format&fit=crop"),
            ("Pineapple Fried Rice", 10.49, "Thai fried rice served inside a scooped pineapple with cashews, raisins, shrimp, curry powder, and coconut milk.", "thai", "https://images.unsplash.com/photo-1603133872878-684f208fb84b?q=80&w=1000&auto=format&fit=crop"),

            # --- PIZZA (restaurant 5: Little Italy) ---
            ("Margherita Pizza", 12.99, "Classic Neapolitan pizza with San Marzano tomato sauce, fresh mozzarella, basil leaves, and extra-virgin olive oil.", "pizza", "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?q=80&w=1000&auto=format&fit=crop"),
            ("Pepperoni Pizza", 14.99, "American-style pizza loaded with spicy cured pepperoni slices, mozzarella, and tomato on a hand-tossed crust.", "pizza", "https://images.unsplash.com/photo-1628840042765-356cda07504e?q=80&w=1000&auto=format&fit=crop"),
            ("BBQ Chicken Pizza", 14.49, "Tangy BBQ sauce base with grilled chicken, red onion, jalapeño, smoked cheese, and fresh coriander.", "pizza", "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=1000&auto=format&fit=crop"),
            ("Veggie Delight Pizza", 12.49, "Colorful wood-fired pizza with roasted bell peppers, olives, mushrooms, caramelized onion, and mozzarella.", "pizza", "https://images.unsplash.com/photo-1585238342024-78d387f4a707?q=80&w=1000&auto=format&fit=crop"),

            # --- PASTA (restaurant 5: Little Italy) ---
            ("Pasta Alfredo", 12.99, "Silky fettuccine coated in a rich Parmesan-butter Alfredo cream sauce — simple Italian elegance at its best.", "pasta", "https://images.unsplash.com/photo-1645112411341-6c4fd023714a?q=80&w=1000&auto=format&fit=crop"),
            ("Red Sauce Pasta", 11.99, "Al dente penne in a slow-cooked San Marzano tomato-basil arrabbiata sauce with garlic and parmesan.", "pasta", "/static/profile_pics/red_sauce_pasta.avif"),
            ("Pesto Pasta", 12.49, "Fresh housemade Genovese basil pesto tossed with al dente fusilli, cherry tomatoes, and toasted pine nuts.", "pasta", "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?q=80&w=1000&auto=format&fit=crop"),
            ("Four Cheese Pasta", 13.49, "Indulgent pasta in a four-cheese sauce: mozzarella, gorgonzola, parmesan, and pecorino — rich and decadent.", "pasta", "https://images.unsplash.com/photo-1551183053-bf91a1d81141?q=80&w=1000&auto=format&fit=crop"),

            # --- BURGER (restaurant 7: The Burger Club) ---
            ("Veggie Burger", 9.99, "Hearty grilled veggie patty with lettuce, tomato, pickles, and house sauce in a toasted sesame brioche bun.", "burger", "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000&auto=format&fit=crop"),
            ("Cheese Burst Burger", 11.99, "Double smash patty burger with a cheese-filled core, caramelized onions, American cheese slices, and secret sauce.", "burger", "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=1000&auto=format&fit=crop"),
            ("Crispy Chicken Burger", 11.49, "Crunchy buttermilk fried chicken fillet with coleslaw, pickles, and spicy sriracha mayo in a brioche bun.", "burger", "/static/profile_pics/crispy_chicken_burger.jpg"),
            ("Smoky BBQ Burger", 12.99, "Juicy beef patty with house-smoked pulled pork, BBQ sauce, crispy onion rings, and cheddar on a pretzel bun.", "burger", "/static/profile_pics/smoky_bbq_burger.jpg"),

            # --- DRINKS (restaurant 8: Mithai Mahal) ---
            ("Cold Coffee", 4.99, "Blended iced coffee with milk, sugar, and cream — richly chilled, deeply caffeinated, and absolutely refreshing.", "drink", "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?q=80&w=1000&auto=format&fit=crop"),
            ("Lemon Iced Tea", 3.99, "Freshly brewed black tea chilled over ice, sweetened, and finished with a squeeze of lemon and mint sprig.", "drink", "https://images.unsplash.com/photo-1556881286-fc6915169721?q=80&w=1000&auto=format&fit=crop"),
            ("Strawberry Milkshake", 5.49, "Thick blended shake with fresh strawberries, vanilla ice cream, cold milk, and a whipped cream topping.", "drink", "https://images.unsplash.com/photo-1579954115545-a95591f28bfc?q=80&w=1000&auto=format&fit=crop"),
            ("Mojito", 4.49, "Refreshing mocktail with muddled mint leaves, lime juice, sugar syrup, and chilled sparkling water over ice.", "drink", "https://images.unsplash.com/photo-1551538827-9c037cb4f32a?q=80&w=1000&auto=format&fit=crop"),

            # --- SALAD (restaurant 5: Little Italy) ---
            ("Caesar Salad", 8.99, "Classic romaine lettuce with parmesan, house-made Caesar dressing, croutons, capers, and anchovy — crisp and tangy.", "salad", "https://images.unsplash.com/photo-1550304943-4f24f54ddde9?q=80&w=1000&auto=format&fit=crop"),
            ("Greek Salad", 8.49, "Chunky tomatoes, cucumbers, olives, red onion, and feta cheese with olive oil and oregano — Mediterranean freshness.", "salad", "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=1000&auto=format&fit=crop"),
            ("Garden Fresh Salad", 7.49, "Crisp seasonal greens with cherry tomatoes, cucumber, carrots, radish, and a light vinaigrette dressing.", "salad", "https://images.unsplash.com/photo-1540420773420-3366772f4999?q=80&w=1000&auto=format&fit=crop"),
            ("Protein Salad", 10.49, "Grilled chicken or tofu over mixed greens with avocado, pumpkin seeds, quinoa, and lemon-tahini dressing.", "salad", "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=1000&auto=format&fit=crop"),

            # --- DESSERT (restaurant 8: Mithai Mahal) ---
            ("Chocolate Cake", 6.99, "Moist, rich dark chocolate layer cake with ganache frosting, chocolate chips, and a dusting of cocoa powder.", "dessert", "https://images.unsplash.com/photo-1578985545062-69928b1d9587?q=80&w=1000&auto=format&fit=crop"),
            ("Brownie with Ice Cream", 7.49, "Warm fudgy chocolate brownie topped with a scoop of vanilla bean ice cream, drizzled with chocolate sauce.", "dessert", "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?q=80&w=1000&auto=format&fit=crop"),
            ("Donuts", 5.49, "Freshly glazed yeast donuts in classic, chocolate, and strawberry — soft, pillowy, and beautifully topped.", "dessert", "https://images.unsplash.com/photo-1551024601-bec78aea704b?q=80&w=1000&auto=format&fit=crop"),

            # --- FRIES (restaurant 7: The Burger Club) ---
            ("French Fries", 4.99, "Golden shoestring fries double-fried to crispy perfection, seasoned with sea salt and served with dipping sauce.", "fries", "/static/profile_pics/french_fries.jpg"),
            ("Peri Peri Fries", 5.49, "Crispy fries tossed in fiery peri peri seasoning with a squeeze of lime — irresistibly spicy and addictive.", "fries", "https://images.unsplash.com/photo-1590301157890-4810ed352733?q=80&w=1000&auto=format&fit=crop"),
            ("Garlic Bread", 4.49, "Thick-cut bread toasted with garlic butter, fresh parsley, and optional mozzarella — the perfect meal starter.", "fries", "/static/profile_pics/garlic_bread.jpg"),
            ("Fruit Bowl", 5.99, "Seasonal fresh fruit medley with watermelon, mango, berries, and kiwi, drizzled with honey and mint.", "fries", "/static/profile_pics/fruit_bowl.jpg"),

            # --- EUROPEAN (restaurant 5: Little Italy) ---
            ("Spaghetti Carbonara", 13.49, "Roman pasta: spaghetti with guanciale, egg yolk, pecorino romano, and black pepper — no cream, just perfection.", "european", "https://images.unsplash.com/photo-1595295333158-4742f28fbd85?q=80&w=1000&auto=format&fit=crop"),
            ("Mushroom Risotto", 13.99, "Creamy Arborio rice with wild mushrooms, white wine, parmesan, and truffle oil — Italian comfort in a bowl.", "european", "https://images.unsplash.com/photo-1476124369491-e7addf5db371?q=80&w=1000&auto=format&fit=crop"),
            ("Chicken Alfredo Pasta", 13.99, "Tender grilled chicken over fettuccine in a rich Parmesan Alfredo sauce with garlic and fresh herbs.", "european", "https://images.unsplash.com/photo-1645112411341-6c4fd023714a?q=80&w=1000&auto=format&fit=crop"),
            ("Fish and Chips", 14.49, "British classic: battered, deep-fried cod fillet with thick-cut chips, mushy peas, tartar sauce, and malt vinegar.", "european", "https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?q=80&w=1000&auto=format&fit=crop"),
            ("Grilled Lamb Steak", 19.99, "Herb-marinated lamb leg steak grilled to medium-rare, served with roasted vegetables and red wine jus.", "european", "https://images.unsplash.com/photo-1544025162-d76694265947?q=80&w=1000&auto=format&fit=crop"),
            ("Lasagna", 13.99, "Layers of pasta sheets with rich beef Bolognese, béchamel sauce, and parmesan — oven-baked to bubbling perfection.", "european", "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?q=80&w=1000&auto=format&fit=crop"),
            ("Bruschetta", 7.49, "Grilled sourdough toasts rubbed with garlic, topped with fresh tomato, basil, olive oil, and aged balsamic glaze.", "european", "https://images.unsplash.com/photo-1572441710227-a6a963da8e73?q=80&w=1000&auto=format&fit=crop"),
            ("French Onion Soup", 8.49, "Slow-caramelized sweet onion soup in beef broth, topped with a croûton and gratinéed Gruyère cheese.", "european", "https://images.unsplash.com/photo-1547592180-85f173990554?q=80&w=1000&auto=format&fit=crop"),

            # --- LATIN AMERICAN (restaurant 7: The Burger Club) ---
            ("Mexican Burrito Bowl", 12.99, "Cilantro-lime rice bowl with black beans, grilled chicken or veggies, guacamole, salsa, and sour cream.", "latinamerican", "https://images.unsplash.com/photo-1512058564366-18510be2db19?q=80&w=1000&auto=format&fit=crop"),
            ("Chicken Quesadilla", 10.99, "Toasted flour tortilla filled with seasoned chicken, melted cheddar, peppers, and onions — served with salsa.", "latinamerican", "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=1000&auto=format&fit=crop"),
            ("Beef Tacos", 11.49, "Three soft corn tortillas with spiced ground beef, pickled jalapeños, shredded lettuce, salsa, and crema.", "latinamerican", "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?q=80&w=1000&auto=format&fit=crop"),
            ("Veg Enchiladas", 10.99, "Corn tortillas stuffed with spiced veggies, rolled, baked under red enchilada sauce, and topped with cheese.", "latinamerican", "https://images.unsplash.com/photo-1570461226513-e08b58b7c8e2?q=80&w=1000&auto=format&fit=crop"),
            ("Nachos Supreme", 9.99, "Tortilla chips loaded with nacho cheese, jalapeños, black beans, guacamole, pico de gallo, and sour cream.", "latinamerican", "https://images.unsplash.com/photo-1548567820-5f1e5e5c2d60?q=80&w=1000&auto=format&fit=crop"),
            ("Mexican Street Corn", 6.99, "Elote: grilled corn on the cob slathered in mayo, cotija cheese, chili powder, and lime juice — street magic.", "latinamerican", "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?q=80&w=1000&auto=format&fit=crop"),
            ("Chimichanga", 11.99, "Deep-fried flour tortilla filled with seasoned beef or chicken, rice, and beans — topped with cheese sauce.", "latinamerican", "https://images.unsplash.com/photo-1593560708920-61dd98c46a4e?q=80&w=1000&auto=format&fit=crop"),

            # --- AFRICAN (restaurant 7: The Burger Club) ---
            ("Jollof Rice", 10.99, "West African one-pot festive rice cooked in a spiced tomato-pepper broth — smoky, vibrant, and deeply satisfying.", "african", "https://images.unsplash.com/photo-1603133872878-684f208fb84b?q=80&w=1000&auto=format&fit=crop"),
            ("Chicken Yassa", 12.99, "Senegalese slow-braised chicken in a caramelized onion-lemon-mustard sauce — tangy and beautifully aromatic.", "african", "https://images.unsplash.com/photo-1606491956689-2ea866880c84?q=80&w=1000&auto=format&fit=crop"),
            ("Bunny Chow", 11.49, "South African street food: a hollowed half-loaf filled with rich, hearty curry — eat the bread bowl too!", "african", "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=1000&auto=format&fit=crop"),
            ("Moroccan Chicken Tagine", 13.99, "Slow-cooked Moroccan chicken with preserved lemon, olives, saffron, and warm spices in a traditional tagine pot.", "african", "https://images.unsplash.com/photo-1547592180-85f173990554?q=80&w=1000&auto=format&fit=crop"),
            ("Couscous Royal", 12.49, "Fluffy steamed couscous served with mixed grilled meats, vegetables, and a rich spiced broth on the side.", "african", "https://images.unsplash.com/photo-1512058564366-18510be2db19?q=80&w=1000&auto=format&fit=crop"),
            ("Peri Peri Chicken", 13.99, "Mozambican flame-grilled chicken marinated in fiery African bird's eye chili, garlic, lemon, and herbs.", "african", "https://images.unsplash.com/photo-1588166524941-3bf61a9c41db?q=80&w=1000&auto=format&fit=crop"),
            ("Ethiopian Doro Wat", 13.49, "Ethiopia's national dish: chicken stewed in a deep, spiced berbere sauce with hard-boiled eggs and niter kibbeh.", "african", "https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?q=80&w=1000&auto=format&fit=crop"),
        ]

        non_veg_keywords = ['chicken', 'mutton', 'fish', 'prawn', 'egg', 'beef', 'lamb', 'pork', 'bacon', 'pepperoni',
                            'meat', 'doro', 'laal maas', 'royyala', 'kodi', 'karaikudi', 'gongura mutton', 'seafood', 'shrimp']
        spicy_keywords = ['spicy', 'chili', 'schezwan', 'peri peri', 'kolhapuri', 'chettinad', 'hot and sour',
                          'andhra', 'curry', 'vepudu', 'tikka', 'masala', 'tagine', 'gongura', 'manchurian',
                          'laal maas', 'thai red', 'thai green', 'mirchi', 'mirchi vada', 'doro wat', 'berbere']

        for (name, price, desc, cat, img_url) in menu_items_data:
            name_lower = name.lower()
            is_veg = not any(kw in name_lower for kw in non_veg_keywords)
            is_spicy = any(kw in name_lower for kw in spicy_keywords) or cat in ['andhra', 'punjabi']
            rest_id = cat_to_restaurant_seed.get(cat, 1)
            cursor.execute("""
            INSERT OR IGNORE INTO menu_item (name, price, description, category, image_url, is_veg, is_spicy, rating, restaurant_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, price, desc, cat, img_url, 1 if is_veg else 0, 1 if is_spicy else 0, 4.5, rest_id))

        conn.commit()
        cursor.execute("SELECT COUNT(*) FROM menu_item")
        print(f"Menu items after seeding: {cursor.fetchone()[0]}")

    # 4. Map MenuItems to Restaurants & categorize Veg/Non-Veg & Spicy & Images
    # Category -> Restaurant ID mapping
    cat_to_restaurant = {
        'biryani': 1,       # Paradise Biryani
        'andhra': 4,        # Rayalaseema Ruchulu
        'tamilnadu': 2,     # Chutneys
        'kerala': 2,        # Chutneys
        'thali': 2,         # Chutneys
        'punjabi': 3,       # Dhaba 1986
        'rajasthani': 3,    # Dhaba 1986
        'maharashtrian': 3, # Dhaba 1986
        'pizza': 5,         # Little Italy
        'pasta': 5,         # Little Italy
        'european': 5,      # Little Italy
        'chinese': 6,       # Mainland China
        'thai': 6,          # Mainland China
        'burger': 7,        # The Burger Club
        'fries': 7,         # The Burger Club
        'latinamerican': 7, # The Burger Club
        'african': 7,       # The Burger Club
        'sweets': 8,        # Mithai Mahal
        'dessert': 8,       # Mithai Mahal
        'snacks': 8,        # Mithai Mahal
        'drink': 8,         # Mithai Mahal
        'salad': 5          # Little Italy
    }

    # Food image fallback dictionary based on keywords
    image_dict = {
        "Margherita Pizza": "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?q=80&w=1000&auto=format&fit=crop",
        "Pepperoni Pizza": "https://images.unsplash.com/photo-1628840042765-356cda07504e?q=80&w=1000&auto=format&fit=crop",
        "BBQ Chicken Pizza": "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=1000&auto=format&fit=crop",
        "Veggie Delight Pizza": "https://images.unsplash.com/photo-1585238342024-78d387f4a707?q=80&w=1000&auto=format&fit=crop",
        "Veggie Burger": "https://images.unsplash.com/photo-1550547660-d9450f859349?q=80&w=1000&auto=format&fit=crop",
        "Cheese Burst Burger": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?q=80&w=1000&auto=format&fit=crop",
        "Crispy Chicken Burger": "/static/profile_pics/crispy_chicken_burger.jpg",
        "Smoky BBQ Burger": "/static/profile_pics/smoky_bbq_burger.jpg",
        "Pasta Alfredo": "https://images.unsplash.com/photo-1645112411341-6c4fd023714a?q=80&w=1000&auto=format&fit=crop",
        "Red Sauce Pasta": "/static/profile_pics/red_sauce_pasta.avif",
        "Pesto Pasta": "https://images.unsplash.com/photo-1473093295043-cdd812d0e601?q=80&w=1000&auto=format&fit=crop",
        "Four Cheese Pasta": "https://images.unsplash.com/photo-1551183053-bf91a1d81141?q=80&w=1000&auto=format&fit=crop",
        "Cold Coffee": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?q=80&w=1000&auto=format&fit=crop",
        "Lemon Iced Tea": "https://images.unsplash.com/photo-1556881286-fc6915169721?q=80&w=1000&auto=format&fit=crop",
        "Strawberry Milkshake": "https://images.unsplash.com/photo-1579954115545-a95591f28bfc?q=80&w=1000&auto=format&fit=crop",
        "Mojito": "https://images.unsplash.com/photo-1551538827-9c037cb4f32a?q=80&w=1000&auto=format&fit=crop",
        "Caesar Salad": "https://images.unsplash.com/photo-1550304943-4f24f54ddde9?q=80&w=1000&auto=format&fit=crop",
        "Greek Salad": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?q=80&w=1000&auto=format&fit=crop",
        "Garden Fresh Salad": "https://images.unsplash.com/photo-1540420773420-3366772f4999?q=80&w=1000&auto=format&fit=crop",
        "Protein Salad": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=1000&auto=format&fit=crop",
        "French Fries": "/static/profile_pics/french_fries.jpg",
        "Peri Peri Fries": "https://images.unsplash.com/photo-1590301157890-4810ed352733?q=80&w=1000&auto=format&fit=crop",
        "Garlic Bread": "/static/profile_pics/garlic_bread.jpg",
        "Chocolate Cake": "https://images.unsplash.com/photo-1578985545062-69928b1d9587?q=80&w=1000&auto=format&fit=crop",
        "Brownie with Ice Cream": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?q=80&w=1000&auto=format&fit=crop",
        "Donuts": "https://images.unsplash.com/photo-1551024601-bec78aea704b?q=80&w=1000&auto=format&fit=crop",
        "Fruit Bowl": "/static/profile_pics/fruit_bowl.jpg",
        "Hyderabadi Chicken Biryani": "https://images.pexels.com/photos/5410401/pexels-photo-5410401.jpeg?cs=srgb&dl=pexels-saveurs-secretes-5410401.jpg&fm=jpg",
        "Hyderabadi Mutton Biryani": "/static/profile_pics/special_biryani.jpg",
        "Lucknowi Dum Biryani": "/static/profile_pics/lucknowi_dum_biryani.jpg",
        "Kolkata Biryani": "/static/profile_pics/kolkata_biryani.jpg",
        "Paneer Biryani": "/static/profile_pics/paneer_biryani.jpg",
        "Veg Dum Biryani": "/static/profile_pics/Vegetable-Dum-Biryani.jpg",
        "Egg Biryani": "/static/profile_pics/Egg-Biryani.jpg",
        "North Indian Royal Thali": "/static/profile_pics/north_thali.webp",
        "South Indian Traditional Thali": "/static/profile_pics/south_thali.avif",
        "Gujarati Thali": "/static/profile_pics/gujarati_th.jpg",
        "Rajasthani Thali": "/static/profile_pics/rajasthani_th.jpg",
        "Maharashtrian Thali": "/static/profile_pics/marathi_th.jpg",
        "Punjabi Special Thali": "/static/profile_pics/punjabi-th.webp",
        "Gulab Jamun": "/static/profile_pics/gulab_jamun.webp",
        "Rasgulla": "/static/profile_pics/rasgulla.jpg",
        "Kaju Katli": "/static/profile_pics/kaju_burfi.webp",
        "Jalebi": "/static/profile_pics/jalebi.webp",
        "Rasmalai": "/static/profile_pics/rasamalai.webp",
        "Motichoor Laddu": "/static/profile_pics/MotichoorLaddu.webp",
        "Mysore Pak": "/static/profile_pics/MysorePak.webp",
        "Samosa": "/static/profile_pics/samosa.jpg",
        "Aloo Tikki Chaat": "/static/profile_pics/Chat.jpg",
        "Pani Puri": "/static/profile_pics/Pani-Puri.webp",
        "Dahi Puri": "/static/profile_pics/dahi-puri.jpg",
        "Pav Bhaji": "/static/profile_pics/pav_bhaji.webp",
        "Vada Pav": "/static/profile_pics/Vada-Pav.webp",
        "Masala Corn": "/static/profile_pics/MasalaCorn.jpg",
        "Bread Pakora": "/static/profile_pics/bread-pakoda.jpg",
        "Butter Chicken": "/static/profile_pics/butter-chicken.jpg",
        "Amritsari Kulcha": "/static/profile_pics/amritsari-kulcha.avif",
        "Sarson da Saag with Makki di Roti": "/static/profile_pics/sarson_ka_saag.webp",
        "Paneer Butter Masala": "/static/profile_pics/paneer-butter-masala.jpg",
        "Dal Makhani": "/static/profile_pics/dal-makhani.webp",
        "Chole Bhature": "/static/profile_pics/chole-bhature.png",
        "Tandoori Chicken": "/static/profile_pics/tandoori.jpg",
        "Paneer Tikka": "/static/profile_pics/paneer-tikka.jpg",
        "Chicken Tikka": "/static/profile_pics/chicken-tikka.jpg",
        "Sweet Lassi": "/static/profile_pics/lassi.webp",
        "Andhra Chicken Curry": "/static/profile_pics/Andhra-Chicken-Curry.jpg",
        "Gongura Mutton": "/static/profile_pics/gongura-mutton.jpg",
        "Andhra Fish Fry": "/static/profile_pics/andhra-fish-curry.jpg",
        "Kodi Vepudu": "/static/profile_pics/kodi-vepudu.jpg",
        "Andhra Prawn Curry": "/static/profile_pics/andhra-prawn-curry.jpg",
        "Royyala Iguru": "/static/profile_pics/royyala-iguru.webp",
        "Andhra Spicy Biryani": "/static/profile_pics/andhra-spicy-biryani.jpg",
        "Tomato Pappu": "/static/profile_pics/tomato-pappu.jpg",
        "Andhra Rasam": "/static/profile_pics/rasam.jpg",
        "Gutti Vankaya Curry": "/static/profile_pics/vankaya-curry.jpg",
        "Chettinad Chicken": "/static/profile_pics/Chicken-Chettinad.jpg",
        "Chicken Chettinad Biryani": "/static/profile_pics/chettinad-biryani.webp",
        "Karaikudi Mutton Curry": "/static/profile_pics/Tamil-style-mutton-biryani.webp",
        "Idli with Sambar": "/static/profile_pics/idli_sambar.jpg",
        "Dosa with Chutney": "/static/profile_pics/dosa.jpg",
        "Pongal": "/static/profile_pics/pongal.jpg",
        "Lemon Rice": "/static/profile_pics/lemon-rice.gif",
        "Tamarind Rice": "/static/profile_pics/tamarindrice.webp",
        "Medu Vada": "/static/profile_pics/medu-vada.webp",
        "Filter Coffee": "/static/profile_pics/coffee.webp",
        "Kerala Fish Curry": "/static/profile_pics/Kerala-Fish-Curry.jpg",
        "Malabar Chicken Biryani": "/static/profile_pics/malabar-chicken-biryani.jpg",
        "Appam with Vegetable Stew": "/static/profile_pics/appam.jpg",
        "Kerala Prawn Curry": "/static/profile_pics/Kerala-Prawn-Curry.jpg",
    }

    non_veg_keywords = ['chicken', 'mutton', 'fish', 'prawn', 'egg', 'beef', 'lamb', 'pork', 'bacon', 'pepperoni', 'meat', 'doro wat', 'laal maas', 'royyala', 'kodi', 'karaikudi', 'gongura mutton']
    spicy_keywords = ['spicy', 'chili', 'schezwan', 'peri peri', 'kolhapuri', 'chettinad', 'hot and sour', 'andhra', 'curry', 'vepudu', 'tikka', 'masala', 'tagine', 'gongura', 'manchurian']

    cursor.execute("SELECT id, name, category, image_url FROM menu_item")
    items = cursor.fetchall()

    for item in items:
        item_id = item['id']
        name = item['name']
        cat = item['category'].lower()
        current_img = item['image_url']

        # Determine veg/non-veg
        name_lower = name.lower()
        is_veg = not any(kw in name_lower for kw in non_veg_keywords)

        # Determine spice level
        is_spicy = any(kw in name_lower for kw in spicy_keywords) or cat in ['andhra', 'punjabi']

        # Determine restaurant (distributing between partner cities)
        pune_dish_map = {
            "Kolhapuri Chicken": 11,      # Maratha Samrat (Vishrantwadi, Pune)
            "Kolhapuri Mutton": 11,       # Maratha Samrat
            "Thalipeeth": 11,             # Maratha Samrat
            "Maharashtrian Thali": 11,    # Maratha Samrat
            "Misal Pav": 11,              # Maratha Samrat
            "Puran Poli": 11,             # Maratha Samrat
            "Lucknowi Dum Biryani": 9,    # Dighi Darbar (Dighi, near AIT Pune)
            "Kolkata Biryani": 9,         # Dighi Darbar
            "Paneer Tikka": 9,            # Dighi Darbar
            "Tandoori Chicken": 9,        # Dighi Darbar
            "Egg Biryani": 10,            # PK Biryani House (Vishrantwadi, Pune)
            "Veg Dum Biryani": 10,        # PK Biryani House
            "Paneer Biryani": 10,         # PK Biryani House
            "Pani Puri": 12,              # Irani Cafe (Viman Nagar, Pune)
            "Dahi Puri": 12,              # Irani Cafe
            "Pav Bhaji": 12,              # Irani Cafe
            "Vada Pav": 12,               # Irani Cafe
            "Bunny Chow": 12,             # Irani Cafe
            "Cheese Burst Burger": 13,    # The Burger Club Pune (Kalyani Nagar, Pune)
            "Crispy Chicken Burger": 13,  # The Burger Club Pune
            "Peri Peri Fries": 13,        # The Burger Club Pune
            "Dosa with Chutney": 14,      # Vaishali (FC Road, Pune)
            "Idli with Sambar": 14,       # Vaishali
            "Medu Vada": 14,              # Vaishali
            "Filter Coffee": 14,          # Vaishali
            "Pongal": 14                  # Vaishali
        }

        if name in pune_dish_map:
            rest_id = pune_dish_map[name]
        else:
            rest_id = cat_to_restaurant.get(cat, 1)

        # Determine image
        img = image_dict.get(name)
        if not img:
            if not current_img or current_img.strip() == '':
                # generic category based food photo
                img = f"https://images.unsplash.com/photo-1546069901-ba9599a7e63c?q=80&w=800&auto=format&fit=crop"
            else:
                img = current_img

        cursor.execute("""
        UPDATE menu_item SET
            image_url = ?,
            is_veg = ?,
            is_spicy = ?,
            restaurant_id = ?,
            rating = ?
        WHERE id = ?
        """, (img, 1 if is_veg else 0, 1 if is_spicy else 0, rest_id, 4.5, item_id))

    conn.commit()

    # 5. Connect orders with restaurants & ensure status_history entries exist
    cursor.execute('SELECT id, status, date_ordered, restaurant_id FROM "order"')
    orders = cursor.fetchall()

    for o in orders:
        order_id = o['id']
        order_status = o['status']
        order_date = o['date_ordered']
        current_rest = o['restaurant_id']

        # Find restaurant from order_items
        if not current_rest:
            cursor.execute("""
            SELECT mi.restaurant_id
            FROM order_item oi
            JOIN menu_item mi ON oi.menu_item_id = mi.id
            WHERE oi.order_id = ?
            LIMIT 1
            """, (order_id,))
            row = cursor.fetchone()
            rest_id = row[0] if row and row[0] else 1
            cursor.execute('UPDATE "order" SET restaurant_id = ? WHERE id = ?', (rest_id, order_id))

        # Check if history exists
        cursor.execute("SELECT COUNT(*) FROM order_status_history WHERE order_id = ?", (order_id,))
        if cursor.fetchone()[0] == 0:
            # Insert sequential history according to order status
            standard_statuses = ["Order Placed", "Order Confirmed", "Preparing Food", "Ready for Pickup", "Out for Delivery", "Delivered"]
            current_idx = 0
            # match status
            status_map = {
                'pending': 0,
                'order placed': 0,
                'preparing': 2,
                'preparing food': 2,
                'out for delivery': 4,
                'delivered': 5,
                'cancelled': -1
            }
            target_idx = status_map.get(order_status.lower(), 1)
            if target_idx == -1:
                cursor.execute("""
                INSERT INTO order_status_history (order_id, status, timestamp, note)
                VALUES (?, 'Order Placed', ?, 'Order registered in system')
                """, (order_id, order_date))
                cursor.execute("""
                INSERT INTO order_status_history (order_id, status, timestamp, note)
                VALUES (?, 'Cancelled', ?, 'Order cancelled by customer or restaurant')
                """, (order_id, order_date))
            else:
                for idx in range(target_idx + 1):
                    s_name = standard_statuses[idx]
                    cursor.execute("""
                    INSERT INTO order_status_history (order_id, status, timestamp, note)
                    VALUES (?, ?, ?, ?)
                    """, (order_id, s_name, order_date, f"Status updated to {s_name}"))

    conn.commit()

    # 6. Seed sample reviews for completed orders
    # Let's check existing reviews
    cursor.execute("SELECT COUNT(*) FROM restaurant_review")
    if cursor.fetchone()[0] == 0:
        sample_reviews = [
            (2, 1, 2, 5.0, "The Hyderabadi Dum Biryani was rich, aromatic, and cooked to perfection! Quick delivery too."),
            (3, 3, 5, 4.5, "Authentic Punjabi Butter Chicken and hot garlic naan. Loved the buttery texture."),
            (4, 4, 7, 5.0, "Super spicy Andhra style Kodi Vepudu! Real spice punch just how we like it in Hyderabad."),
            (2, 5, 3, 4.0, "Thin crust pizza arrived warm with lots of melted mozzarella. Fresh basil leaves on top.")
        ]
        for user_id, rest_id, order_id, rating, comment in sample_reviews:
            try:
                cursor.execute("""
                INSERT INTO restaurant_review (user_id, restaurant_id, order_id, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, rest_id, order_id, rating, comment))
            except Exception as e:
                pass
        conn.commit()

    # Backfill any legacy reviews with NULL created_at
    cursor.execute("""
    UPDATE restaurant_review
    SET created_at = COALESCE(
        (SELECT date_ordered FROM "order" WHERE "order".id = restaurant_review.order_id),
        CURRENT_TIMESTAMP
    )
    WHERE created_at IS NULL
    """)
    conn.commit()

    # Update restaurant ratings based on reviews
    cursor.execute("SELECT id FROM restaurant")
    for r_row in cursor.fetchall():
        r_id = r_row['id']
        cursor.execute("SELECT AVG(rating), COUNT(*) FROM restaurant_review WHERE restaurant_id = ?", (r_id,))
        avg_r, cnt_r = cursor.fetchone()
        if cnt_r and cnt_r > 0:
            cursor.execute("UPDATE restaurant SET rating = ?, total_reviews = ? WHERE id = ?",
                           (round(avg_r, 1), cnt_r, r_id))
        else:
            # Default decent rating
            cursor.execute("UPDATE restaurant SET rating = 4.6, total_reviews = 15 WHERE id = ?", (r_id,))
    conn.commit()

    conn.close()
    print("Database migration and seeding completed successfully!")

if __name__ == '__main__':
    migrate_and_seed()
