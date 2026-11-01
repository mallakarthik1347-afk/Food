# 🍽️ Foodmato — Smart AI-Powered Food Delivery Platform

Foodmato is a full-featured, production-ready, AI-powered food delivery web application built with **Flask, SQLite, SQLAlchemy, Bootstrap, Leaflet OpenStreetMap, and Google Gemini 2.0 Flash**.

---

## 🌟 Key Highlights & Major Features

### 1. 🔍 Smart Food Filters & Dynamic Menu
- **Multi-parameter filtering**: Filter simultaneously by Category, Pure Vegetarian (🟢), Non-Vegetarian (🔴), and Spicy level (🌶️).
- **Price Range selector**: Filter by minimum and maximum budget prices.
- **Dynamic Sorting**: Sort dishes by Recommended, Price (Low to High), Price (High to Low), Customer Rating, and Alphabetical (A-Z).
- **Search bar**: Instant keyword matching across food titles, descriptions, and cuisines.
- **Database-Backed**: Fast server-side SQLAlchemy queries with clean reset capability.

### 2. ⭐ Restaurant Ratings & Verified Reviews
- **1 to 5 Star ratings** with detailed customer reviews.
- **Verified Order Guarantee**: Reviews are strictly unlocked only after a customer receives a completed/delivered order from that restaurant.
- **Anti-Duplication**: Prevents duplicate review submissions on the same order.
- **Automatic Rating Calculation**: Real-time average restaurant rating and total review counts computed on database commit.
- **Dedicated Public Reviews Hub**: Displays authentic customer experiences across all partner restaurants.

### 3. 📍 GPS-Based Nearby Restaurants & Live Map
- **"Find Restaurants Near Me" button**: Integrates browser Geolocation API (`navigator.geolocation`).
- **Real Mathematical Proximity**: Implements the **Haversine Great-Circle Distance formula** to calculate exact distance in kilometers between user coordinates and restaurant pins.
- **Proximity Range Filters**: Filter dining options within **2 km**, **5 km**, and **10 km** radii.
- **Interactive Leaflet.js & OpenStreetMap**: Custom map pins, interactive popups with restaurant cuisine, rating, and distance.
- **Google Maps Navigation**: One-click turn-by-turn directions link to restaurant coordinates.

### 4. 🤖 AI Food Assistant Chatbot (Google Gemini Powered)
- **Grounded in Database Truth**: Queries the real SQLite database before building the Gemini context prompt, ensuring zero hallucinations.
- **Budget-conscious Recommendations**: e.g., *"Suggest food under $10 or ₹200"* recommends real dishes within budget.
- **Dietary & Flavor Inquiries**: Recommends pure veg, spicy specials, and top-rated restaurants.
- **Location-Aware Answers**: When GPS coordinates are provided, recommends nearest restaurants with exact distances.
- **Live Order Status Queries**: Authenticated customers can ask *"What is my order status?"* to receive real-time order tracking links.
- **Clickable Cards & Badges**: Returns clickable links to food and restaurant detail pages.
- **Graceful Deterministic Fallback**: Provides database-grounded responses even if the external Gemini API is offline or unconfigured.

### 5. 🚚 Live Order Tracking & Management
- **Visual 6-Stage Progress Timeline**:
  1. *Order Placed*
  2. *Order Confirmed*
  3. *Preparing Food*
  4. *Ready for Pickup*
  5. *Out for Delivery*
  6. *Delivered*
- **Pulsing Animation**: Visual cues highlighting active stage vs. completed vs. upcoming stages.
- **Real-Time Polling**: Automatic client-side status refresh every 10 seconds via `/api/order/<id>/status`.
- **Timestamped Audit History**: Every status transition records an exact UTC timestamp and note in `OrderStatusHistory`.
- **Ownership Security**: Strict authorization ensuring customers only access their own order tracking and records.

### 6. 📊 Admin Dashboard & Restaurant Management
- **Executive KPI Metrics**: Live statistics on Total Revenue, Total Orders, Active Restaurants, Menu Items, and Registered Customers.
- **Order Control Panel**: Authorized administrators can update order statuses through dropdowns with instant timeline propagation.
- **Community Stories**: User-published culinary stories and recipes.

---

## 🏗️ High-Level Architecture

```
┌────────────────────────────────────────────────────────┐
│                   Client Layer                         │
│  Browser • Bootstrap 4.6 • Leaflet.js • Chatbot UI    │
└───────────────────────────┬────────────────────────────┘
                            │ HTTP / JSON REST APIs
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Flask Application                      │
│────────────────────────────────────────────────────────│
│  • routes.py (Controller & API endpoints)              │
│  • ai_assistant.py (Gemini Engine & Haversine Math)    │
│  • forms.py (WTForms Validation)                       │
│  • config.py (Environment Variables)                   │
└─────────────┬──────────────────────────┬───────────────┘
              │                          │
              ▼                          ▼
┌───────────────────────────┐  ┌─────────────────────────┐
│     SQLAlchemy ORM        │  │    Google Gemini API    │
│───────────────────────────│  │─────────────────────────│
│ • User & Roles            │  │ • gemini-2.0-flash      │
│ • Restaurant (lat/long)   │  │ • Zero hallucination   │
│ • MenuItem (veg/spicy)    │  │ • Grounded DB Context   │
│ • Order & OrderItem       │  └─────────────────────────┘
│ • OrderStatusHistory      │
│ • RestaurantReview        │
│ • Cart                    │
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│      SQLite Database      │
│     (instance/site.db)    │
└───────────────────────────┘
```

