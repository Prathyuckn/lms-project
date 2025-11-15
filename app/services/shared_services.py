from datetime import datetime, timedelta
from bson import ObjectId

from app.roles.member.member_services import get_member_with_borrowed_items
from app.services.library_items_copy_services import (
    get_available_copies_by_branch,
    get_copy_item_by_rfid,
)
from app.utils.enums import (
    ItemCopyStatus,
    MemberStatus,
    TransactionType,
    TransferStatus,
)
from app.utils.remove_file_util import remove_file_util
from app.utils.upload_file import upload_file_util
from app.utils.convert_string_toArray import convert_string_to_array
from app.utils.database import db
from app.utils.collections import (
    branches_collection,
    borrowed_collection,
    copies_collection,
    items_collection,
    members_collection,
    notifications_collection,
    reservations_collection,
    transactions_collection,
    transfers_collection,
)
from pymongo import errors


def create_transaction(values):
    insert_data = {
        "transaction_id": f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "transaction_date": datetime.now(),
        "status": "active",
    }
    insert_data.update(values)
    transactions_collection.insert_one(insert_data)


def calculate_fees_and_update():
    late_fee_per_day = 0.50  # Late fee per day in dollars

    # Fetch all borrowed items that are not returned
    borrowed_items = borrowed_collection.find({"returned": False})
    # print(list(borrowed_items))
    total_due_per_member = {}

    for item in borrowed_items:
        borrow_id = ObjectId(item["_id"])
        member_id = ObjectId(item["member_id"])
        due_date = item["due_date"]
        borrowed_on = item["borrowed_on"]

        # Calculate delayed days
        today = datetime.now()
        delayed_days = (today - due_date).days if today > due_date else 0
        late_fee = delayed_days * late_fee_per_day

        # Update the borrowed item with delayed_days and late_fee
        borrowed_collection.update_one(
            {"_id": borrow_id},
            {"$set": {"delayed_days": delayed_days, "late_fee": late_fee}},
        )

        # Accumulate the total late fee per member
        if member_id not in total_due_per_member:
            total_due_per_member[member_id] = 0
        total_due_per_member[member_id] += late_fee

    # Update the members collection with total due amount
    for member_id, total_due in total_due_per_member.items():
        members_collection.update_one(
            {"_id": member_id}, {"$set": {"due_amount": total_due}}
        )

    return {
        "status": "success",
        "message": "Late fees and total dues updated successfully",
    }


# def filter_checkout(member_id, rfid, branch_id):
#     member = None
#     if member_id:
#         member_resp = get_member_with_borrowed_items(member_id)
#         if member_resp["status"] == "fail":
#             return member_resp
#         member = member_resp["data"]

#     copy = None
#     if rfid and branch_id:
#         copy_resp = get_copy_item_by_rfid(rfid, branch_id)
#         if copy_resp["status"] == "fail":
#             return copy_resp
#         else:
#             copy = copy_resp["data"]

#     data = {"member": member, "copy": copy}
#     return {"status": "success", "data": data}


def filter_checkout(member_id, branch_id):
    member = None
    if member_id:
        member_resp = get_member_with_borrowed_items(member_id)
        if member_resp["status"] == "fail":
            return member_resp
        member = member_resp["data"]

    copies = None
    if branch_id:
        copy_resp = get_available_copies_by_branch(branch_id)
        if copy_resp["status"] == "fail":
            return copy_resp
        else:
            copies = copy_resp["data"]

    data = {"member": member, "copies": copies}
    return {"status": "success", "data": data}


def checkout(member_id, rfid_list):
    try:
        member = members_collection.find_one(
            {"member_id": member_id.upper(), "status": MemberStatus.APPROVED.value}
        )

        if not member:
            return {"status": "fail", "message": "Member not found"}

        due_date = datetime.now() + timedelta(days=21)  # 3 weeks borrowing period
        member_id = ObjectId(member["_id"])

        for rfid in rfid_list:
            copy = copies_collection.find_one({"rfid": rfid})
            item_id = ObjectId(copy["item_id"])

            item = items_collection.find_one({"_id": item_id})

            # add the member borrowed items
            borrowed_collection.insert_one(
                {
                    "member_id": member_id,
                    "item_id": item_id,
                    "item_type": item["item_type"],
                    "copy_id": ObjectId(copy["_id"]),
                    "branch_id": ObjectId(copy["original_branch_id"]),
                    "rfid": copy["rfid"],
                    "borrowed_on": datetime.now(),
                    "due_date": due_date,
                    "delayed_days": 0,
                    "late_fee": 0,
                    "renewals_left": 2,
                    "returned": False,
                    "return_date": None,
                }
            )

            # add tranctions
            transaction_data = {
                "member_id": member_id,
                "item_id": item_id,
                "copy_id": ObjectId(copy["_id"]),
                "transaction_type": TransactionType.BORROW.value,
                "borrow_branch_id": ObjectId(copy["original_branch_id"]),
                "due_date": due_date,
            }
            create_transaction(transaction_data)

            # Mark the copy as borrowed, update borrower_id
            copies_collection.update_one(
                {"_id": ObjectId(copy["_id"])},
                {
                    "$set": {
                        "borrower_id": member_id,
                        "status": ItemCopyStatus.BORROWED.value,
                    }
                },
            )

            # decrease total available copies
            items_collection.update_one(
                {"_id": item_id},
                {"$inc": {"available_copies": -1}},
            )

            # check reservation by item and member if available delete reservation
            reservations_collection.delete_one(
                {"item_id": item_id, "member_id": member_id}
            )

        return {"status": "success", "message": "Item borrowed successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching copy : {str(e)}"}


