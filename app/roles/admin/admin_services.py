from bson import ObjectId
from app.utils.database import db
from pymongo import errors, ReturnDocument
from werkzeug.security import generate_password_hash

from app.utils.enums import ItemCopyStatus, MemberStatus
from app.utils.collections import (
    branches_collection,
    staffs_collection,
    members_collection,
    items_collection,
    copies_collection,
)
from app.utils.init_roles import generate_staff_id


# add new staff
def staff_add_service(data):
    try:
        staff_id = generate_staff_id(db)

        staff_input = {
            "staff_id": str(staff_id),
            "firstname": data.get("firstname"),
            "lastname": data.get("lastname"),
            "email": data.get("email"),
            "mobile": data.get("mobile"),
            "ssn": data.get("ssn"),
            "location": data.get("location"),
            "dob": data.get("dob"),
            "password": generate_password_hash(data.get("password")),
            "role": "staff",
            "is_active": True,
        }

        # check if staff already created
        staff = staffs_collection.find_one({"staff_id": staff_id})
        if staff:
            return {
                "status": "fail",
                "message": f"Staff with id:{staff_id} already exist!",
            }

        staffs_collection.insert_one(staff_input)
        return {"status": "success", "message": "Staff added successfully!"}
    except errors.DuplicateKeyError:
        return {
            "status": "fail",
            "message": f"Staff id :{staff_input['staff_id']} already exist",
        }
    except Exception as e:
        return {
            "status": "fail",
            "message": f"Error adding staff: {str(e)}",
        }


# get all active staffs
def staff_get_all_service():
    try:
        staffs = staffs_collection.find({"is_active": True}).sort("_id", -1)
        return list(staffs)
    except Exception as e:
        print(e)
        return {
            "status": "fail",
            "message": f"Error fetching staffs",
        }


def staff_get(staff_id):
    try:
        staff = staffs_collection.find_one({"staff_id": staff_id, "is_active": True})
        if not staff:
            return {"status": "fail", "message": "Staff not found!"}

        del staff["password"]
        return {"status": "success", "data": staff}
    except Exception as e:
        return {"status": "fail", "message": f"Error fetching staff : {str(e)}"}


def staff_update(data, staff_id):
    try:
        updated_staff = {
            "firstname": data.get("firstname"),
            "lastname": data.get("lastname"),
            "email": data.get("email"),
            "mobile": data.get("mobile"),
            "ssn": data.get("ssn"),
            "location": data.get("location"),
            "dob": data.get("dob"),
        }

        # if data.get("password") != "":
        #     updated_staff["password"] = generate_password_hash(data.get("password"))

        staffs_collection.find_one_and_update(
            {"staff_id": staff_id}, {"$set": updated_staff}
        )
        return {"status": "success", "message": "Staff updated successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error updating staff: {str(e)}"}


def staff_set_inactive(staff_id):
    try:
        staffs_collection.find_one_and_update(
            {"staff_id": staff_id}, {"$set": {"is_active": False}}
        )
        return {"status": "success", "message": "Staff deleted successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error updating staff: {str(e)}"}


# add branch
def branch_add(data):
    try:
        staff_id = ObjectId(data.get("staff_id"))
        branch = {
            "branch_id": data.get("branch_id"),
            "staff_id": staff_id,
            "name": data.get("name"),
            "location": data.get("location"),
            "is_active": True,
        }

        # Get the old branch of the staff, if any
        old_branch = branches_collection.find_one({"staff_id": staff_id})
        if old_branch:
            # Remove staff from the old branch, if exists
            branches_collection.update_one(
                {"_id": ObjectId(old_branch._id)}, {"$unset": {"staff_id": None}}
            )

        branch_id = branches_collection.insert_one(branch).inserted_id

        # update branch id in staff collection
        staffs_collection.update_one(
            {"_id": staff_id}, {"$set": {"branch_id": ObjectId(branch_id)}}
        )

        return {"status": "success", "message": "Branch added successfully!"}
    except errors.DuplicateKeyError:
        return {
            "status": "fail",
            "message": f"Branch name or id already exist",
            "data": branch,
        }
    except Exception as e:
        return {
            "status": "fail",
            "message": f"Error adding branch: {str(e)}",
            "data": branch,
        }


# update branch by id
def branch_update(data, branch_id):
    try:
        staff_id = ObjectId(data.get("staff_id"))
        updated_branch = {
            "branch_id": data.get("branch_id"),
            "staff_id": staff_id,
            "name": data.get("name"),
            "location": data.get("location"),
        }

        staff = staffs_collection.find_one({"_id": staff_id})
        old_branch = branches_collection.find_one({"branch_id": branch_id})

        # Remove staff from the old branch, if exists
        if old_branch.get("staff_id"):
            staffs_collection.update_one(
                {"_id": ObjectId(old_branch["staff_id"])}, {"$unset": {"branch_id": ""}}
            )
        # Remove old branch reference from staff
        if staff.get("branch_id"):
            branches_collection.update_one(
                {"_id": ObjectId(staff["branch_id"])}, {"$unset": {"staff_id": ""}}
            )

        branch = branches_collection.find_one_and_update(
            {"branch_id": branch_id},
            {"$set": updated_branch},
            return_document=ReturnDocument.AFTER,
        )
        # update branch id in staff collection
        staffs_collection.update_one(
            {"_id": staff_id}, {"$set": {"branch_id": ObjectId(branch["_id"])}}
        )
        return {"status": "success", "message": "Branch updated successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error updating branch: {str(e)}"}


