from flask_sqlalchemy import SQLAlchemy
import base64
import boto3
import datetime
import io
from io import BytesIO
from mimetypes import guess_extension, guess_type
import os
from PIL import Image
import random
import re
import string
import hashlib
import bcrypt

db = SQLAlchemy()

# image model and methods
EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-1.amazonaws.com"

class Asset(db.Model):
    """
    Asset model
    """
    __tablename__ = "assets"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    base_url = db.Column(db.String, nullable=False)
    salt = db.Column(db.String, nullable=False)
    extension = db.Column(db.String, nullable=False)
    width = db.Column(db.Integer, nullable=False)
    height = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    
    def __init__(self, **kwargs):
        """
        Initializes an asset object
        """
        self.create(kwargs.get("image_data"))

    def create(self, image_data):
        """
        Given an image in base64 encoding, does the following:
        1. Rejects the image if it is not a supported filename
        2. Generate a random string for the image filename
        3. Decodes the image and attempts to upload it to AWS
        """
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]
            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} is not valid!")
            salt = "".join(
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))
            
            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()

            img_filename = f"{self.salt}.{self.extension}"
            
            self.upload(img, img_filename)
        except Exception as e:
            print(f"Error when creating image: {e}")

    def upload(self, img, img_filename):
        """
        Attempts to upload the image into the specified S3 bucket
        """
        try:
            #save image into temporary location
            img_temp_location = f"{BASE_DIR}/{img_filename}"
            img.save(img_temp_location)
            
            #upload image into s3 bucket
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temp_location, S3_BUCKET_NAME, img_filename)
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename)
            object_acl.put(ACL = "public-read")
            
            #remove image from temp location
            os.remove(img_temp_location)
        except Exception as e:
            print(f"Error when uploading image: {e}")

    def serialize(self):
        """
        Serializes an asset object
        """
        return {
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at)
        }


association_table = db.Table(
    "association table",
    db.Column("outfit_id", db.Integer, db.ForeignKey("outfit.id")),
    db.Column("tag_id", db.Integer, db.ForeignKey("tag.id"))
)

class User(db.Model):
    """
    User model
    """
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    # User information
    username = db.Column(db.String, nullable=False, unique=True)
    password_digest = db.Column(db.String, nullable=False)
    
    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        """
        Initializes a user object
        """
        self.username = kwargs.get("username")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.renew_session()

    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token
    
    def serialize(self):
        """
        Serializes a user object
        """
        return {
            "id": self.id,
            "username": self.username
        }
    
class Clothing(db.Model):
    """
    Clothing model
    """
    __tablename__ = "clothing"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asset_id = db.Column(db.Integer, nullable=False)
    classification = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes a clothing object
        """
        self.asset_id = kwargs.get("asset_id")
        self.classification = kwargs.get("classification")
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializes a clothing object
        """
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "classification": self.classification,
            "user_id": self.user_id
        }
    
class Outfit(db.Model):
    """
    Outfit model
    """
    __tablename__ = "outfit"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    headwear_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    top_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    bottom_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    shoes_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    tags = db.relationship("Tag", secondary=association_table)

    def __init__(self, **kwargs):
        """
        Initializes an outfit object
        """
        self.headwear_id = kwargs.get("headwear_id")
        self.top_id = kwargs.get("top_id")
        self.bottom_id = kwargs.get("bottom_id")
        self.shoes_id = kwargs.get("shoes_id")

    def serialize(self):
        """
        Serializes an outfit object
        """
        tag_list = [i.serialize() for i in self.tags]
        return {
            "id": self.id,
            "tags": tag_list
        }

class Tag(db.Model):
    """
    Tag model
    """
    __tablename__ = "tag"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    label = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes a tag object
        """
        self.label = kwargs.get("label")

    def serialize(self):
        """
        Serializes a tag object
        """
        return {
            "id": self.id,
            "label": self.label
        }