# def checkout(member_id, rfid):
#     try:
#         member = members_collection.find_one(
#             {"member_id": member_id.upper(), "status": MemberStatus.APPROVED.value}
#         )

#         if not member:
#             return {"status": "fail", "message": "Member not found"}

#         copy = copies_collection.find_one(
#             {"rfid": rfid.upper(), "status": ItemCopyStatus.AVAILABLE.value}
#         )

#         if not copy:
#             return {"status": "fail", "message": "Copy not found"}

#         member_id = ObjectId(member["_id"])
#         item_id = ObjectId(copy["item_id"])

#         # check if member already borrowed this item and yet to return
#         is_borrowed = (
#             borrowed_collection.count_documents(
#                 {"member_id": member_id, "item_id": item_id, "returned": False}
#             )
#             > 0
#         )

#         if is_borrowed:
#             return {
#                 "status": "fail",
#                 "message": "The member has already borrowed this item and has not yet returned it.",
#             }

#         item = items_collection.find_one({"_id": item_id})

#         due_date = datetime.now() + timedelta(days=21)  # 3 weeks borrowing period

#         # add the member borrowed items
#         borrowed_collection.insert_one(
#             {
#                 "member_id": member_id,
#                 "item_id": item_id,
#                 "item_type": item["item_type"],
#                 "copy_id": ObjectId(copy["_id"]),
#                 "branch_id": ObjectId(copy["original_branch_id"]),
#                 "rfid": copy["rfid"],
#                 "borrowed_on": datetime.now(),
#                 "due_date": due_date,
#                 "delayed_days": 0,
#                 "late_fee": 0,
#                 "renewals_left": 2,
#                 "returned": False,
#                 "return_date": None,
#             }
#         )

#         # add tranctions
#         transaction_data = {
#             "member_id": member_id,
#             "item_id": item_id,
#             "copy_id": ObjectId(copy["_id"]),
#             "transaction_type": TransactionType.BORROW.value,
#             "borrow_branch_id": ObjectId(copy["original_branch_id"]),
#             "due_date": due_date,
#         }
#         create_transaction(transaction_data)

#         # Mark the copy as borrowed, update borrower_id
#         copies_collection.update_one(
#             {"_id": ObjectId(copy["_id"])},
#             {
#                 "$set": {
#                     "borrower_id": member_id,
#                     "status": ItemCopyStatus.BORROWED.value,
#                 }
#             },
#         )
#         # decrease total available copies
#         items_collection.update_one(
#             {"_id": item_id},
#             {"$inc": {"available_copies": -1}},
#         )

#         # check reservation by item and member if available delete reservation
#         reservations_collection.delete_one({"item_id": item_id, "member_id": member_id})

#         return {"status": "success", "message": "Item borrowed successfully"}
#     except Exception as e:
#         print(e)
#         return {"status": "fail", "message": f"Error fetching copy : {str(e)}"}


