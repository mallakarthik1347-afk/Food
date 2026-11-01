from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FloatField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Optional, Email, EqualTo, Length, NumberRange, ValidationError
from foodMenuWebsite.models import User
from flask_login import current_user

class RegisterForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=30)])
    last_name = StringField('Last Name (Optional)', validators=[Optional(), Length(min=2, max=30)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, message="Password must be at least 6 characters")])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Passwords must match")])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.strip().lower()).first()
        if user:
            raise ValidationError('Email already exists. Please choose another or log in.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=30)])
    last_name = StringField('Last Name (Optional)', validators=[Optional(), Length(min=2, max=30)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png', 'jpeg', 'webp'], 'Images only!')])
    submit = SubmitField('Update')

    def validate_email(self, email):
        if email.data.strip().lower() != current_user.email.lower():
            user = User.query.filter_by(email=email.data.strip().lower()).first()
            if user:
                raise ValidationError('Email already registered by another account.')

class RestaurantReviewForm(FlaskForm):
    rating = SelectField(
        'Rating',
        choices=[
            ('5', '⭐⭐⭐⭐⭐ (5 - Exceptional)'),
            ('4', '⭐⭐⭐⭐ (4 - Very Good)'),
            ('3', '⭐⭐⭐ (3 - Average)'),
            ('2', '⭐⭐ (2 - Below Average)'),
            ('1', '⭐ (1 - Poor)')
        ],
        validators=[DataRequired()]
    )
    comment = TextAreaField('Review Comments', validators=[DataRequired(), Length(min=5, max=1000, message="Review must be between 5 and 1000 characters")])
    submit = SubmitField('Submit Review')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(min=2, max=200)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=5, max=2000)])
    details = TextAreaField('More Details (Optional)', validators=[Optional(), Length(max=10000)])
    submit = SubmitField('Publish')

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(), Length(max=120)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=5, max=2000)])
    submit = SubmitField('Send Message')

class OrderForm(FlaskForm):
    food_item = StringField('Food Item', validators=[DataRequired(), Length(min=2)])
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1, max=50)])
    submit = SubmitField('Place Order')

class UpdateOrderStatusForm(FlaskForm):
    status = SelectField(
        "Order Status",
        choices=[
            ("Order Placed", "Order Placed"),
            ("Order Confirmed", "Order Confirmed"),
            ("Preparing Food", "Preparing Food"),
            ("Ready for Pickup", "Ready for Pickup"),
            ("Out for Delivery", "Out for Delivery"),
            ("Delivered", "Delivered"),
            ("Cancelled", "Cancelled")
        ],
        validators=[DataRequired()]
    )
    note = StringField("Update Note (Optional)", validators=[Optional(), Length(max=200)])
    submit = SubmitField('Update Order Status')

class MenuItemForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=750)])
    category = StringField('Category', validators=[DataRequired(), Length(min=2, max=100)])
    image_url = StringField('Image URL', validators=[Optional(), Length(max=500)])
    is_veg = BooleanField('Vegetarian')
    is_spicy = BooleanField('Spicy')
    restaurant_id = IntegerField('Restaurant ID', validators=[Optional()])
    submit = SubmitField('Save Item')
