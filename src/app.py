import json
from db import db
from flask import Flask, request
from db import User
from db import Clothing
from db import Outfit
from db import Tag

app = Flask(__name__)
db_filename = "clothes.db"

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

# user routes
#   SignUp User (Create User)

@app.route("/signup/", methods=["POST"])
def create_user():
    """
    Endpoint for creating a user
    """
    body = json.loads(request.data)
    username = body.get("username")
    password = body.get("password")
    # checking if username and password are present 
    # delegated to frontend

    user = User.query.filter_by(username=username).first()
    if user is not None:
        return failure_response("Username taken", 400)

    new_user = User(
        username = username,
        password = password
    )
    db.session.add(new_user)
    db.session.commit()
    return success_response(new_user.serialize(), 201)


#   Login User (IsUser)
#   Get User

# clothing routes
#   Create Clothing
#   Get Clothing
#   Delete Clothing

# Outfit Routes
#   Create Outfit
#   Delete Outfit
#   Get Outfit

# Tag Routes
#   Add tag
#   Remove tag


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)