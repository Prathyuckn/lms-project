from bson import ObjectId
from flask_login import UserMixin, current_user
from app import login_manager

from .database import db


class User(UserMixin):
    def __init__(self, user_id, fullname, role):
        self.id = user_id
        self.fullname = fullname
        self.role = role

    def add_attribute(self, key, value):
        """Add a custom attribute to the User object dynamically."""
        setattr(self, key, value)


@login_manager.user_loader
def load_user(user_id):
    # Load user based on the role-specific collection
    for role in ["admin", "staff", "member"]:
        user_collection = db.get_collection(role)
        user_data = user_collection.find_one({"_id": ObjectId(user_id)})
        if user_data:
            fullname = (
                user_data["fullname"]
                if role == "admin"
                else f"{user_data['firstname']} {user_data['lastname']}"
            )
            user = User(str(user_data["_id"]), fullname, user_data["role"])
            if role == "staff":
                branch_collection = db.get_collection("branches")
                branch_data = branch_collection.find_one(
                    {"_id": ObjectId(user_data["branch_id"])}
                )
                user.add_attribute("branch_id", user_data.get("branch_id", ""))
                user.add_attribute("branch_name", branch_data["name"])
            return user
    return None