---

## ⚙️ Tech Stack

- **Backend**: Python 3.10+, Flask 3.1, Flask-Login, Flask-Bcrypt, Flask-WTF
- **Database**: SQLite, SQLAlchemy ORM
- **AI / LLM**: Google Gemini 2.0 Flash (`google-genai` / `google-generativeai`)
- **Maps**: Leaflet.js, OpenStreetMap
- **Frontend**: HTML5, CSS3, Bootstrap 4.6, Font Awesome 6, Jinja2
- **Production Server**: Gunicorn, Nginx (for AWS EC2)

---

## 🚀 Local Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/Hemanth880225/FoodDeliveryRestaurant.git
cd FoodDeliveryRestaurant
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the project root:
```env
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=sqlite:///site.db
GEMINI_API_KEY=your_gemini_api_key_here
FLASK_DEBUG=True
PORT=5000
```
> **Note**: To obtain a free Gemini API key, visit [Google AI Studio](https://aistudio.google.com/). If no API key is provided, the chatbot seamlessly operates in high-quality deterministic fallback mode with real database data.

### 5. Initialize Database & Seed Sample Data
```bash
python foodMenuWebsite/seed_data.py
```

### 6. Run the Application
```bash
python run.py
```
Open your browser at: **`http://127.0.0.1:5000`**

---

## 🔑 Default User Accounts

| Role | Email | Password | Permissions |
|------|-------|----------|-------------|
| **Admin / Owner** | `foodmato@gmail.com` | *Registered in DB* | Admin dashboard, all orders, update status |
| **Customer** | `hemanthvarma@gmail.com` | *Registered in DB* | Order, cart, tracking, write verified reviews |

*(You can also sign up a new account anytime via `/register`)*

---

## 🌐 AWS EC2 Deployment Guide

### Step 1: Launch an Ubuntu 22.04 / 24.04 EC2 Instance
- Instance type: `t2.micro` or `t3.small` (Free tier eligible)
- Security Group: Allow Inbound traffic on **Port 80 (HTTP)**, **Port 443 (HTTPS)**, and **Port 22 (SSH)**.

### Step 2: Connect & Install System Packages
```bash
ssh -i your-key.pem ubuntu@<your-ec2-public-ip>

sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx git
```

### Step 3: Clone Code & Configure Environment
```bash
cd /var/www
sudo git clone https://github.com/Hemanth880225/FoodDeliveryRestaurant.git foodmato
sudo chown -R ubuntu:ubuntu /var/www/foodmato
cd /var/www/foodmato

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create production .env
nano .env
```
Add:
```env
SECRET_KEY=production-secure-random-key-12345
DATABASE_URL=sqlite:///instance/site.db
GEMINI_API_KEY=your_actual_gemini_key
FLASK_DEBUG=False
PORT=5000
```

### Step 4: Seed Database
```bash
python3 foodMenuWebsite/seed_data.py
```

### Step 5: Configure Systemd Service
Create `/etc/systemd/system/foodmato.service`:
```bash
sudo nano /etc/systemd/system/foodmato.service
```
Insert:
```ini
[Unit]
Description=Foodmato Gunicorn Application Server
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/foodmato
Environment="PATH=/var/www/foodmato/.venv/bin"
ExecStart=/var/www/foodmato/.venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 run:app

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl start foodmato
sudo systemctl enable foodmato
sudo systemctl status foodmato
```

### Step 6: Configure Nginx as Reverse Proxy
Edit `/etc/nginx/sites-available/default`:
```bash
sudo nano /etc/nginx/sites-available/default
```
Replace the `server` block:
```nginx
server {
    listen 80;
    server_name _;

    client_max_body_size 16M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/foodmato/foodMenuWebsite/static;
        expires 30d;
    }
}
```
Test and restart Nginx:
```bash
sudo nginx -t
sudo systemctl restart nginx
```

Access your platform live at `http://<YOUR-EC2-PUBLIC-IP>`!

---

## 🧪 Testing Verification Checklist

- [x] **Smart Filters**: Multi-select veg, non-veg, category, and price range filters return instant database results.
- [x] **GPS & Maps**: "Find Restaurants Near Me" computes Haversine distance and pins restaurants on Leaflet map.
- [x] **Verified Reviews**: 1-5 star review form unlocks only after placing and completing an order.
- [x] **Live Order Tracking**: Visual 6-stage timeline auto-refreshes every 10 seconds with SQLite timestamp history.
- [x] **Gemini Chatbot**: Answers budget and dietary questions with clickable food links, zero hallucinations.
- [x] **Security**: Bcrypt password hashing, session ownership checks, server-side WTForms validation.

---

## 👨‍💻 Author & License
- Project Author: **Hemanth**
- License: **MIT License**
