from datetime import datetime, timedelta
from bson import ObjectId
from app.utils.enums import ItemCopyStatus, TransferStatus
from app.utils.collections import (
    transfers_collection,
    items_collection,
    copies_collection,
    branches_collection,
)


def transfer_items_list(branch_id=None, status=None):
    try:
        match_filter = {"status": TransferStatus.PENDING.value}
        if branch_id:
            branch_id = ObjectId(branch_id)
            match_filter["from_branch"] = branch_id
        if status:
            match_filter["status"] = status

        items = transfers_collection.aggregate(
            [
                {"$match": match_filter},
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
                        "from": branches_collection.name,
                        "localField": "from_branch",
                        "foreignField": "_id",
                        "as": "from_branch",
                    }
                },
                {"$unwind": "$from_branch"},
                {
                    "$lookup": {
                        "from": branches_collection.name,
                        "localField": "to_branch",
                        "foreignField": "_id",
                        "as": "to_branch",
                    }
                },
                {"$unwind": "$to_branch"},
            ]
        )
        return {"status": "success", "data": list(items)}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error fetching transfer list : {str(e)}"}


def initiate_transfer(transfer_id, copy_id):
    try:
        transfer_id = ObjectId(transfer_id)
        transfer = transfers_collection.find_one(
            {"_id": transfer_id, "status": TransferStatus.PENDING.value}
        )
        if not transfer:
            return {"status": "fail", "message": "No transfer found"}

        copy_id = ObjectId(copy_id)
        copy = copies_collection.find_one(
            {"_id": copy_id, "status": ItemCopyStatus.AT_OTHER_BRANCH.value}
        )
        if not copy:
            return {"status": "fail", "message": "Copy not found"}
        # update status in transfer collection
        result = transfers_collection.update_one(
            {"_id": transfer_id},
            {
                "$set": {
                    "status": TransferStatus.IN_TRANSIT.value,
                    "initiated_on": datetime.now(),
                }
            },
        )
        if result.modified_count > 0:
            # update status in copies collection
            copies_collection.update_one(
                {"_id": copy_id}, {"$set": {"status": ItemCopyStatus.IN_TRANSIT.value}}
            )
            return {
                "status": "success",
                "message": "Item transfer initiated successfully",
            }
        else:
            return {"status": "fail", "message": "Item transfer initiated successfully"}
    except Exception as e:
        print(e)
        return {"status": "fail", "message": f"Error transfering item : {str(e)}"}


def update_transfer_status():
    # Get the current time
    current_time = datetime.now()
    # Find transfers that are older than 24 hours and still active
    expired_transfers = transfers_collection.find(
        {
            "status": TransferStatus.IN_TRANSIT.value,
            "initiated_on": {"$lt": (current_time - timedelta(hours=24))},
        }
    )

    for transfer in expired_transfers:

        transfer_id = ObjectId(transfer["_id"])
        copy_id = ObjectId(transfer["copy_id"])
        original_branch_id = ObjectId(transfer["to_branch"])

        # Update transfer status to "completed" in the transfer collection
        transfers_collection.update_one(
            {"_id": transfer_id},
            {
                "$set": {
                    "status": TransferStatus.COMPLETED.value,
                    "completed_on": current_time,
                }
            },
        )

        # Update copy status to "available" in the copies collection and reset its current branch
        copies_collection.update_one(
            {"_id": copy_id},
            {
                "$set": {
                    "status": ItemCopyStatus.AVAILABLE.value,
                    "current_branch_id": original_branch_id,
                }
            },
        )
