from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

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
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes a user object
        """
        self.username = kwargs.get("username")
        self.password = kwargs.get("password")

    def serialize(self):
        """
        Serializes a user object
        """
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password
        }
    
    def simple_serialize(self):
        """
        Serializes a user object without courses field
        """
        return {
            "id": self.id,
            "username": self.username,
            "password": self.password
        }
    
class Clothing(db.Model):
    """
    Clothing model
    """
    __tablename__ = "clothing"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    classification = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def __init__(self, **kwargs):
        """
        Initializes a clothing object
        """
        self.classification = kwargs.get("classification")
        self.user_id = kwargs.get("user_id")

    def serialize(self):
        """
        Serializes a clothing object
        """
        return {
            "id": self.id,
            "classification": self.classification,
            "user_id": self.user_id
        }
    
class Outfit(db.Model):
    """
    Outfit model
    """
    __tablename__ = "outfit"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String, nullable=False)
    headwear_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    top_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    bottom_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
    shoes_id = db.Column(db.Integer, db.ForeignKey("clothing.id"))
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
            "name": self.name,
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