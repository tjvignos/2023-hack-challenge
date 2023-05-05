import json
from db import db
from flask import Flask, request
from db import User
from db import Clothing
from db import Outfit
from db import Tag
from db import Asset
import users_dao
import datetime

app = Flask(__name__)
db_filename = "ootd.db"

app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_filename}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()

# generalized response formats
def success_response(data, code=200):
    return json.dumps(data), code

def failure_response(message, code=404):
    return json.dumps({"error": message}), code

# authentication method
def extract_token(request):
    """
    Helper function that extracts the token from the header of a request
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, failure_response("Missing auth header", 400)
    bearer_token = auth_header.replace("Bearer", "").strip()
    if not bearer_token:
        return False, failure_response("Invalid auth header", 400)
    return True, bearer_token

# base endpoint
@app.route("/")
def hello_world():
    """
    Endpoint for printing Hello World!
    """
    return "Hello World!"

# user routes
@app.route("/register/", methods=["POST"])
def register_account():
    """
    Endpoint for registering a new user
    """
    body = json.loads(request.data)
    username = body.get("username")
    password = body.get("password")

    if username is None or password is None:
        return failure_response("Invalid username or password", 400)
    
    created, user = users_dao.create_user(username, password)

    if not created:
        return failure_response("User already exists", 400)

    return success_response(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token
        }
    )

@app.route("/login/", methods=["POST"])
def login():
    """
    Endpoint for logging in a user
    """
    body = json.loads(request.data)
    username = body.get("username")
    password = body.get("password")
    
    if username is None or password is None:
        return failure_response("Invalid username or password", 400)
    
    success, user = users_dao.verify_credentials(username, password)

    if not success:
        return failure_response("Incorrect username or password", 400)

    return success_response(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token
        }
    )

@app.route("/logout/", methods=["POST"])
def logout():
    """
    Endpoint for logging out a user
    """
    success, session_token = extract_token(request)
    if not success:
        return session_token
    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    user.session_expiration = datetime.datetime.now()
    db.session.commit()
    return success_response({"message": "User has successfully logged out"})

@app.route("/session/", methods=["POST"])
def update_session():
    """
    Endpoint for updating a user's session
    """
    success, update_token = extract_token(request)
    if not success:
        return update_token
    user = users_dao.renew_session(update_token)
    if user is None:
        return failure_response("Invalid update token")
    return success_response(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token
        }
    )

@app.route("/secret/", methods=["POST"])
def secret_message():
    """
    Endpoint for verifying a session token and returning a secret message

    In your project, you will use the same logic for any endpoint that needs 
    authentication
    """
    success, session_token = extract_token(request)

    if not success:
        return session_token
    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
    
    return success_response({"message": "Wow we implemented session token!!"})

@app.route("/user/id/", methods=["POST"])
def get_user_id():
    """
    Gets user_id by username
    """
    body = json.loads(request.data)
    username = body.get("username")
    user = User.query.filter_by(username=username).first()
    return str(user.id)

@app.route("/user/list/")
def user_list():
    """
    Endpoint for getting a list of all users
    """
    return [user.serialize() for user in User.query.all()]

# clothing routes
#   Create Clothing

@app.route("/clothing/", methods=["POST"])
def upload():
    """
    Endpoint for uploading an image to AWS given its base64 form,
    adding the image to the clothing table, then returning the
    serialized clothing object
    """
    body = json.loads(request.data)
    classification = body.get("classification")
    username = body.get("username")
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No base64 image found")
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    user = User.query.filter_by(username=username).first()
    clothing = Clothing(
        asset_id = asset.id,
        classification = classification,
        user_id = user.id
    )
    db.session.add(clothing)
    db.session.commit()
    return success_response(asset.serialize(), 201)

#   Get Clothing list by user

@app.route("/clothing/", methods=["POST"])
def get_clothing():
    """
    Endpoint for getting a list of clothing by username
    """
    body = json.loads(request.data)
    username = body.get("username")
    user = User.query.filter_by(username=username).first()
    clothing = [clothes.serialize() for clothes in Clothing.query.filter_by(user_id=user.id)]
    return success_response({"clothing": clothing})

@app.route("/clothing/filter/", methods=["POST"])
def filter_clothing():
    """
    Endpoint for getting a list of clothing by username 
    filtered by classification
    """
    body = json.loads(request.data)
    username = body.get("username")
    classification = body.get("classification")
    user = User.query.filter_by(username=username).first()
    return [clothing.asset_serialize() for clothing in Clothing.query.filter_by(user_id=user.id, classification=classification)]

#   Delete Clothing

@app.route("/clothing/<int:id>/", methods=["DELETE"])
def delete_clothing(id):
    """
    Endpoint for deleting clothing by id
    """
    clothing = Clothing.query.filter_by(id=id).first()
    if clothing is None:
        return failure_response("Clothing not found")
    db.session.delete(clothing)
    db.session.commit()
    return success_response(clothing.serialize())

# Outfit Routes
#   Create Outfit

@app.route("/outfit/", methods=["POST"])
def create_outfit():
    """
    Endpoint for creating an outfit
    """
    body = json.loads(request.data)
    headwear_id = body.get("headwear_id")
    top_id = body.get("top_id")
    bottom_id = body.get("bottom_id")
    shoes_id = body.get("shoes_id")
    username = body.get("username")
    user = User.query.filter_by(username=username).first()
    outfit = Outfit(
        headwear_id = headwear_id,
        top_id = top_id,
        bottom_id = bottom_id,
        shoes_id = shoes_id,
        user_id = user.id
    )
    db.session.add(outfit)
    db.session.commit()
    return success_response(outfit.serialize(), 201)

#   Get Outfit list by user

@app.route("/outfit/", methods=["POST"])
def get_outfits():
    """
    Endpoint for getting all outfits by user id
    """
    body = json.loads(request.data)
    username = body.get("username")
    user = User.query.filter_by(username=username).first()
    outfits = [outfit.serialize() for outfit in Outfit.query.filter_by(user_id=user.id)]
    return success_response({"outfits": outfits})

#   Delete Outfit

@app.route("/outfit/<int:id>/", methods=["DELETE"])
def delete_outfit(id):
    """
    Endpoint for deleting an outfit by id
    """
    outfit = Outfit.query.filter_by(id=id).first()
    if outfit is None:
        return failure_response("Outfit not found")
    db.session.delete(outfit)
    db.session.commit()
    return success_response(outfit.serialize())

# Tag Routes
#   Add tag

@app.route("/tag/<int:outfit_id>/", methods=["POST"])
def add_tag(outfit_id):
    """
    Endpoint for creating and adding a tag to an outfit by outfit id
    """
    body = json.loads(request.data)
    label = body.get("label")
    tag = Tag.query.filter_by(label=label).first()
    if tag is None:
        tag = Tag(label=label)
        db.session.add(tag)
    if label is None:
        return failure_response("Lable not present", 400)
    outfit = Outfit.query.filter_by(id=outfit_id).first()
    outfit.tags.append(tag)
    db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)