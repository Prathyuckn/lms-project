from datetime import datetime, timedelta
from bson import ObjectId
from flask import redirect
from flask_login import login_user
from app.utils.auth import User
from app.utils.database import db
from pymongo import errors, ReturnDocument
from werkzeug.security import generate_password_hash, check_password_hash

from app.utils.enums import BorrowedItemStatus, ItemCopyStatus, MemberStatus
from app.utils.init_roles import generate_member_id

member_collection = db.get_collection("member")
borrowed_collection = db.get_collection("borrowed_items")
items_collection = db.get_collection("library_items")
branches_collection = db.get_collection("branches")
copies_collection = db.get_collection("copies")
reservations_collection = db.get_collection("reservations")
notifications_collection = db.get_collection("notifications")


def member_update_password(member_id, password):
    member = member_collection.find_one(
        {"member_id": member_id, "status": {"$ne": MemberStatus.DELETED.value}}
    )

    if not member:
        return {"status": "fail", "message": "Invalid Member ID"}

    if member["status"] == MemberStatus.PENDING.value:
        return {
            "status": "fail",
            "message": "Your registration has not been approved yet, so you cannot log in at this time",
        }

    if member["status"] == MemberStatus.BLOCKED.value:
        return {
            "status": "fail",
            "message": "We’re sorry, but your account has been blocked.",
        }

    hashed_password = generate_password_hash(password)
    member_collection.update_one(
        {"member_id": member_id}, {"$set": {"password": hashed_password}}
    )
    return {"status": "success", "message": "Password updated successfully"}


def member_login(data):
    member_id = data.get("member_id")
    password = data.get("password")

    member = member_collection.find_one(
        {"member_id": member_id, "status": {"$ne": MemberStatus.DELETED.value}}
    )

    if not member:
        return {"status": "fail", "message": "Invalid Member ID"}

    if member["status"] == MemberStatus.PENDING.value:
        return {
            "status": "fail",
            "message": "Your registration has not been approved yet, so you cannot log in at this time",
        }

    if member["status"] == MemberStatus.BLOCKED.value:
        return {
            "status": "fail",
            "message": "We’re sorry, but your account has been blocked.",
        }

    if check_password_hash(member["password"], password):
        fullname = f"{member['firstname']} {member['lastname']}"
        user = User(str(member["_id"]), fullname, member["role"])
        login_user(user)  # Sets `current_user`
        return {"status": "success"}
    else:
        return {"status": "fail", "message": "The login credentials you provided are invalid."}


