from datetime import datetime
import uuid
from bson import ObjectId
from flask_login import current_user

from app.utils.enums import ItemCopyStatus
from app.utils.remove_file_util import remove_file_util
from app.utils.upload_file import upload_file_util
from app.utils.convert_string_toArray import convert_string_to_array
from app.utils.database import db
from pymongo import errors

copies_collection = db.get_collection("copies")
items_collection = db.get_collection("library_items")
branches_collection = db.get_collection("branches")
members_collection = db.get_collection("member")


# get copies of library item by item_id
def copies_getby_itemId(item_id):
    try:
        filter = {
            "item_id": ObjectId(item_id),
            "status": {"$ne": ItemCopyStatus.DELETED.value},
        }

        if current_user.role == "staff":
            filter["original_branch_id"] = ObjectId(current_user.branch_id)

        copies = copies_collection.aggregate(
            [
                {"$match": filter},
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "original_branch_id",
                        "foreignField": "_id",
                        "as": "original_branch",
                    }
                },
                {"$unwind": "$original_branch"},
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "current_branch_id",
                        "foreignField": "_id",
                        "as": "current_branch",
                    }
                },
                {"$unwind": "$current_branch"},
                {
                    "$lookup": {
                        "from": members_collection.name,
                        "localField": "borrower_id",
                        "foreignField": "_id",
                        "as": "borrower",
                    }
                },
                {"$unwind": {"path": "$borrower", "preserveNullAndEmptyArrays": True}},
                {"$sort": {"original_branch_id": 1}},
            ]
        )
        return {"status": "success", "data": list(copies)}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching copies : {str(e)}"}


# get copy by copy id(_id)
def library_item_copy_get(copy_id):
    try:
        # copy = copies_collection.find_one(
        #     {"_id": ObjectId(id), "status": {"$ne": ItemCopyStatus.DELETED.value}}
        # )
        copies = copies_collection.aggregate(
            [
                {
                    "$match": {
                        "_id": ObjectId(copy_id),
                        "status": {"$ne": ItemCopyStatus.DELETED.value},
                    }
                },
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "original_branch_id",
                        "foreignField": "_id",
                        "as": "original_branch",
                    }
                },
                {"$unwind": "$original_branch"},
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "current_branch_id",
                        "foreignField": "_id",
                        "as": "current_branch",
                    }
                },
                {"$unwind": "$current_branch"},
                {
                    "$lookup": {
                        "from": members_collection.name,
                        "localField": "borrower_id",
                        "foreignField": "_id",
                        "as": "borrower",
                    }
                },
                {"$unwind": {"path": "$borrower", "preserveNullAndEmptyArrays": True}},
            ]
        )

        copies = list(copies)
        copy = copies[0]

        if not copy:
            return {"status": "fail", "message": "Copy not found"}

        return {"status": "success", "data": copy}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching copy : {str(e)}"}


def get_available_copies_by_branch(branch_id):
    copies = copies_collection.aggregate(
        [
            {
                "$match": {
                    "original_branch_id": ObjectId(branch_id),
                    "status": ItemCopyStatus.AVAILABLE.value,
                }
            },
            {
                "$lookup": {
                    "from": items_collection.name,
                    "localField": "item_id",
                    "foreignField": "_id",
                    "as": "library_item",
                }
            },
            {"$unwind": "$library_item"},
            {"$sort": {"item_id": 1}},
        ]
    )

    return {"status": "success", "data": list(copies)}


def get_copy_item_by_rfid(rfid, branch_id):
    try:
        copies = copies_collection.aggregate(
            [
                {
                    "$match": {
                        "rfid": rfid.upper(),
                        "original_branch_id": ObjectId(branch_id),
                        "status": {"$ne": ItemCopyStatus.DELETED.value},
                    }
                },
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "original_branch_id",
                        "foreignField": "_id",
                        "as": "original_branch",
                    }
                },
                {"$unwind": "$original_branch"},
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "current_branch_id",
                        "foreignField": "_id",
                        "as": "current_branch",
                    }
                },
                {"$unwind": "$current_branch"},
                {
                    "$lookup": {
                        "from": items_collection.name,
                        "localField": "item_id",
                        "foreignField": "_id",
                        "as": "item",
                    }
                },
                {"$unwind": {"path": "$item", "preserveNullAndEmptyArrays": True}},
            ]
        )

        copies = list(copies)
        if not copies:
            return {"status": "fail", "message": "Item could not be found"}
        copy = copies[0]

        if copy["status"] == ItemCopyStatus.AVAILABLE.value:
            return {"status": "success", "data": copy}

        elif copy["status"] == ItemCopyStatus.BORROWED.value:
            return {
                "status": "fail",
                "message": "The item is already borrowed and not available",
            }

        elif copy["status"] == ItemCopyStatus.AT_OTHER_BRANCH.value:
            return {
                "status": "fail",
                "message": "This item is available at another branch.",
            }
        else:
            return {
                "status": "fail",
                "message": "This item is currently unavailable.",
            }

    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching copy : {str(e)}"}


def library_item_copy_add(data):
    try:
        item_id = ObjectId(data.get("item_id"))
        copy = {
            "item_id": item_id,
            "rfid": data.get("rfid"),
            "original_branch_id": ObjectId(data.get("branch_id")),
            "current_branch_id": ObjectId(data.get("branch_id")),
            "borrower_id": None,
            "status": ItemCopyStatus.AVAILABLE.value,
            "created_at": datetime.now(),
        }
        copies_collection.insert_one(copy)
        # increase total copies & available copies value to 1
        items_collection.update_one(
            {"_id": item_id}, {"$inc": {"total_copies": 1, "available_copies": 1}}
        )
        return {"status": "success", "message": "Copy created successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error inserting copy : {str(e)}"}


def library_item_copy_update(data, id):
    try:
        copy_data = {
            "item_id": ObjectId(data.get("item_id")),
            "copy_id": data.get("copy_id"),
            "original_branch_id": ObjectId(data.get("branch_id")),
            "current_branch_id": ObjectId(data.get("branch_id")),
            "updated_at": datetime.now(),
        }
        # check if copy is available in branch
        copy = copies_collection.find_one(
            {"_id": ObjectId(id), "status": ItemCopyStatus.AVAILABLE.value}
        )
        if not copy:
            return {
                "status": "fail",
                "message": "Copy not available in branch, cannot be updated",
            }

        copies_collection.find_one_and_update(
            {"_id": ObjectId(id)}, {"$set": copy_data}
        )
        return {"status": "success", "message": "Copy updated successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error updating copy : {str(e)}"}
