from .database import db

admin_collection = db.get_collection("admin")
staffs_collection = db.get_collection("staff")
members_collection = db.get_collection("member")

branches_collection = db.get_collection("branches")

types_collection = db.get_collection("library_item_types")
items_collection = db.get_collection("library_items")
copies_collection = db.get_collection("copies")

borrowed_collection = db.get_collection("borrowed_items")
reservations_collection = db.get_collection("reservations")

transfers_collection = db.get_collection("transfers")
transactions_collection = db.get_collection("transactions")
notifications_collection = db.get_collection("notifications")
