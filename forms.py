from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField
from wtforms.validators import DataRequired, Length, EqualTo, Email

# Form for user login
class LoginForm(FlaskForm):
    # Username input field with a minimum length of 3 and a maximum of 80 characters
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    
    # Password input field (required)
    password = PasswordField('Password', validators=[DataRequired()])
    
    # Submit button for the form
    submit = SubmitField('Login')

# Form for user signup/registration
class SignupForm(FlaskForm):
    # Username input field with a minimum length of 3 and a maximum of 80 characters
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    
    # Email input field, must be a valid email format
    email = StringField('Email', validators=[DataRequired(), Email()])
    
    # Password input field with a minimum length of 6 characters
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    
    # Confirm password input field to match the password field
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    
    # Optional field for uploading a profile picture
    profile_pic = FileField('Profile Picture')
    
    # Submit button for the form
    submit = SubmitField('Sign Up')

# Form for updating user account information
class UpdateAccountForm(FlaskForm):
    # Username input field with a minimum length of 3 and a maximum of 80 characters
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    
    # Email input field, must be a valid email format
    email = StringField('Email', validators=[DataRequired(), Email()])
    
    # Optional field for updating profile picture
    profile_pic = FileField('Update Profile Picture')
    
    # Optional field for entering a new password with a minimum length of 6 characters
    password = PasswordField('New Password', validators=[Length(min=6)])
    
    # Confirm new password field to match the password field
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('password')])
    
    # Submit button for the form
    submit = SubmitField('Update')
