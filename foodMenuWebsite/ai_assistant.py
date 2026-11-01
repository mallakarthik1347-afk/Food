import os
import math
import re
from datetime import datetime
from flask import current_app
from foodMenuWebsite.models import Restaurant, MenuItem, Order

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points in kilometers."""
    try:
        R = 6371.0  # Earth radius in kilometers
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = (math.sin(dlat / 2) ** 2 +
             math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) *
             math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)
    except Exception:
        return 999.0

def build_knowledge_context(user_message, user_id=None, user_lat=None, user_lng=None):
    """
    Extracts relevant factual data from SQLite database to ground the Gemini prompt.
    Prevents hallucination by only supplying actual entities and facts.
    """
    msg = user_message.lower()
    context_lines = []

    # 1. Nearby restaurants if user coordinates available
    all_restaurants = Restaurant.query.filter_by(is_active=True).all()
    if user_lat is not None and user_lng is not None:
        try:
            u_lat = float(user_lat)
            u_lng = float(user_lng)
            rest_with_dist = []
            for r in all_restaurants:
                if r.latitude and r.longitude:
                    dist = haversine_distance(u_lat, u_lng, r.latitude, r.longitude)
                    rest_with_dist.append((dist, r))
            rest_with_dist.sort(key=lambda x: x[0])
            context_lines.append("--- NEARBY RESTAURANTS (Sorted by distance from user) ---")
            for dist, r in rest_with_dist[:5]:
                context_lines.append(f"• Restaurant: {r.name} (ID: {r.id}) | Cuisine: {r.cuisine_type} | Rating: {r.rating}⭐ ({r.total_reviews} reviews) | Distance: {dist} km | Address: {r.address}")
        except Exception:
            pass

    # If user asks about restaurants generally or best rated
    context_lines.append("--- ALL TOP RESTAURANTS IN OUR PLATFORM ---")
    for r in sorted(all_restaurants, key=lambda x: x.rating, reverse=True)[:6]:
        context_lines.append(f"• {r.name} (ID: {r.id}) - {r.cuisine_type} - {r.rating}⭐ - {r.address}")

    # 2. Food query matching (budget, veg, non-veg, spicy, category, dishes)
    # Check for budget / price numbers
    price_match = re.search(r'(?:under|below|less than|within|budget of)?\s*(?:rs\.?|₹|\$)?\s*(\d+(?:\.\d+)?)', msg)
    max_price = None
    if price_match and any(w in msg for w in ['under', 'below', 'less than', 'budget', 'cheap', 'affordable', '₹', '$']):
        try:
            max_price = float(price_match.group(1))
        except ValueError:
            pass

    food_query = MenuItem.query
    if max_price:
        food_query = food_query.filter(MenuItem.price <= max_price)
    if 'veg' in msg and 'non-veg' not in msg and 'non veg' not in msg:
        food_query = food_query.filter(MenuItem.is_veg == True)
    elif 'non-veg' in msg or 'non veg' in msg or 'chicken' in msg or 'mutton' in msg or 'fish' in msg:
        food_query = food_query.filter(MenuItem.is_veg == False)
    if 'spicy' in msg or 'hot' in msg:
        food_query = food_query.filter(MenuItem.is_spicy == True)

    matching_items = food_query.limit(20).all()
    if matching_items:
        context_lines.append(f"--- MATCHING FOOD ITEMS IN DATABASE ({len(matching_items)} items) ---")
        for item in matching_items:
            veg_str = "Veg" if item.is_veg else "Non-Veg"
            spice_str = "Spicy" if item.is_spicy else "Mild"
            rest_name = item.restaurant.name if item.restaurant else "Foodmato Kitchen"
            context_lines.append(f"• Dish: '{item.name}' (ID: {item.id}) | Category: {item.category} | Price: ${item.price:.2f} (approx ₹{int(item.price * 83)}) | {veg_str} | {spice_str} | Rating: {item.rating}⭐ | Restaurant: {rest_name} (ID: {item.restaurant_id})")

    # 3. User's recent orders if authenticated
    if user_id:
        user_orders = Order.query.filter_by(user_id=user_id).order_by(Order.date_ordered.desc()).limit(5).all()
        if user_orders:
            context_lines.append(f"--- USER'S RECENT ORDERS ---")
            for o in user_orders:
                item_names = ", ".join([f"{it.menu_item.name} (x{it.quantity})" for it in o.items if it.menu_item])
                dt_str = o.date_ordered.strftime('%Y-%m-%d %H:%M') if o.date_ordered else 'Recent'
                rest_name = o.restaurant.name if o.restaurant else 'Restaurant'
                context_lines.append(f"• Order #{o.id} | Date: {dt_str} | Status: {o.status} | Restaurant: {rest_name} | Total: ${o.total_price:.2f} | Items: [{item_names}]")
        else:
            context_lines.append("--- USER'S ORDERS: No orders placed yet. ---")

    return "\n".join(context_lines)

def generate_ai_response(user_message, user_id=None, user_lat=None, user_lng=None):
    """
    Communicates with Gemini via google.genai SDK using grounded context.
    Falls back gracefully if API key is not present or error occurs.
    """
    api_key = current_app.config.get('GEMINI_API_KEY') or os.environ.get('GEMINI_API_KEY', '')
    
    # Build factual database context
    context = build_knowledge_context(user_message, user_id, user_lat, user_lng)

    # If no Gemini API key is configured, provide an intelligent deterministic local response
    if not api_key:
        return generate_local_fallback(user_message, user_id, user_lat, user_lng)

    system_instruction = f"""You are 'Foodmato AI Assistant', a friendly, concise, and helpful food delivery assistant for the FoodDeliveryRestaurant platform.
