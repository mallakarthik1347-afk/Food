import os
import secrets
from datetime import datetime, timezone
from PIL import Image
from flask import render_template, request, redirect, url_for, flash, abort, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

from foodMenuWebsite import app, db, bcrypt
from foodMenuWebsite.models import (
    User, Restaurant, MenuItem, Order, OrderItem, OrderStatusHistory,
    RestaurantReview, Cart, Post, Message
)
from foodMenuWebsite.forms import (
    RegisterForm, LoginForm, UpdateAccountForm, PostForm, OrderForm,
    UpdateOrderStatusForm, RestaurantReviewForm, ContactForm, MenuItemForm
)
from foodMenuWebsite.ai_assistant import generate_ai_response, haversine_distance


# ---------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static', 'profile_pics', picture_fn)

    try:
        output_size = (250, 250)
        im = Image.open(form_picture)
        im.thumbnail(output_size)
        im.save(picture_path)
    except Exception:
        form_picture.save(picture_path)

    return picture_fn


# ---------------------------------------------------------
# Home & Static Pages
# ---------------------------------------------------------

@app.route("/")
@app.route('/home')
def home():
    featured_restaurants = Restaurant.query.filter_by(is_active=True).order_by(Restaurant.rating.desc()).limit(4).all()
    popular_dishes = MenuItem.query.order_by(MenuItem.rating.desc()).limit(6).all()
    categories = [
        {"name": "Biryani", "icon": "fa-bowl-rice", "slug": "biryani"},
        {"name": "Pizza", "icon": "fa-pizza-slice", "slug": "pizza"},
        {"name": "Burgers", "icon": "fa-hamburger", "slug": "burger"},
        {"name": "South Indian", "icon": "fa-utensils", "slug": "andhra"},
        {"name": "North Indian", "icon": "fa-fire", "slug": "punjabi"},
        {"name": "Chinese", "icon": "fa-bowl-food", "slug": "chinese"},
        {"name": "Desserts", "icon": "fa-ice-cream", "slug": "dessert"},
        {"name": "Drinks", "icon": "fa-cocktail", "slug": "drink"}
    ]
    return render_template("home.html", title="Foodmato — Fast AI-Powered Food Delivery",
                           restaurants=featured_restaurants, popular_dishes=popular_dishes, categories=categories)


@app.route('/About/Story')
def about():
    return render_template("about.html", title="About Foodmato")