# get all branches
def branch_get_all():
    try:
        branches = branches_collection.aggregate(
            [
                {"$match": {"is_active": True}},
                {
                    "$lookup": {
                        "from": staffs_collection.name,
                        "localField": "staff_id",
                        "foreignField": "_id",
                        "as": "staff",
                    }
                },
                # {"$unwind": "$staff"},
                {"$sort": {"_id": -1}},
            ]
        )
        return list(branches)
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching branches"}


# get branch by branch id
def branch_get(branch_id):
    try:
        branch = branches_collection.find_one(
            {"branch_id": branch_id, "is_active": True}
        )
        if not branch:
            return {"status": "fail", "message": "Branch not found!"}

        return {"status": "success", "data": branch}
    except Exception as e:
        return {"status": "fail", "message": f"Error fetching branch : {str(e)}"}


# set branch active status to false
def branch_set_inactive(branch_id):
    try:
        branches_collection.find_one_and_update(
            {"branch_id": branch_id}, {"$set": {"is_active": False}}
        )
        return {"status": "success", "message": "Staff deleted successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error deleting branch: {str(e)}"}


# get member pending for approval
def members_get_all_by_status(status):
    try:
        members = members_collection.find({"status": status}).sort("created_at", -1)
        return {"status": "success", "data": members}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching members: {str(e)}"}


def members_update_by_status(data):
    try:
        member_id = ObjectId(data.get("member_id"))
        status = data.get("update_status_to")
        members_collection.find_one_and_update(
            {"_id": member_id}, {"$set": {"status": status}}
        )
        return {"status": "success", "message": f"Member {status} successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error updating member: {str(e)}"}


def member_delete(member_id):
    member_id = ObjectId(member_id)

    try:
        members_collection.update_one({})
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error deleting member: {str(e)}"}


def delete_library_item(item_id):
    item_id = ObjectId(item_id)

    item = items_collection.find_one({"_id": item_id, "is_active": True})
    if not item:
        return {
            "status": "fail",
            "message": "Sorry, this item is already deleted",
        }

    if item["available_copies"] != item["total_copies"]:
        return {
            "status": "fail",
            "message": "Sorry, this item is either borrowed or in transit, so it cannot be deleted",
        }

    # update copies status to deleted
    copies_collection.update_many(
        {"item_id": item_id}, {"$set": {"status": ItemCopyStatus.DELETED.value}}
    )
    # update item status to deleted
    items_collection.update_one(
        {"_id": item_id},
        {"$set": {"is_active": False, "total_copies": 0, "available_copies": 0}},
    )
    return {
        "status": "success",
        "message": "This item deleted successfully",
    }


def delete_branch_service(branch_id):
    branch_id = ObjectId(branch_id)

    try:
        branch = branches_collection.find_one({"_id": branch_id, "is_active": True})
        if not branch:
            return {
                "status": "fail",
                "message": "Branch not found",
            }

        copies = list(
            copies_collection.find(
                {
                    "original_branch_id": branch_id,
                    "status": {
                        "$nin": [
                            ItemCopyStatus.AVAILABLE.value,
                            ItemCopyStatus.DELETED.value,
                        ]
                    },
                }
            )
        )
        if copies:
            return {
                "status": "fail",
                "message": "Sorry, items in this branch is either borrowed or in transit, so it cannot be deleted",
            }

        # get item id and total_copies for this branch
        result = copies_collection.aggregate(
            [
                {"$match": {"original_branch_id": branch_id}},
                {
                    "$group": {
                        "_id": "$item_id",  # Group by item_id
                        "total_copies": {
                            "$sum": 1
                        },  # Count the number of copies for each item_id
                    }
                },
                {
                    "$project": {
                        "item_id": "$_id",  # Rename _id to item_id
                        "_id": 0,  # Exclude _id field
                        "total_copies": 1,
                    }
                },
            ]
        )

        # update vailable copies in library items
        for item in result:
            items_collection.update_one(
                {"_id": ObjectId(item["item_id"])},
                {
                    "$inc": {
                        "total_copies": -item["total_copies"],
                        "available_copies": -item["total_copies"],
                    }
                },
            )

        copies_collection.update_many(
            {"original_branch_id": branch_id},
            {"$set": {"status": ItemCopyStatus.DELETED.value}},
        )

        # delete branch
        branches_collection.update_one(
            {"_id": branch_id},
            {
                "$set": {"is_active": False, "branch_id": None},
                "$unset": {"staff_id": None},
            },
        )

        return {
            "status": "success",
            "message": "Branch deleted successfully",
        }
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error : {str(e)}"}