Your job is to assist customers in exploring food, finding restaurants, suggesting dishes matching their budget or dietary preference (Veg / Non-Veg / Spicy), and checking their order status.

STRICT ACCURACY RULES:
1. ONLY recommend food items, restaurants, and prices that exist in the DATABASE CONTEXT below.
2. NEVER invent non-existent restaurants, items, or order numbers.
3. When recommending a food dish, include a clickable HTML link in this format: <a href="/food/{{id}}" class="badge badge-primary p-2 mr-1 mb-1">🍽️ {{name}} - ${{price}}</a>.
4. When recommending a restaurant, include a clickable HTML link in this format: <a href="/restaurant/{{id}}" class="badge badge-danger p-2 mr-1 mb-1">🏪 {{name}}</a>.
5. If the user asks for order status, refer to their real order data provided in the context and provide a link to track: <a href="/order/{{id}}/track" class="btn btn-sm btn-outline-success mt-1">Track Order #{{id}}</a>.
6. Keep answers clean, conversational, and format lists nicely with bullet points.

DATABASE CONTEXT:
{context}
"""

    try:
        # Try modern google.genai first
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"{system_instruction}\n\nUser Question: {user_message}"
        )
        if response and response.text:
            return response.text
    except Exception as e_genai:
        try:
            # Try legacy google.generativeai if installed
            import google.generativeai as legacy_genai
            legacy_genai.configure(api_key=api_key)
            model = legacy_genai.GenerativeModel('gemini-1.5-flash')
            res = model.generate_content(f"{system_instruction}\n\nUser Question: {user_message}")
            if res and res.text:
                return res.text
        except Exception as e_legacy:
            pass

    # If API call failed or timed out, use grounded deterministic fallback
    return generate_local_fallback(user_message, user_id, user_lat, user_lng)

def generate_local_fallback(msg, user_id=None, user_lat=None, user_lng=None):
    """High quality rule-based response using the live database when Gemini API is unavailable."""
    msg_low = msg.lower()

    # 1. Order status query
    if any(k in msg_low for k in ['order status', 'my order', 'track order', 'latest order', 'where is my food']):
        if not user_id:
            return "Please <a href='/login' class='text-primary font-weight-bold'>log in</a> to check your order status."
        order = Order.query.filter_by(user_id=user_id).order_by(Order.date_ordered.desc()).first()
        if order:
            items_str = ", ".join([f"{i.menu_item.name} (x{i.quantity})" for i in order.items if i.menu_item])
            return (f"Your latest <strong>Order #{order.id}</strong> is currently: "
                    f"<span class='badge badge-info'>{order.status}</span>.<br>"
                    f"Items: {items_str}<br>Total: ${order.total_price:.2f}<br>"
                    f"<a href='/order/{order.id}/track' class='btn btn-sm btn-outline-success mt-2'>"
                    f"🚀 Live Order Tracking</a>")
        else:
            return "You haven't placed any orders yet. Check out our <a href='/menu'>delicious menu</a>!"

    # 2. Nearby query
    if any(k in msg_low for k in ['near me', 'nearby', 'closest', 'around me', 'location']):
        if user_lat and user_lng:
            rests = Restaurant.query.filter_by(is_active=True).all()
            with_dist = []
            for r in rests:
                d = haversine_distance(float(user_lat), float(user_lng), r.latitude, r.longitude)
                with_dist.append((d, r))
            with_dist.sort(key=lambda x: x[0])
            out = "Here are the closest restaurants near your location:<br><ul class='pl-3 mt-2'>"
            for d, r in with_dist[:4]:
                out += f"<li><a href='/restaurant/{r.id}'><strong>{r.name}</strong></a> — {d:.1f} km away ({r.cuisine_type}, ⭐ {r.rating})</li>"
            out += "</ul><a href='/restaurants' class='btn btn-sm btn-primary mt-1'>View Nearby Map</a>"
            return out
        else:
            return ("To find restaurants near you, please grant location access when prompted by your browser, "
                    "or browse all our <a href='/restaurants'>restaurant listings with GPS map</a>.")

    # 3. Best rated / top restaurants
    if any(k in msg_low for k in ['best', 'top', 'highest rated', 'popular restaurant']):
        top_rests = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.rating.desc()).limit(3).all()
        out = "Here are our top-rated restaurants:<br><ul class='pl-3 mt-2'>"
        for r in top_rests:
            out += f"<li><a href='/restaurant/{r.id}'><strong>{r.name}</strong></a> ⭐ {r.rating} ({r.total_reviews} reviews) — {r.cuisine_type}</li>"
        out += "</ul>"
        return out

    # 4. Spicy food recommendation
    if 'spicy' in msg_low:
        spicy_items = MenuItem.query.filter_by(is_spicy=True).limit(4).all()
        out = "Craving something with a kick? Here are our top spicy favorites:<br><ul class='pl-3 mt-2'>"
        for item in spicy_items:
            out += f"<li><a href='/food/{item.id}'><strong>{item.name}</strong></a> - ${item.price:.2f} ({'Veg' if item.is_veg else 'Non-Veg'})</li>"
        out += "</ul>"
        return out

    # 5. Vegetarian food recommendation
    if 'veg' in msg_low and 'non-veg' not in msg_low and 'non veg' not in msg_low:
        veg_items = MenuItem.query.filter_by(is_veg=True).limit(4).all()
        out = "Here are popular 100% vegetarian dishes:<br><ul class='pl-3 mt-2'>"
        for item in veg_items:
            out += f"<li><a href='/food/{item.id}'><strong>{item.name}</strong></a> - ${item.price:.2f} ({item.category.capitalize()})</li>"
        out += "</ul>"
        return out

    # 6. Non-Veg food recommendation
    if 'non-veg' in msg_low or 'non veg' in msg_low or 'chicken' in msg_low or 'mutton' in msg_low:
        non_veg_items = MenuItem.query.filter_by(is_veg=False).limit(4).all()
        out = "Here are our signature non-vegetarian dishes:<br><ul class='pl-3 mt-2'>"
        for item in non_veg_items:
            out += f"<li><a href='/food/{item.id}'><strong>{item.name}</strong></a> - ${item.price:.2f}</li>"
        out += "</ul>"
        return out

    # 7. Budget food query
    price_match = re.search(r'\d+', msg_low)
    if price_match and any(w in msg_low for w in ['under', 'below', 'budget', 'cheap']):
        val = float(price_match.group(0))
        # if in rupees (e.g. 150), convert to dollars (e.g. ~ $2 - $15)
        dollar_limit = val if val < 50 else round(val / 83.0, 2)
        budget_items = MenuItem.query.filter(MenuItem.price <= dollar_limit).limit(4).all()
        if budget_items:
            out = f"Here are delicious items within your budget (${dollar_limit:.2f}):<br><ul class='pl-3 mt-2'>"
            for item in budget_items:
                out += f"<li><a href='/food/{item.id}'><strong>{item.name}</strong></a> - ${item.price:.2f}</li>"
            out += "</ul>"
            return out

    # General greeting / fallback
    return ("Hello! I'm your Foodmato AI Assistant. I can help you with:<br>"
            "• <strong>Find restaurants near me</strong> (using your live GPS)<br>"
            "• <strong>Recommend food under $10 (or ₹200)</strong><br>"
            "• <strong>Suggest spicy vegetarian or non-veg dishes</strong><br>"
            "• <strong>Check your latest order status</strong><br>"
            "What would you like to enjoy today?")
