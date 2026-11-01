from datetime import datetime, timezone
from flask_login import UserMixin
from foodMenuWebsite import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80))
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(128), nullable=False)
    date_created = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    image_file = db.Column(db.String(50), nullable=False, default='default.webp')
    is_owner = db.Column(db.Boolean, default=False)

    # Relationships
    posts = db.relationship('Post', backref='author', lazy=True)
    orders = db.relationship('Order', backref='customer', lazy=True, order_by='Order.date_ordered.desc()')
    reviews = db.relationship('RestaurantReview', backref='user', lazy=True)

    @property
    def is_admin(self):
        return bool(self.is_owner)

    def __repr__(self):
        return f"User('{self.first_name}', '{self.last_name}', '{self.email}')"


class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    address = db.Column(db.String(500))
    phone = db.Column(db.String(20))
    image_url = db.Column(db.String(500), default='')
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    rating = db.Column(db.Float, default=4.5)
    total_reviews = db.Column(db.Integer, default=0)
    is_veg = db.Column(db.Boolean, default=False)
    cuisine_type = db.Column(db.String(200), default='Multi-Cuisine')
    opening_hours = db.Column(db.String(100), default='9:00 AM - 11:00 PM')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    menu_items = db.relationship('MenuItem', backref='restaurant', lazy=True)
    reviews = db.relationship('RestaurantReview', backref='restaurant', lazy=True, order_by='RestaurantReview.created_at.desc()')
    orders = db.relationship('Order', backref='restaurant', lazy=True)

    def update_rating(self):
        revs = self.reviews
        if revs:
            self.total_reviews = len(revs)
            self.rating = round(sum(r.rating for r in revs) / len(revs), 1)
        else:
            self.total_reviews = 0
            self.rating = 4.5

    def __repr__(self):
        return f"Restaurant('{self.name}', '{self.cuisine_type}', Rating: {self.rating})"


class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100), nullable=False)
    image_url = db.Column(db.String(500), default='')
    is_veg = db.Column(db.Boolean, default=True)
    is_spicy = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Float, default=4.5)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=True)

    def __repr__(self):
        return f"MenuItem('{self.name}', '{self.category}', ${self.price})"


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=True)
    total_price = db.Column(db.Float, nullable=False)
    date_ordered = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(50), default='Order Placed')
    delivery_address = db.Column(db.String(500), default='MG Road, Hyderabad')
    phone = db.Column(db.String(20), default='+91 98765 43210')

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade="all, delete-orphan")
    status_history = db.relationship('OrderStatusHistory', backref='order', lazy=True,
                                     order_by='OrderStatusHistory.timestamp.asc()', cascade="all, delete-orphan")
    review = db.relationship('RestaurantReview', backref='order', uselist=False, lazy=True)

    def __repr__(self):
        return f"Order(#{self.id}, User: {self.user_id}, Status: '{self.status}', Total: ${self.total_price})"


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price_at_order = db.Column(db.Float, nullable=True)

    menu_item = db.relationship('MenuItem', backref='order_items')

    def __repr__(self):
        return f"OrderItem(Order #{self.order_id}, Item #{self.menu_item_id}, Qty: {self.quantity})"


class OrderStatusHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    note = db.Column(db.String(200), default='')

    def __repr__(self):
        return f"OrderStatusHistory(Order #{self.order_id}, '{self.status}' at {self.timestamp})"


class RestaurantReview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False, unique=True)
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), server_default=db.func.now())

    def __repr__(self):
        return f"RestaurantReview(Restaurant #{self.restaurant_id}, Rating: {self.rating}, User #{self.user_id})"


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_on = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    menu_item = db.relationship('MenuItem', backref='cart_items')

    def __repr__(self):
        return f"Cart(User: {self.user_id}, Item: {self.menu_item_id}, Qty: {self.quantity})"


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    content = db.Column(db.Text, nullable=False)
    details = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text)
    date_sent = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"Message('{self.name}', '{self.email}')"


# Legacy Review model preserved for database compatibility
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text)

    def __repr__(self):
        return f"Review('{self.user_id}', '{self.date}')"