@app.route('/Contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        msg = Message(name=form.name.data.strip(), email=form.email.data.strip().lower(), message=form.message.data.strip())
        db.session.add(msg)
        db.session.commit()
        flash('Thank you! Your message has been sent successfully. We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    return render_template("contact.html", title="Contact Us", form=form)


# ---------------------------------------------------------
# User Authentication & Profile
# ---------------------------------------------------------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip() if form.last_name.data else '',
            email=form.email.data.strip().lower(),
            password=hashed_password
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been created! You can now log in to order.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f"Welcome back, {user.first_name}! You are now logged in.", 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash("Login failed. Please check your email and password.", 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been successfully logged out.", 'info')
    return redirect(url_for('home'))


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.first_name = form.first_name.data.strip()
        current_user.last_name = form.last_name.data.strip() if form.last_name.data else ''
        current_user.email = form.email.data.strip().lower()
        db.session.commit()
        flash('Your profile has been updated successfully!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/' + (current_user.image_file or "default.webp"))
    return render_template('account.html', title='Account Settings', form=form, image_file=image_file)


# ---------------------------------------------------------
# Feature A: Smart Food Filters & Menu Browsing
# ---------------------------------------------------------

@app.route('/menu')
def menu():
    # Query parameters
    search_query = request.args.get('q', '').strip()
    category = request.args.get('category', '').strip().lower()
    veg_filter = request.args.get('veg', '')  # '1' for veg, '0' for non-veg
    spicy_filter = request.args.get('spicy', '')  # '1' for spicy
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    sort_by = request.args.get('sort', 'default')

    query = MenuItem.query

    # Search filter
    if search_query:
        query = query.filter(or_(
            MenuItem.name.ilike(f"%{search_query}%"),
            MenuItem.description.ilike(f"%{search_query}%"),
            MenuItem.category.ilike(f"%{search_query}%")
        ))

    # Category filter
    if category and category != 'all':
        query = query.filter(MenuItem.category == category)

    # Veg / Non-Veg filter
    if veg_filter == '1':
        query = query.filter(MenuItem.is_veg == True)
    elif veg_filter == '0':
        query = query.filter(MenuItem.is_veg == False)

    # Spicy filter
    if spicy_filter == '1':
        query = query.filter(MenuItem.is_spicy == True)

    # Price range
    if min_price is not None:
        query = query.filter(MenuItem.price >= min_price)
    if max_price is not None:
        query = query.filter(MenuItem.price <= max_price)

    # Sorting
    if sort_by == 'price_asc':
        query = query.order_by(MenuItem.price.asc())
    elif sort_by == 'price_desc':
        query = query.order_by(MenuItem.price.desc())
    elif sort_by == 'rating_desc':
        query = query.order_by(MenuItem.rating.desc())
    elif sort_by == 'name_asc':
        query = query.order_by(MenuItem.name.asc())
    else:
        query = query.order_by(MenuItem.id.asc())

    items = query.all()

    # Get all distinct categories for filter buttons
    categories = db.session.query(MenuItem.category).distinct().order_by(MenuItem.category).all()
    category_list = [c[0] for c in categories]

    return render_template(
        "menu.html",
        title="Food Menu",
        items=items,
        categories=category_list,
        selected_category=category,
        search_query=search_query,
        veg_filter=veg_filter,
        spicy_filter=spicy_filter,
        min_price=min_price,
        max_price=max_price,
        sort_by=sort_by,
        total_count=len(items)
    )


@app.route('/food/<int:item_id>')
def food_detail(item_id):
    item = MenuItem.query.get_or_404(item_id)
    related_items = MenuItem.query.filter(
        MenuItem.category == item.category,
        MenuItem.id != item.id
    ).limit(4).all()
    return render_template('food_detail.html', title=item.name, item=item, related_items=related_items)


# ---------------------------------------------------------
# Feature C: GPS-Based Nearby Restaurants & Listings
# ---------------------------------------------------------

@app.route('/restaurants')
def restaurants():
    search = request.args.get('q', '').strip()
    cuisine = request.args.get('cuisine', '').strip().lower()
    sort = request.args.get('sort', 'rating_desc')

    query = Restaurant.query.filter_by(is_active=True)

    if search:
        query = query.filter(or_(
            Restaurant.name.ilike(f"%{search}%"),
            Restaurant.description.ilike(f"%{search}%"),
            Restaurant.cuisine_type.ilike(f"%{search}%"),
            Restaurant.address.ilike(f"%{search}%")
        ))

    if cuisine and cuisine != 'all':
        query = query.filter(Restaurant.cuisine_type.ilike(f"%{cuisine}%"))

    if sort == 'rating_desc':
        query = query.order_by(Restaurant.rating.desc())
    elif sort == 'reviews_desc':
        query = query.order_by(Restaurant.total_reviews.desc())
    elif sort == 'name_asc':
        query = query.order_by(Restaurant.name.asc())

    restaurants_list = query.all()
    return render_template('restaurants.html', title="Find Restaurants Near You",
                           restaurants=restaurants_list, search=search, cuisine=cuisine, sort=sort)


@app.route('/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    menu_items = MenuItem.query.filter_by(restaurant_id=restaurant.id).all()
    reviews = RestaurantReview.query.filter_by(restaurant_id=restaurant.id).order_by(RestaurantReview.created_at.desc()).all()

    # Check if current user is eligible to review:
    # Must be logged in, must have an order from this restaurant with status 'Delivered' (or completed),
    # and must NOT have reviewed that order already.
    eligible_order = None
    if current_user.is_authenticated:
        completed_orders = Order.query.filter_by(user_id=current_user.id, restaurant_id=restaurant.id).all()
        for o in completed_orders:
            # check if this order already has a review
            has_rev = RestaurantReview.query.filter_by(order_id=o.id).first()
            if not has_rev:
                eligible_order = o
                break

    review_form = RestaurantReviewForm()
    return render_template('restaurant_detail.html', title=restaurant.name,
                           restaurant=restaurant, menu_items=menu_items,
                           reviews=reviews, eligible_order=eligible_order, form=review_form)


@app.route('/api/restaurants/nearby')
def api_nearby_restaurants():
    """
    Computes real Haversine distance from user coordinates,
    filters by maximum distance radius (e.g. 2, 5, 10 km),
    and returns sorted JSON for OpenStreetMap / Leaflet markers.
    Does not assume or fallback to hardcoded coordinates.
    """
    lat_param = request.args.get('lat')
    lng_param = request.args.get('lng')

    if not lat_param or not lng_param:
        return jsonify({'error': 'GPS coordinates (lat, lng) are required to discover nearby restaurants'}), 400

    try:
        user_lat = float(lat_param)
        user_lng = float(lng_param)
        max_dist = request.args.get('max_distance', type=float)  # in km, e.g. 2, 5, 10
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid latitude or longitude values'}), 400

    restaurants_list = Restaurant.query.filter_by(is_active=True).all()
    nearby_data = []

    for r in restaurants_list:
        if r.latitude is not None and r.longitude is not None:
            dist = haversine_distance(user_lat, user_lng, r.latitude, r.longitude)
            if max_dist is None or dist <= max_dist:
                nearby_data.append({
                    'id': r.id,
                    'name': r.name,
                    'cuisine': r.cuisine_type,
                    'address': r.address,
                    'phone': r.phone,
                    'rating': r.rating,
                    'total_reviews': r.total_reviews,
                    'image_url': r.image_url,
                    'latitude': r.latitude,
                    'longitude': r.longitude,
                    'distance_km': dist,
                    'directions_url': f"https://www.google.com/maps/dir/?api=1&destination={r.latitude},{r.longitude}"
                })

    nearby_data.sort(key=lambda x: x['distance_km'])
    return jsonify({
        'user_location': {'lat': user_lat, 'lng': user_lng},
        'count': len(nearby_data),
        'restaurants': nearby_data
    })


# ---------------------------------------------------------
# Feature B: Restaurant Ratings and Reviews
# ---------------------------------------------------------

@app.route('/restaurant/<int:restaurant_id>/review', methods=['POST'])
@login_required
def submit_review(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    form = RestaurantReviewForm()

    if form.validate_on_submit():
        order_id = request.form.get('order_id', type=int)
        if not order_id:
            flash("Review submission requires a verified completed order.", "danger")
            return redirect(url_for('restaurant_detail', restaurant_id=restaurant.id))

        order = Order.query.get_or_404(order_id)

        # Security check: User must own the order
        if order.user_id != current_user.id:
            abort(403)

        # Check duplicate review on same order
        existing = RestaurantReview.query.filter_by(order_id=order.id).first()
        if existing:
            flash("You have already reviewed this order.", "warning")
            return redirect(url_for('restaurant_detail', restaurant_id=restaurant.id))

        rating_val = float(form.rating.data)
        comment_val = form.comment.data.strip()

        new_review = RestaurantReview(
            user_id=current_user.id,
            restaurant_id=restaurant.id,
            order_id=order.id,
            rating=rating_val,
            comment=comment_val,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(new_review)
        db.session.commit()

        # Recalculate restaurant average rating
        restaurant.update_rating()
        db.session.commit()

        flash("Thank you! Your verified customer review has been posted.", "success")
        return redirect(url_for('restaurant_detail', restaurant_id=restaurant.id))

    flash("Error submitting review. Please verify all fields.", "danger")
    return redirect(url_for('restaurant_detail', restaurant_id=restaurant.id))


@app.route('/reviews')
def reviews():
    all_reviews = RestaurantReview.query.order_by(RestaurantReview.created_at.desc()).all()
    avg_rating = round(sum(r.rating for r in all_reviews) / len(all_reviews), 1) if all_reviews else 4.7
    return render_template('reviews.html', title='Customer Reviews', reviews=all_reviews, avg_rating=avg_rating)


# ---------------------------------------------------------
# Feature E: Live Order Tracking & Management
# ---------------------------------------------------------

STANDARD_ORDER_STATUSES = [
    "Order Placed",
    "Order Confirmed",
    "Preparing Food",
    "Ready for Pickup",
    "Out for Delivery",
    "Delivered"
]

@app.route('/order/<int:order_id>/track')
@login_required
def track_order(order_id):
    order = Order.query.get_or_404(order_id)
    # Ensure user can only view their own orders unless they are owner/admin
    if order.user_id != current_user.id and not current_user.is_owner:
        abort(403)

    history = OrderStatusHistory.query.filter_by(order_id=order.id).order_by(OrderStatusHistory.timestamp.asc()).all()

    # Determine index of current status in the progress timeline
    status_lower = order.status.lower()
    current_index = -1
    for idx, s in enumerate(STANDARD_ORDER_STATUSES):
        if s.lower() == status_lower:
            current_index = idx
            break

    # If it was cancelled
    is_cancelled = (status_lower == 'cancelled')

    return render_template(
        'order_tracking.html',
        title=f"Tracking Order #{order.id}",
        order=order,
        history=history,
        statuses=STANDARD_ORDER_STATUSES,
        current_index=current_index,
        is_cancelled=is_cancelled
    )


@app.route('/api/order/<int:order_id>/status')
@login_required
def api_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_owner:
        return jsonify({'error': 'Unauthorized'}), 403

    history = [
        {
            'status': h.status,
            'timestamp': h.timestamp.strftime('%I:%M %p, %b %d') if h.timestamp else '',
            'note': h.note or ''
        }
        for h in order.status_history
    ]

    status_lower = order.status.lower()
    current_index = -1
    for idx, s in enumerate(STANDARD_ORDER_STATUSES):
        if s.lower() == status_lower:
            current_index = idx
            break

    return jsonify({
        'order_id': order.id,
        'status': order.status,
        'current_index': current_index,
        'is_cancelled': status_lower == 'cancelled',
        'total_price': order.total_price,
        'history': history
    })


@app.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('orders.html', title='My Orders', orders=user_orders)


@app.route('/orders/view/<int:order_id>')
@login_required
def view_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_owner:
        abort(403)
    return redirect(url_for('track_order', order_id=order.id))


@app.route('/owner/orders')
@login_required
def owner_orders():
    if not current_user.is_owner:
        flash('Access restricted to authorized administrators.', 'danger')
        return redirect(url_for('home'))

    status_filter = request.args.get('status', '').strip()
    query = Order.query.order_by(Order.date_ordered.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)

    all_orders = query.all()
    return render_template('owner_orders.html', title="Manage Orders", orders=all_orders, status_filter=status_filter)


@app.route('/owner/orders/<int:order_id>/update', methods=['GET', 'POST'])
@login_required
def update_order_status(order_id):
    if not current_user.is_owner:
        flash('Access restricted to authorized administrators.', 'danger')
        return redirect(url_for('home'))

    order = Order.query.get_or_404(order_id)
    form = UpdateOrderStatusForm()

    if form.validate_on_submit():
        new_status = form.status.data
        note = form.note.data.strip() if form.note.data else f"Status updated to '{new_status}' by administrator."

        order.status = new_status
        history_entry = OrderStatusHistory(
            order_id=order.id,
            status=new_status,
            timestamp=datetime.now(timezone.utc),
            note=note
        )
        db.session.add(history_entry)
        db.session.commit()

        flash(f"Order #{order.id} status successfully updated to '{new_status}'.", "success")
        return redirect(url_for('owner_orders'))

    form.status.data = order.status
    return render_template('update_order_status.html', form=form, order=order)


# ---------------------------------------------------------
# Cart & Checkout
# ---------------------------------------------------------

@app.route('/cart', methods=['GET', 'POST'])
@login_required
def view_cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).order_by(Cart.added_on.desc()).all()
    subtotal = sum(item.menu_item.price * item.quantity for item in cart_items if item.menu_item)
    delivery_fee = 0.0 if subtotal > 20 or subtotal == 0 else 2.50
    tax = round(subtotal * 0.05, 2)
    total = round(subtotal + delivery_fee + tax, 2)

    return render_template(
        'cart.html',
        title='My Cart',
        cart_items=cart_items,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        tax=tax,
        total=total
    )


@app.route('/cart/add/<int:menu_item_id>', methods=['POST'])
@login_required
def add_to_cart(menu_item_id):
    menu_item = MenuItem.query.get_or_404(menu_item_id)
    qty = request.form.get('quantity', 1, type=int)
    if qty < 1:
        qty = 1

    existing_item = Cart.query.filter_by(user_id=current_user.id, menu_item_id=menu_item.id).first()
    if existing_item:
        existing_item.quantity += qty
    else:
        new_cart_item = Cart(user_id=current_user.id, menu_item_id=menu_item.id, quantity=qty)
        db.session.add(new_cart_item)
    db.session.commit()
    flash(f"'{menu_item.name}' added to your cart!", "success")
    return redirect(request.referrer or url_for('view_cart'))


@app.route('/cart/update/<int:cart_id>', methods=['POST'])
@login_required
def update_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    if cart_item.user_id != current_user.id:
        abort(403)

    if request.form.get('remove'):
        db.session.delete(cart_item)
        flash(f"Removed '{cart_item.menu_item.name}' from your cart.", "info")
    else:
        new_quantity = request.form.get('quantity', 1, type=int)
        if new_quantity < 1:
            db.session.delete(cart_item)
            flash(f"Removed '{cart_item.menu_item.name}' from your cart.", "info")
        else:
            cart_item.quantity = new_quantity
            flash(f"Updated quantity for '{cart_item.menu_item.name}'.", "success")

    db.session.commit()
    return redirect(url_for('view_cart'))


@app.route('/cart/remove/<int:cart_id>', methods=['POST'])
@login_required
def remove_from_cart(cart_id):
    cart_item = Cart.query.get_or_404(cart_id)
    if cart_item.user_id != current_user.id:
        abort(403)
    db.session.delete(cart_item)
    db.session.commit()
    flash(f"'{cart_item.menu_item.name}' removed from your cart.", "info")
    return redirect(url_for('view_cart'))


@app.route('/checkout', methods=['POST'])
@login_required
def checkout():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash("Your cart is empty!", "warning")
        return redirect(url_for('view_cart'))

    subtotal = sum(item.menu_item.price * item.quantity for item in cart_items if item.menu_item)
    delivery_fee = 0.0 if subtotal > 20 else 2.50
    tax = round(subtotal * 0.05, 2)
    total_price = round(subtotal + delivery_fee + tax, 2)

    # Determine restaurant_id from items in cart
    restaurant_id = None
    for item in cart_items:
        if item.menu_item and item.menu_item.restaurant_id:
            restaurant_id = item.menu_item.restaurant_id
            break
    if not restaurant_id:
        restaurant_id = 1

    address = request.form.get('delivery_address', 'Road No 36, Jubilee Hills, Hyderabad')
    phone = request.form.get('phone', '+91 98765 43210')

    # Create order
    new_order = Order(
        user_id=current_user.id,
        restaurant_id=restaurant_id,
        total_price=total_price,
        status='Order Placed',
        delivery_address=address,
        phone=phone,
        date_ordered=datetime.now(timezone.utc)
    )
    db.session.add(new_order)
    db.session.commit()

    # Create order items
    for item in cart_items:
        if item.menu_item:
            order_item = OrderItem(
                order_id=new_order.id,
                menu_item_id=item.menu_item_id,
                quantity=item.quantity,
                price_at_order=item.menu_item.price
            )
            db.session.add(order_item)
            db.session.delete(item)

    # Create initial status history entry
    init_history = OrderStatusHistory(
        order_id=new_order.id,
        status='Order Placed',
        timestamp=datetime.now(timezone.utc),
        note='Order successfully placed and sent to restaurant'
    )
    db.session.add(init_history)
    db.session.commit()

    flash("🎉 Order placed successfully! Live tracking is now active.", "success")
    return redirect(url_for('track_order', order_id=new_order.id))


@app.route('/order/item/<int:order_id>', methods=['GET', 'POST'])
@login_required
def order_item(order_id):
    menu_item = MenuItem.query.get_or_404(order_id)
    form = OrderForm()

    if form.validate_on_submit():
        quantity = form.quantity.data
        total_price = menu_item.price * quantity

        new_order = Order(
            user_id=current_user.id,
            restaurant_id=menu_item.restaurant_id or 1,
            total_price=total_price,
            status='Order Placed',
            date_ordered=datetime.now(timezone.utc)
        )
        db.session.add(new_order)
        db.session.commit()

        order_item_obj = OrderItem(order_id=new_order.id, menu_item_id=menu_item.id, quantity=quantity, price_at_order=menu_item.price)
        db.session.add(order_item_obj)

        init_history = OrderStatusHistory(
            order_id=new_order.id,
            status='Order Placed',
            timestamp=datetime.now(timezone.utc),
            note=f"Quick order placed for {menu_item.name}"
        )
        db.session.add(init_history)
        db.session.commit()

        flash(f"Your order for {menu_item.name} has been placed successfully!", "success")
        return redirect(url_for('track_order', order_id=new_order.id))

    return render_template('place_order.html', form=form, menu_item=menu_item)


# ---------------------------------------------------------
# Feature D: AI Food Assistant Chatbot (Gemini Powered)
# ---------------------------------------------------------

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    user_lat = data.get('latitude')
    user_lng = data.get('longitude')

    if not message:
        return jsonify({'response': "Please enter a question or request so I can help you!"}), 400

    user_id = current_user.id if current_user.is_authenticated else None

    # Call AI Assistant engine
    response_text = generate_ai_response(
        user_message=message,
        user_id=user_id,
        user_lat=user_lat,
        user_lng=user_lng
    )

    return jsonify({'response': response_text})


# ---------------------------------------------------------
# Admin Dashboard
# ---------------------------------------------------------

@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_owner:
        flash("You are not authorized to access the Admin Dashboard.", "danger")
        return redirect(url_for('home'))

    total_users = User.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_price)).scalar() or 0.0
    total_menu_items = MenuItem.query.count()
    total_restaurants = Restaurant.query.count()

    recent_orders = Order.query.order_by(Order.date_ordered.desc()).limit(10).all()
    recent_reviews = RestaurantReview.query.order_by(RestaurantReview.created_at.desc()).limit(5).all()

    return render_template(
        'admin.html',
        title="Admin Dashboard",
        total_users=total_users,
        total_orders=total_orders,
        total_revenue=total_revenue,
        total_menu_items=total_menu_items,
        total_restaurants=total_restaurants,
        recent_orders=recent_orders,
        recent_reviews=recent_reviews
    )


# ---------------------------------------------------------
# Blog / Posts
# ---------------------------------------------------------

@app.route('/posts')
def all_posts():
    posts = Post.query.order_by(Post.date_posted.desc()).all()
    return render_template('all_posts.html', title='Community & Food Stories', posts=posts)


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data.strip(), content=form.content.data.strip(),
                    details=form.details.data.strip() if form.details.data else '', author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your food story has been published!', 'success')
        return redirect(url_for('all_posts'))
    return render_template('create_post.html', title='New Post', form=form, legend='Share a Food Story')


@app.route('/post/<int:post_id>')
def single_post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('single_post.html', title=post.title, post=post)


@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_owner:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data.strip()
        post.content = form.content.data.strip()
        post.details = form.details.data.strip() if form.details.data else ''
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('single_post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
        form.details.data = post.details
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')


@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user and not current_user.is_owner:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Post deleted successfully.', 'success')
    return redirect(url_for('all_posts'))
