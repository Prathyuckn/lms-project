from werkzeug.security import generate_password_hash, check_password_hash


def init_user_roles(db):
    """Initialize default users for each role if not already created."""
    # Admin user
    admin = db.get_collection("admin")
    if not admin.find_one({"username": "admin"}):
        hashed_password = generate_password_hash("admin@123")
        admin.insert_one(
            {
                "username": "admin",
                "fullname": "Administrator",
                "password": hashed_password,
                "role": "admin",
            }
        )


def init_sequence_collection(db):
    sequence_collection = db.get_collection("sequences")
    if sequence_collection.count_documents({"_id": "member_id"}) == 0:
        sequence_collection.insert_one({"_id": "member_id", "sequence_value": 1000})


def init_staff_sequence_collection(db):
    staff_sequence_collection = db.get_collection("staff_sequences")
    if staff_sequence_collection.count_documents({"_id": "staff_id"}) == 0:
        staff_sequence_collection.insert_one(
            {"_id": "staff_id", "sequence_value": 1000}
        )


def generate_member_id(db):
    sequence_collection = db.get_collection("sequences")

    # Atomically increment the sequence value
    sequence = sequence_collection.find_one_and_update(
        {"_id": "member_id"}, {"$inc": {"sequence_value": 1}}, return_document=True
    )

    if not sequence:
        raise Exception("Failed to generate member ID")

    # Generate the member_id and return
    return f"MEM{sequence['sequence_value']:04d}"


def generate_staff_id(db):
    sequence_collection = db.get_collection("staff_sequences")

    # Atomically increment the sequence value
    sequence = sequence_collection.find_one_and_update(
        {"_id": "staff_id"}, {"$inc": {"sequence_value": 1}}, return_document=True
    )

    if not sequence:
        raise Exception("Failed to generate staff ID")

    # Generate the staff_id and return
    return sequence["sequence_value"]
