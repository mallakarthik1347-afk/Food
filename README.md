# 🍽️ Foodmato — Smart AI-Powered Food Delivery Platform

Foodmato is an AI-powered food delivery web application built using **Flask, SQLite, SQLAlchemy, Bootstrap, Leaflet OpenStreetMap, and Google Gemini 2.0 Flash**.

It allows users to explore restaurants, browse food menus, order food online, discover nearby restaurants, track orders, and get AI-powered food recommendations.

---

## 🌟 Key Features

### 1. 🔍 Smart Food Filters & Dynamic Menu

- **Multi-parameter filtering:** Filter by category, vegetarian, non-vegetarian, and spicy food.
- **Price range selector:** Filter dishes by minimum and maximum price.
- **Dynamic sorting:** Sort by recommended, price (low to high), price (high to low), customer rating, and alphabetical order.
- **Search functionality:** Search food items by title, description, and cuisine.
- **Database-backed filtering:** Uses SQLAlchemy queries to retrieve menu items.

### 2. ⭐ Restaurant Ratings & Verified Reviews

- 1–5 star restaurant ratings with customer reviews.
- Reviews are available only after a customer receives a completed order.
- Prevents duplicate reviews for the same order.
- Automatically calculates average restaurant ratings and review counts.
- Dedicated reviews page to display customer experiences.

### 3. 📍 GPS-Based Nearby Restaurants & Live Map

- **Find Restaurants Near Me:** Uses the browser Geolocation API.
- **Haversine distance calculation:** Calculates the geographical distance between the user and restaurants.
- **Proximity filters:** Find restaurants within 2 km, 5 km, and 10 km.
- **Interactive map:** Uses Leaflet.js and OpenStreetMap.
- **Restaurant map markers:** Displays restaurant information, cuisine, ratings, and distance.
- **Google Maps navigation:** Provides directions to selected restaurants.

> Browser geolocation requires HTTPS or localhost.

### 4. 🤖 AI Food Assistant Chatbot

Powered by Google Gemini 2.0 Flash.

- **Database-grounded recommendations:** Uses actual food and restaurant information from the database.
- **Budget-based suggestions:** Recommends food within the user's budget.
- **Dietary recommendations:** Helps users find vegetarian, non-vegetarian, spicy, and highly rated food.
- **Location-aware recommendations:** Suggests nearby restaurants when GPS coordinates are available.
- **Order status queries:** Authenticated customers can ask about their current order status.
- **Clickable recommendations:** Provides links to food and restaurant detail pages.
- **Fallback responses:** Provides database-based responses when the Gemini API is unavailable or not configured.

### 5. 🚚 Live Order Tracking & Management

- Visual six-stage order progress timeline:
  1. Order Placed
  2. Order Confirmed
  3. Preparing Food
  4. Ready for Pickup
  5. Out for Delivery
  6. Delivered
- Visual indicators for completed, active, and upcoming stages.
- Automatic order status refresh every 10 seconds.
- Timestamped order status history.
- Customer ownership checks to protect order information.

### 6. 📊 Admin Dashboard & Restaurant Management

- Dashboard statistics for total revenue, orders, restaurants, menu items, and customers.
- Admin order management.
- Order status updates through dropdown controls.
- Restaurant and menu management.
- Community stories and recipes.

---

## 🏗️ High-Level Architecture

```text
                 CLIENT LAYER
       Browser | Bootstrap | Leaflet.js
                 Chatbot UI
                     |
                     | HTTP / JSON APIs
                     |
              FLASK APPLICATION
                     |
       +-------------+-------------+
       |             |             |
    routes.py   ai_assistant.py  forms.py
       |             |             |
       |          Gemini API       |
       |          Haversine        |
       |                           |
       +-------------+-------------+
                     |
               SQLAlchemy ORM
                     |
                SQLite DB
                     |
       +-------------+-------------+
       |             |             |
      User       Restaurant      MenuItem
       |             |             |
      Order      Reviews       Cart
       |
  OrderStatusHistory
```

---

