import os
from werkzeug.utils import secure_filename
from PIL import Image

def save_profile_pic(form_picture):
    _, f_ext = os.path.splitext(secure_filename(form_picture.filename))
    picture_fn = f'{os.urandom(8).hex()}{f_ext}'
    picture_path = os.path.join('static/profile_pics', picture_fn)
    
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn
