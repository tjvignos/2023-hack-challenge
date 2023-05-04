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

# upload route
@app.route("/upload/", methods=["POST"])
def upload():
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No base64 image found")
    asset = Asset(image_data=image_data)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)

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

# clothing routes
#   Create Clothing
#   Get Clothing list by user
#   Delete Clothing

# Outfit Routes
#   Create Outfit
#   Delete Outfit
#   Get Outfit list by user

# Tag Routes
#   Add tag
#   Remove tag


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)