def return_borrowed_item(copy_id, return_branch_id=None):
    # Find the borrowed item based on the copy_id
    copy_id = ObjectId(copy_id)

    borrowed_item = borrowed_collection.find_one(
        {"copy_id": copy_id, "returned": False}
    )
    if not borrowed_item:
        return {
            "status": "error",
            "message": "Borrowed item not found or already returned.",
        }

    member_id = ObjectId(borrowed_item["member_id"])
    item_id = ObjectId(borrowed_item["item_id"])
    late_fee = borrowed_item.get("late_fee", 0.0)
    original_branch_id = ObjectId(borrowed_item["branch_id"])

    if return_branch_id:
        return_branch_id = ObjectId(return_branch_id)
    else:
        return_branch_id = ObjectId(borrowed_item["branch_id"])

    # Update the borrowed item to mark it as returned
    borrowed_collection.update_one(
        {"_id": borrowed_item["_id"]},
        {"$set": {"returned": True, "return_date": datetime.now()}},
    )

    # Update the copy status in the copies collection
    copy_update = {
        "status": ItemCopyStatus.AVAILABLE.value,
        "borrower_id": None,
    }
    if return_branch_id != original_branch_id:
        copy_update["status"] = ItemCopyStatus.AT_OTHER_BRANCH.value
        copy_update["current_branch_id"] = return_branch_id  # Track the current branch

        # Create a transfer record
        transfer = {
            "copy_id": copy_id,
            "item_id": item_id,
            "from_branch": return_branch_id,
            "to_branch": original_branch_id,
            "transfer_date": datetime.now(),
            "status": TransferStatus.PENDING.value,
        }
        transfers_collection.insert_one(transfer)
    else:
        # Check for reservations for this item in the branch
        reservation = reservations_collection.find_one(
            {
                "item_id": item_id,
                "branch_id": original_branch_id,
            }
        )

        item = items_collection.find_one({"_id": ObjectId(item_id)})
        if reservation:

            # Create a notification for the member
            notification = {
                "notification_id": f"NTF{notifications_collection.count_documents({}) + 1:04d}",
                "member_id": reservation["member_id"],
                "message": f"The item '{item['title']}' you reserved is now available at branch.",
                "date": datetime.now(),
                "status": "unread",
            }
            notifications_collection.insert_one(notification)

            # Update reservation status
            reservations_collection.update_one(
                {"_id": ObjectId(reservation["_id"])},
                {"$set": {"status": "notified"}},
            )

    copies_collection.update_one({"_id": copy_id}, {"$set": copy_update})

    # Create a transaction record for the return
    transaction_date = {
        "member_id": member_id,
        "item_id": item_id,
        "copy_id": copy_id,
        "transaction_type": "returned",
        "paid_amount": late_fee,  # Add the late fee as paid amount
        "return_branch_id": return_branch_id,
    }
    create_transaction(transaction_date)

    # Increment available copies in the library_items collection
    items_collection.update_one({"_id": item_id}, {"$inc": {"available_copies": 1}})

    return {
        "status": "success",
        "message": f"Item returned successfully.",
    }


def filter_copies_by_rfid(rfid):
    try:
        copies = copies_collection.aggregate(
            [
                {"$match": {"rfid": rfid}},
                {
                    "$lookup": {
                        "from": items_collection.name,
                        "localField": "item_id",
                        "foreignField": "_id",
                        "as": "library_item",
                    }
                },
                {"$unwind": "$library_item"},
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
                        "as": "member",
                    }
                },
                {"$unwind": {"path": "$member", "preserveNullAndEmptyArrays": True}},
                {
                    "$lookup": {
                        "from": borrowed_collection.name,
                        "localField": "_id",
                        "foreignField": "copy_id",
                        "pipeline": [
                            {"$match": {"returned": False}},
                        ],
                        "as": "borrowed",
                    }
                },
                {"$unwind": {"path": "$borrowed", "preserveNullAndEmptyArrays": True}},
                {"$sort": {"original_branch_id": 1}},
            ]
        )
        copies = list(copies)
        copy = copies[0]
        return {"status": "success", "data": copy}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching copy : {str(e)}"}


def get_all_transactions(branch_id=None, member_id=None):
    filter = {}
    sort = {"transaction_date": -1}
    if branch_id:
        branch_id = ObjectId(branch_id)
        filter = {
            "$or": [{"borrow_branch_id": branch_id}, {"return_branch_id": branch_id}]
        }
    if member_id:
        member_id = ObjectId(member_id)
        filter["member_id"] = member_id

    result = transactions_collection.aggregate(
        [
            {"$match": filter},
            {
                "$lookup": {
                    "from": members_collection.name,
                    "localField": "member_id",
                    "foreignField": "_id",
                    "as": "member",
                }
            },
            {"$unwind": "$member"},
            {
                "$lookup": {
                    "from": items_collection.name,
                    "localField": "item_id",
                    "foreignField": "_id",
                    "as": "library_item",
                }
            },
            {"$unwind": "$library_item"},
            {
                "$lookup": {
                    "from": copies_collection.name,
                    "localField": "copy_id",
                    "foreignField": "_id",
                    "as": "copy",
                }
            },
            {"$unwind": "$copy"},
            {
                "$lookup": {
                    "from": "branches",
                    "let": {
                        "borrow_branch_id": "$borrow_branch_id",
                        "return_branch_id": "$return_branch_id",
                    },
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$or": [
                                        {"$eq": ["$_id", "$$borrow_branch_id"]},
                                        {"$eq": ["$_id", "$$return_branch_id"]},
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "branch_details",
                }
            },
            {"$unwind": "$copy"},
            {"$sort": sort},
        ]
    )
    return list(result)


# delete a copy
def delete_copy(id):
    id = ObjectId(id)
    try:
        copy = copies_collection.find_one(
            {"_id": id, "status": ItemCopyStatus.AVAILABLE.value}
        )
        if not copy:
            return {
                "status": "fail",
                "message": f"This copy is not currently available at this branch and therefore cannot be deleted.",
            }
        copies_collection.update_one(
            {"_id": id}, {"$set": {"status": ItemCopyStatus.DELETED.value}}
        )
        # update total copies and available copies in item
        items_collection.update_one(
            {"_id": ObjectId(copy["item_id"])},
            {"$inc": {"total_copies": -1, "available_copies": -1}},
        )

        return {"status": "success", "message": "Copy removed successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Message : {str(e)}"}