def registration(data):
    try:
        member_id = generate_member_id(db)
        member = {
            "member_id": member_id,
            "firstname": data.get("firstname"),
            "lastname": data.get("lastname"),
            "email": data.get("email"),
            "contact_no": data.get("contact_no"),
            "address": data.get("address"),
            "password": generate_password_hash(data.get("password")),
            "due_amount": None,
            "created_at": datetime.now(),
            "status": MemberStatus.PENDING.value,
            "role": "member",
        }
        member_collection.insert_one(member)
        return {
            "status": "success",
            "message": f"Registration successful! Please save your member ID : {member_id}. You can log in once your registration is approved.",
            "member_id": member_id,
        }
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def member_update(member_id, data):
    try:
        member_data = {
            "firstname": data.get("firstname"),
            "lastname": data.get("lastname"),
            "email": data.get("email"),
            "contact_no": data.get("contact_no"),
            "address": data.get("address"),
        }
        result = member_collection.find_one_and_update(
            {"_id": ObjectId(member_id)},
            {"$set": member_data},
            return_document=ReturnDocument.AFTER,
        )
        result["_id"] = str(result["_id"])  # Convert for rendering
        fullname = f"{result['firstname']} {result['lastname']}"
        user = User(str(result["_id"]), fullname, result["role"])
        login_user(user)  # Sets `current_user`
        return {"status": "success", "message": "Profile updated successfully."}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def get_member_with_borrowed_items(member_id, status=None):
    try:
        match_filter = {"member_id": str(member_id).upper(), "status": MemberStatus.APPROVED.value}
        if status:
            match_filter["status"] = status

        member = member_collection.aggregate([
            {"$match": match_filter},
            {
                "$lookup": {
                    "from": borrowed_collection.name,
                    "localField": "_id",
                    "foreignField": "member_id",
                    "pipeline": [
                        {"$match": {"returned": False}},
                        {"$lookup": {"from": items_collection.name, "localField": "item_id", "foreignField": "_id", "as": "item"}},
                        {"$unwind": "$item"},
                        {"$lookup": {"from": branches_collection.name, "localField": "branch_id", "foreignField": "_id", "as": "branch"}},
                        {"$unwind": "$branch"},
                    ],
                    "as": "borrowed_items",
                }
            },
        ])

        member_list = list(member)
        if not member_list:
            return {"status": "fail", "message": "Member not found"}

        member_data = member_list[0]
        member_data["_id"] = str(member_data["_id"])
        for b in member_data.get("borrowed_items", []):
            b["_id"] = str(b["_id"])
            b["item"]["_id"] = str(b["item"]["_id"])
            b["branch"]["_id"] = str(b["branch"]["_id"])

        return {"status": "success", "data": member_data}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def get_member_with_borrowed_history(member_id, status=None):
    try:
        match_filter = {"member_id": str(member_id).upper(), "status": MemberStatus.APPROVED.value}
        if status:
            match_filter["status"] = status

        member = member_collection.aggregate([
            {"$match": match_filter},
            {
                "$lookup": {
                    "from": borrowed_collection.name,
                    "localField": "_id",
                    "foreignField": "member_id",
                    "pipeline": [
                        {"$lookup": {"from": items_collection.name, "localField": "item_id", "foreignField": "_id", "as": "item"}},
                        {"$unwind": "$item"},
                        {"$lookup": {"from": branches_collection.name, "localField": "branch_id", "foreignField": "_id", "as": "branch"}},
                        {"$unwind": "$branch"},
                    ],
                    "as": "borrowed_items",
                }
            },
            {"$sort": {"returned": -1}},
        ])

        member_list = list(member)
        if not member_list:
            return {"status": "fail", "message": "Member not found"}

        member_data = member_list[0]
        member_data["_id"] = str(member_data["_id"])
        for b in member_data.get("borrowed_items", []):
            b["_id"] = str(b["_id"])
            b["item"]["_id"] = str(b["item"]["_id"])
            b["branch"]["_id"] = str(b["branch"]["_id"])

        return {"status": "success", "data": member_data}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def get_member_by_id(id):
    try:
        member = member_collection.find_one({"_id": ObjectId(id)})
        if not member:
            return {"status": "fail", "message": "Member not found"}
        member["_id"] = str(member["_id"])
        return {"status": "success", "data": member}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def member_get_borrowed_items(member_id, returned=False):
    try:
        filter_query = {"member_id": member_id, "returned": False}
        if returned:
            filter_query["returned"] = True

        items = borrowed_collection.aggregate([
            {"$match": filter_query},
            {"$lookup": {"from": items_collection.name, "localField": "item_id", "foreignField": "_id", "as": "item"}},
            {"$unwind": "$item"},
            {"$lookup": {"from": copies_collection.name, "localField": "copy_id", "foreignField": "_id", "as": "copy"}},
            {"$unwind": "$copy"},
            {"$lookup": {"from": branches_collection.name, "localField": "branch_id", "foreignField": "_id", "as": "branch"}},
            {"$unwind": "$branch"},
        ])
        items_list = list(items)
        for i in items_list:
            i["_id"] = str(i["_id"])
            i["item"]["_id"] = str(i["item"]["_id"])
            i["copy"]["_id"] = str(i["copy"]["_id"])
            i["branch"]["_id"] = str(i["branch"]["_id"])

        return {"status": "success", "data": items_list}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def renew_borrowed_item(member_id, borrowed_item_id):
    try:
        borrowed_item_id = ObjectId(borrowed_item_id)

        borrowed_item = borrowed_collection.find_one(
            {"_id": borrowed_item_id, "member_id": member_id}
        )
        if not borrowed_item:
            return {"status": "fail", "message": f"No borrowed item found with ID {borrowed_item_id}."}

        if borrowed_item.get("renewals_left", 0) == 0:
            return {"status": "fail", "message": "Renewal limit reached. You cannot renew this item further."}

        reservation = reservations_collection.find_one({
            "item_id": ObjectId(borrowed_item["item_id"]),
            "branch_id": ObjectId(borrowed_item["branch_id"]),
        })
        if reservation:
            return {"status": "fail", "message": "Renewal Denied. This item has been reserved by other member."}

        previous_due_date = borrowed_item["due_date"]
        if isinstance(previous_due_date, str):
            previous_due_date = datetime.strptime(previous_due_date, "%Y-%m-%d")
        new_due_date = previous_due_date + timedelta(weeks=3)

        borrowed_item["_id"] = str(borrowed_item["_id"])
        borrowed_item["item_id"] = str(borrowed_item["item_id"])
        borrowed_item["branch_id"] = str(borrowed_item["branch_id"])

        return {"status": "success", "data": borrowed_item}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}
