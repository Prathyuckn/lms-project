from datetime import datetime
from bson import ObjectId

from app.utils.enums import ItemCopyStatus
from app.utils.remove_file_util import remove_file_util
from app.utils.upload_file import upload_file_util
from app.utils.convert_string_toArray import convert_string_to_array
from app.utils.database import db
from pymongo import errors
from app.utils.collections import items_collection, copies_collection, types_collection


def get_all_library_items(type):
    try:
        items = items_collection.find({"item_type": type, "is_active": True}).sort(
            "_id", -1
        )
        return {"status": "success", "data": list(items)}
    except Exception as e:
        print(e)
        return {
            "status": "fail",
            "message": f"Error fetching library item types",
        }


def get_library_items_by_type(item_type, branch_id):
    try:
        branch_id = ObjectId(branch_id)
        # Fetch library items by item_type
        items_aggregation = items_collection.aggregate(
            [
                {"$match": {"item_type": item_type}},  # Filter by item_type
                {
                    "$lookup": {
                        "from": copies_collection.name,
                        "let": {"item_id": "$_id"},
                        "pipeline": [
                            {
                                "$match": {"$expr": {"$eq": ["$item_id", "$$item_id"]}}
                            },  # Match copies for this item
                            {
                                "$match": {"original_branch_id": branch_id}
                            },  # Filter by branch_id
                        ],
                        "as": "branch_copies",
                    }
                },
                {
                    "$addFields": {
                        "total_copies": {"$size": "$branch_copies"},
                        "available_copies": {
                            "$size": {
                                "$filter": {
                                    "input": "$branch_copies",
                                    "as": "copy",
                                    "cond": {"$eq": ["$$copy.status", "available"]},
                                }
                            }
                        },
                    }
                },
                {
                    "$match": {
                        "total_copies": {"$gt": 0}
                    }  # Ensure branch has at least one copy
                },
                {
                    "$project": {
                        "_id": 1,  # Exclude the internal MongoDB ID
                        "image_filename": 1,
                        "id": 1,
                        "title": 1,
                        "availability_type": 1,
                        "categories": 1,
                        "item_type": 1,
                        "total_copies": 1,
                        "available_copies": 1,
                    }
                },
            ]
        )

        # Convert the aggregation result to a list
        items = list(items_aggregation)

        return {
            "status": "success",
            "data": items,
        }
    except Exception as e:
        print(e)
        return {
            "status": "fail",
            "message": f"Error fetching library item types",
        }


# get library item by id
def library_item_get(item_id):
    try:
        item = items_collection.find_one({"_id": ObjectId(item_id), "is_active": True})
        if not item:
            return {"status": "fail", "message": "Library item not found"}
        return {"status": "success", "data": item}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": "Library item not found"}


# get item details with copies count branch wise
def library_item_details_with_copies_count_branchwise(item_id):
    try:
        item_id = ObjectId(item_id)
        item = items_collection.find_one({"_id": item_id, "is_active": True})
        if not item:
            return {"status": "fail", "message": "Library item not found"}
        # Step 2: Aggregate copies by branch for the given item_id
        copies_aggregation = copies_collection.aggregate(
            [
                {"$match": {"item_id": item_id}},
                {
                    "$group": {
                        "_id": "$original_branch_id",
                        "total_copies": {"$sum": 1},
                        "available_copies": {
                            "$sum": {"$cond": [{"$eq": ["$status", "available"]}, 1, 0]}
                        },
                    }
                },
                {
                    "$lookup": {
                        "from": "branches",
                        "localField": "_id",
                        "foreignField": "_id",
                        "as": "branch_details",
                    }
                },
                {
                    "$unwind": {
                        "path": "$branch_details",
                        "preserveNullAndEmptyArrays": True,
                    }
                },
                {
                    "$project": {
                        "_id": 0,
                        "branch_id": "$_id",
                        "total_copies": 1,
                        "available_copies": 1,
                        "branch_name": "$branch_details.name",
                        # "branch_name": {"$arrayElemAt": ["$branch_details.name", 0]},
                    }
                },
            ]
        )

        copies_details = list(copies_aggregation)
        return {
            "status": "success",
            "item": item,
            "copies": copies_details or "No copies available.",
        }

    except Exception as e:
        print(e)
        return {"status": "fail", "message": "Error fetching library item"}


# add new library item
def library_item_add(data, files, type):
    try:
        item_id = data["id"].upper()

        # check item already exist
        exiting_item = items_collection.find_one({"id": item_id})
        if exiting_item:
            return {
                "status": "fail",
                "message": f"This item id {item_id} already exist",
            }

        image_file = files["image"]

        # upload and move image to folder
        upload_folder = f"{type}s"
        allowed_extensions = {"png", "jpg", "jpeg"}
        error, filename = upload_file_util(
            image_file, upload_folder, allowed_extensions
        )

        if error:
            return {"status": "fail", "message": f"Error : {error}"}

        # check if digital file exist
        if "digital_file" in files:
            digital_file = files["digital_file"]
            # move uploaded digital file
            upload_folder = f"{type}s"
            allowed_extensions = {"pdf", "txt"}
            error, digital_filename = upload_file_util(
                digital_file, upload_folder, allowed_extensions
            )

            if error:
                return {"status": "fail", "message": f"Error : {error}"}

        item = {key: value for key, value in data.items()}

        item["id"] = item["id"].upper()
        item["categories"] = convert_string_to_array(item["categories"])
        item["image_filename"] = filename
        if "digital_file" in files:
            item["digital_filename"] = digital_filename
        item["total_copies"] = 0
        item["available_copies"] = 0
        item["created_at"] = datetime.now()
        item["is_active"] = True

        items_collection.insert_one(item)
        return {
            "status": "success",
            "message": "Library item added successfully",
        }
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error adding item : {str(e)}"}


# update existing library item
def library_item_update(item_id, data, files, type):
    try:
        image_file = files["image"]
        if "digital_file" in files:
            digital_file = files["digital_file"]

        item = {key: value for key, value in data.items()}

        filename = old_filename = item["image_filename"]
        if "digital_filename" in item:
            digital_filename = old_digital_filename = item["digital_filename"]

        if image_file:
            # upload and move image to folder
            upload_folder = f"{type}s"
            allowed_extensions = {"png", "jpg", "jpeg"}
            error, filename = upload_file_util(
                image_file, upload_folder, allowed_extensions
            )

            if error:
                return {"status": "fail", "message": f"Error : {error}"}
            remove_file_util(upload_folder, old_filename)

        if "digital_file" in files and files["digital_file"].filename != "":
            digital_file = files["digital_file"]
            # move uploaded file
            upload_folder = f"{type}s"
            allowed_extensions = {"pdf", "txt"}
            error, digital_filename = upload_file_util(
                digital_file, upload_folder, allowed_extensions
            )

            if error:
                return {"status": "fail", "message": f"Error : {error}"}
            remove_file_util(upload_folder, old_digital_filename)

        item["id"] = item["id"].upper()
        item["categories"] = convert_string_to_array(item["categories"])
        item["image_filename"] = filename
        if "digital_file" in files:
            item["digital_filename"] = digital_filename

        items_collection.find_one_and_update({"_id": ObjectId(item_id)}, {"$set": item})
        return {
            "status": "success",
            "message": "Library item updated successfully",
        }
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error updating item : {str(e)}"}