## ⚙️ Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, Flask |
| Authentication | Flask-Login, Flask-Bcrypt |
| Forms & Validation | Flask-WTF, WTForms |
| Database | SQLite, SQLAlchemy |
| AI / LLM | Google Gemini 2.0 Flash |
| Maps | Leaflet.js, OpenStreetMap |
| Frontend | HTML5, CSS3, Bootstrap 4.6 |
| Icons | Font Awesome 6 |
| Templates | Jinja2 |
| Production Server | Gunicorn, Nginx |
| Deployment | AWS EC2 |

---

## 🚀 Local Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/mallakarthik1347-afk/Food.git
cd Food
```

### 2. Create a Virtual Environment

**Windows:**

```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root directory.

```env
SECRET_KEY=your-super-secret-key
DATABASE_URL=sqlite:///site.db
GEMINI_API_KEY=your_gemini_api_key
FLASK_DEBUG=True
PORT=5000
```

To obtain a Gemini API key, visit [Google AI Studio](https://aistudio.google.com/).

The chatbot can also use its database-based fallback responses when no Gemini API key is configured.

**Important:** Never upload your actual `.env` file or API keys to GitHub.

### 5. Initialize the Database and Seed Sample Data

```bash
python foodMenuWebsite/seed_data.py
```

### 6. Run the Application

```bash
python run.py
```

Open the application in your browser:

```text
http://127.0.0.1:5000
```

---

## 🔑 Default User Accounts

The following accounts are referenced by the project documentation. Their passwords are not specified here.

| Role | Email | Permissions |
|---|---|---|
| Admin / Owner | foodmato@gmail.com | Admin dashboard, order management |
| Customer | hemanthvarma@gmail.com | Cart, orders, tracking, reviews |

You can also register a new account through the `/register` page.

---

## ☁️ AWS EC2 Deployment Guide

### Step 1: Launch an EC2 Instance

Launch an Ubuntu EC2 instance.

Suggested configuration:

- Operating System: Ubuntu
- Instance Type: t2.micro or t3.small
- Security Group:
  - Port 22 — SSH
  - Port 80 — HTTP
  - Port 443 — HTTPS

### Step 2: Connect to EC2 and Install Packages

Connect using SSH:

```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

Update the system:

```bash
sudo apt update
sudo apt upgrade -y
```

Install required packages:

```bash
sudo apt install -y python3 python3-pip python3-venv nginx git
```

### Step 3: Clone the Repository

```bash
cd /var/www

sudo git clone https://github.com/mallakarthik1347-afk/Food.git foodmato

sudo chown -R ubuntu:ubuntu /var/www/foodmato

cd /var/www/foodmato
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv

source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create the production `.env` file:

```bash
nano .env
```

Add your production configuration:

```env
SECRET_KEY=your-production-secret-key
DATABASE_URL=sqlite:///instance/site.db
GEMINI_API_KEY=your_actual_gemini_api_key
FLASK_DEBUG=False
PORT=5000
```

Save the file and exit.

### Step 5: Initialize the Database

```bash
python3 foodMenuWebsite/seed_data.py
```

### Step 6: Configure Gunicorn Using Systemd

Create a service file:

```bash
sudo nano /etc/systemd/system/foodmato.service
```

Add:

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

### Step 7: Configure Nginx

Open the Nginx configuration:

```bash
sudo nano /etc/nginx/sites-available/default
```

Configure the server block:

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

Test the Nginx configuration:

```bash
sudo nginx -t
```

Restart Nginx:

```bash
sudo systemctl restart nginx
```

Access the application using:

```text
http://YOUR_EC2_PUBLIC_IP
```

---

## 🧪 Testing Verification Checklist

- [x] Smart food filters and dynamic sorting.
- [x] GPS-based nearby restaurant discovery.
- [x] Haversine distance calculation.
- [x] Interactive restaurant maps.
- [x] Restaurant ratings and verified reviews.
- [x] Live order tracking with status history.
- [x] AI chatbot with food recommendations.
- [x] Admin dashboard and order management.
- [x] Password hashing and authentication.
- [x] Customer order ownership checks.

---

## 👨‍💻 Author & License

- **Project:** Foodmato — Smart AI-Powered Food Delivery Platform
- **GitHub Repository:** [Foodmato](https://github.com/mallakarthik1347-afk/Food)
- **License:** MIT License