# Continue from renew_borrowed_item
def renew_borrowed_item(member_id, borrowed_item_id):
    try:
        borrowed_item_id_obj = ObjectId(borrowed_item_id)

        borrowed_item = borrowed_collection.find_one(
            {"_id": borrowed_item_id_obj, "member_id": member_id}
        )
        if not borrowed_item:
            return {"status": "fail", "message": f"No borrowed item found with ID {borrowed_item_id}."}

        if borrowed_item.get("renewals_left", 0) == 0:
            return {"status": "fail", "message": "Renewal limit reached. You cannot renew this item further."}

        reservation = reservations_collection.find_one({
            "item_id": borrowed_item["item_id"],
            "branch_id": borrowed_item["branch_id"],
        })
        if reservation:
            return {"status": "fail", "message": "Renewal Denied. This item has been reserved by other member."}

        previous_due_date = borrowed_item["due_date"]
        if isinstance(previous_due_date, str):
            previous_due_date = datetime.strptime(previous_due_date, "%Y-%m-%d")
        new_due_date = previous_due_date + timedelta(weeks=3)

        # Update the borrowed item in the database
        update_result = borrowed_collection.update_one(
            {"_id": borrowed_item_id_obj},
            {"$set": {"due_date": new_due_date}, "$inc": {"renewals_left": -1}},
        )

        if update_result.modified_count == 0:
            return {"status": "fail", "message": "Failed to renew the borrowed item. Please try again."}

        borrowed_item["_id"] = str(borrowed_item["_id"])
        borrowed_item["item_id"] = str(borrowed_item["item_id"])
        borrowed_item["branch_id"] = str(borrowed_item["branch_id"])
        borrowed_item["due_date"] = new_due_date

        return {"status": "success", "message": "Item Renewed Successfully", "data": borrowed_item}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def reserve_library_item(member_id, item_id, branch_id):
    try:
        # Keep member_id, item_id, branch_id as strings
        # Convert to ObjectId only when querying _id fields in DB
        item_id_obj = ObjectId(item_id)
        branch_id_obj = ObjectId(branch_id)

        library_item = items_collection.find_one({"_id": item_id_obj})
        if not library_item:
            return {"status": "fail", "message": f"Library item with ID {item_id} not found."}

        copies = list(copies_collection.find({"item_id": item_id_obj, "original_branch_id": branch_id_obj}))
        available_copies = [c for c in copies if c["status"] == ItemCopyStatus.AVAILABLE.value]

        if available_copies:
            return {"status": "fail", "message": "Copies are available in the specified branch. Reservation is not allowed."}

        borrowed = borrowed_collection.find_one({"member_id": member_id, "item_id": item_id, "returned": False})
        if borrowed:
            return {"status": "fail", "message": "You have already borrowed this item."}

        existing_reservation = reservations_collection.find_one({"member_id": member_id, "item_id": item_id, "branch_id": branch_id})
        if existing_reservation:
            return {"status": "fail", "message": "You have already reserved this item in the specified branch."}

        reservation = {
            "member_id": member_id,
            "item_id": item_id,
            "branch_id": branch_id,
            "reserved_date": datetime.now(),
            "status": "active",
        }
        reservations_collection.insert_one(reservation)

        notification = {
            "notification_id": f"NTF{notifications_collection.count_documents({}) + 1:04d}",
            "member_id": member_id,
            "message": f"You have reserved the {library_item['item_type']} <em>'{library_item['title']}'</em>.",
            "date": datetime.now(),
            "status": "unread",
        }
        notifications_collection.insert_one(notification)

        reservation["_id"] = str(reservation.get("_id", ""))

        return {"status": "success", "message": "Reservation successful.", "reservation": reservation}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def reserved_items(member_id=None, branch_id=None, item_id=None):
    try:
        filter_query = {}
        if member_id:
            filter_query["member_id"] = member_id
        if branch_id:
            filter_query["branch_id"] = branch_id
        if item_id:
            filter_query["item_id"] = item_id

        items = reservations_collection.aggregate([
            {"$match": filter_query},
            {"$lookup": {"from": member_collection.name, "localField": "member_id", "foreignField": "member_id", "as": "member"}},
            {"$unwind": "$member"},
            {"$lookup": {"from": items_collection.name, "localField": "item_id", "foreignField": "item_id", "as": "library_item"}},
            {"$unwind": "$library_item"},
            {"$lookup": {"from": branches_collection.name, "localField": "branch_id", "foreignField": "branch_id", "as": "branch"}},
            {"$unwind": "$branch"},
        ])

        items_list = list(items)
        for r in items_list:
            r["_id"] = str(r["_id"])
            r["member"]["_id"] = str(r["member"].get("_id", ""))
            r["library_item"]["_id"] = str(r["library_item"].get("_id", ""))
            r["branch"]["_id"] = str(r["branch"].get("_id", ""))
        return {"status": "success", "data": items_list}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def get_reserved_items(member_id=None, branch_id=None, item_id=None):
    try:
        filter_query = {}
        if member_id:
            filter_query["member_id"] = member_id
        if branch_id:
            filter_query["branch_id"] = branch_id
        if item_id:
            filter_query["item_id"] = item_id

        reservations = reservations_collection.aggregate([
            {"$match": filter_query},
            {"$lookup": {"from": items_collection.name, "localField": "item_id", "foreignField": "item_id", "as": "library_item"}},
            {"$lookup": {"from": member_collection.name, "localField": "member_id", "foreignField": "member_id", "as": "member"}},
            {"$lookup": {"from": branches_collection.name, "localField": "branch_id", "foreignField": "branch_id", "as": "branch"}},
            {"$unwind": "$library_item"},
            {"$unwind": "$member"},
            {"$unwind": "$branch"},
            {"$lookup": {
                "from": copies_collection.name,
                "let": {"item_id": "$item_id", "branch_id": "$branch_id"},
                "pipeline": [
                    {"$match": {"$expr": {"$and": [
                        {"$eq": ["$item_id", "$$item_id"]},
                        {"$eq": ["$original_branch_id", "$$branch_id"]},
                        {"$eq": ["$status", ItemCopyStatus.AVAILABLE.value]}
                    ]}}}
                ],
                "as": "available_copies"
            }},
            {"$addFields": {"item_available": {"$gt": [{"$size": "$available_copies"}, 0]}}},
            {"$project": {
                "_id": 1,
                "image_filename": "$library_item.image_filename",
                "member_id": "$member.member_id",
                "member_name": {"$concat": ["$member.firstname", " ", "$member.lastname"]},
                "item_id": "$library_item.item_id",
                "item_title": "$library_item.title",
                "item_type": "$library_item.item_type",
                "branch_id": "$branch.branch_id",
                "branch_name": "$branch.name",
                "rfid": "$available_copies.rfid",
                "item_available": 1,
                "reservation_id": 1,
                "reserved_date": 1
            }}
        ])

        results = list(reservations)
        return {"status": "success", "data": results}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def get_notifications(member_id):
    try:
        notifications = notifications_collection.find({"member_id": member_id}).sort("date", -1)
        results = list(notifications)
        for n in results:
            n["_id"] = str(n["_id"])
        return {"status": "success", "data": results}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def delete_notification(id):
    try:
        notifications_collection.delete_one({"_id": ObjectId(id)})
        return {"status": "success", "message": "Deleted Successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}


def delete_reservation(id):
    try:
        reservations_collection.delete_one({"_id": ObjectId(id)})
        return {"status": "success", "message": "Deleted Successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error: {str(e)}"}
