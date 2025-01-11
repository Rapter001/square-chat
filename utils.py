import os
from werkzeug.utils import secure_filename
from PIL import Image

# Function to save and resize a profile picture
def save_profile_pic(form_picture):
    # Extract the file extension from the uploaded picture
    _, f_ext = os.path.splitext(secure_filename(form_picture.filename))
    
    # Generate a random filename to avoid name conflicts, using 8 random bytes
    picture_fn = f'{os.urandom(8).hex()}{f_ext}'
    
    # Define the path where the picture will be saved
    picture_path = os.path.join('square-chat/static/profile_pics', picture_fn)
    
    # Resize the image to 125x125 pixels
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    
    # Save the resized image to the specified path
    i.save(picture_path)
    
    # Return the generated filename for saving to the user's profile
    return picture_fn
