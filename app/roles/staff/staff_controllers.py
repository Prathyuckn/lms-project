import json
import uuid
from bson import ObjectId
from flask import Blueprint, flash, jsonify, render_template, redirect, request, url_for
from flask_login import login_required, current_user, login_user
from werkzeug.security import check_password_hash

from app.roles.admin.admin_services import branch_get, members_get_all_by_status
from app.roles.member.member_services import (
    get_member_with_borrowed_history,
    get_member_with_borrowed_items,
    get_reserved_items,
    reserved_items,
)
from app.roles.staff.staff_services import (
    initiate_transfer,
    transfer_items_list,
    update_transfer_status,
)
from app.services.library_items_copy_services import (
    copies_getby_itemId,
    library_item_copy_add,
    library_item_copy_get,
    library_item_copy_update,
)
from app.services.library_items_services import (
    get_library_items_by_type,
    library_item_get,
)
from app.services.shared_services import (
    calculate_fees_and_update,
    checkout,
    delete_copy,
    filter_checkout,
    filter_copies_by_rfid,
    get_all_transactions,
    return_borrowed_item,
)
from app.utils.auth import User
from app.utils.database import db
from app.utils.enums import MemberStatus, TransferStatus

staff_bp = Blueprint("staff", __name__, template_folder="templates")


def template(filename):
    return f"staff/{filename}.html"


# Load collections
staff_collection = db.get_collection("staff")
branch_collection = db.get_collection("branches")


@staff_bp.route("/")
def staff_home():
    if current_user.is_authenticated and current_user.role == "staff":
        return redirect(url_for("staff.dashboard"))
    else:
        return redirect(url_for("staff.login"))


@staff_bp.route("/login", methods=["GET", "POST"])
def login():

    calculate_fees_and_update()
    # Handle POST
    if request.method == "POST":
        staff_id = request.form["staff_id"]
        password = request.form["password"]

        staff_data = staff_collection.find_one(
            {"staff_id": staff_id, "is_active": True}
        )
        if not staff_data:
            flash(
                (
                    "error",
                    "Invalid Login Credentials!",
                    "Login Failed",
                )
            )
            return redirect(url_for("staff.login"))

        if "branch_id" not in staff_data:
            flash(
                (
                    "error",
                    "Library Branch not allocated, contact administrator!",
                    "Login Failed",
                )
            )
            return redirect(url_for("staff.login"))

        if staff_data and check_password_hash(staff_data["password"], password):
            fullname = f"{staff_data['firstname']} {staff_data['lastname']}"
            user = User(str(staff_data["_id"]), fullname, staff_data["role"])

            branch = branch_collection.find_one(
                {"_id": ObjectId(staff_data["branch_id"])}
            )

            if branch:
                user.add_attribute("branch_name", branch["name"])

            user.add_attribute("branch_id", staff_data.get("branch_id", ""))

            login_user(user)  # Sets `current_user`
            return redirect(url_for("staff.dashboard"))
        else:
            flash(("error", "Invalid login credentials!", "Login Failed"))
            return redirect(url_for("staff.login"))

    return render_template(template("staff_login_form"))


@staff_bp.route("/dashboard/")
@login_required
def dashboard():
    if current_user.role != "staff":
        return redirect(url_for("login"))

    calculate_fees_and_update()
    update_transfer_status()
    return render_template(template("dashboard"))


# View Library items by item type
@staff_bp.route("/library-items/<type>/")
@login_required
def library_items(type):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    items = None
    response = get_library_items_by_type(type, current_user.branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    print(items)
    template_name = template(f"{type}s/{type}s")
    return render_template(template_name, items=items, type=type)


# View Library Items
@staff_bp.route("/library-items/<type>/<item_id>/view/")
@login_required
def view_library_items_details(type, item_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.library_items", type=type))

    item = response["data"]

    template_name = template(f"{type}s/{type}s_details")
    return render_template(template_name, type=type, item=item)


# View Library Items copies on current branch
@staff_bp.route("/library-items/<type>/<item_id>/copies/")
@login_required
def view_library_items_copies(type, item_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    # get item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.library_items", type=type))

    item = response["data"]

    resp = copies_getby_itemId(item_id)
    if resp["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.library_items", type=type))

    copies = resp["data"]

    template_name = template(f"{type}s/{type}s_copies")
    return render_template(template_name, type=type, item=item, copies=copies)


# add item copy GET
@staff_bp.route("/library-items/<type>/<item_id>/copies/add/", methods=["GET"])
@login_required
def add_item_copy(type, item_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    # get item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.library_items", type=type))

    item = response["data"]

    copy = None
    rfid = uuid.uuid4().hex.upper()
    template_name = template(f"{type}s/{type}s_copies_form")

    return render_template(
        template_name,
        type=type,
        item=item,
        copy=copy,
        str=str,
        branch_id=current_user.branch_id,
        rfid=rfid,
    )


# add item copy post
@staff_bp.route("/library-items/<type>/<item_id>/copies/add/", methods=["POST"])
@login_required
def add_item_copy_post(type, item_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    data = request.form

    resp = library_item_copy_add(data)
    if resp["status"] == "fail":
        flash(("error", resp["message"]))
        return redirect(url_for("staff.add_item_copy", type=type, item_id=item_id))
    flash(("success", resp["message"]))

    return redirect(
        url_for("staff.view_library_items_copies", type=type, item_id=item_id)
    )


# edit item copy GET
@staff_bp.route(
    "/library-items/<type>/<item_id>/copies/<copy_id>/edit/", methods=["GET"]
)
@login_required
def edit_item_copy(type, item_id, copy_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    # get item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.library_items", type=type))

    item = response["data"]

    # get copy
    response = library_item_copy_get(copy_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(
            url_for("staff.view_library_items_copies", type=type, item_id=item_id)
        )

    copy = response["data"]
    template_name = template(f"{type}s/{type}s_copies_form")
    return render_template(
        template_name,
        type=type,
        item=item,
        copy=copy,
        str=str,
        branch_id=current_user.branch_id,
    )


# edit item copy POST
@staff_bp.route(
    "/library-items/<type>/<item_id>/copies/<copy_id>/edit/", methods=["POST"]
)
@login_required
def edit_item_copy_post(type, item_id, copy_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    data = request.form
    resp = library_item_copy_update(data, copy_id)
    if resp["status"] == "fail":
        flash(("error", resp["message"]))
        return redirect(
            url_for("staff.edit_item_copy", type=type, item_id=item_id, copy_id=copy_id)
        )

    flash(("success", resp["message"]))
    return redirect(
        url_for("staff.view_library_items_copies", type=type, item_id=item_id)
    )


# view copy details
@staff_bp.route("/library-items/<type>/<item_id>/copies/<copy_id>/")
@login_required
def view_library_items_copy_byid(type, item_id, copy_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    # get library item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.library_items", type=type))

    item = response["data"]

    # get copy details
    copy_resp = library_item_copy_get(copy_id)
    if copy_resp["status"] == "fail":
        flash(("error", copy_resp["message"]))
        return redirect(
            url_for("staff.view_library_items_copies", type=type, item_id=item_id)
        )

    copy = copy_resp["data"]

    template_name = template(f"{type}s/{type}s_copy_details")
    return render_template(template_name, item=item, copy=copy)


# Delete Copy
@staff_bp.route("/library-items/<type>/<item_id>/copies/<copy_id>/delete/")
@login_required
def delete_library_item_copy(type, item_id, copy_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    response = delete_copy(copy_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(
        url_for(
            "staff.view_library_items_copies",
            type=type,
            item_id=item_id,
        )
    )


# filter checkout datas
@staff_bp.route("filter/check-out", methods=["GET"])
@login_required
def filter_checkout_items():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    calculate_fees_and_update()
    member = None
    copies = None

    member_id = request.args.get("m") if request.args.get("m") else ""
    branch_id = current_user.branch_id

    response = filter_checkout(member_id, branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        member, copies = response["data"].values()

    template_name = template("checkout")
    return render_template(
        template_name,
        member_id=member_id,
        member=member,
        branch_id=branch_id,
        copies=copies,
        str=str,
    )


@staff_bp.route("checkout-items", methods=["POST"])
@login_required
def checkout_items():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    member_id = request.form.get("member_id")
    if member_id == "" or None:
        flash(("error", "Please add a member to checkout"))
        return redirect(url_for("staff.filter_checkout_items"))

    rfid_list = request.form.getlist("rfids")

    if not rfid_list:
        flash(("error", "Please select atleast one item to checkout"))
        return redirect(url_for("staff.filter_checkout_items", m=member_id))

    branch_id = current_user.branch_id

    response = checkout(member_id, rfid_list)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(url_for("staff.filter_checkout_items", m=member_id))


# checkout item
# @staff_bp.route("check-out", methods=["GET"])
# @login_required
# def checkout_items():
#     if current_user.role != "staff":
#         return redirect(url_for("staff.login"))

#     member_id = request.args.get("m") if request.args.get("m") else ""
#     rfid = request.args.get("r") if request.args.get("r") else ""
#     branch_id = current_user.branch_id

#     if member_id and rfid:
#         response = checkout(member_id, rfid)
#         if response["status"] == "fail":
#             flash(("error", response["message"]))
#         else:
#             flash(("success", response["message"]))
#     else:
#         flash(("error", "Error checking out item!"))

#     return redirect(url_for("staff.filter_checkout_items", m=member_id))


# filter return item by rfid
@staff_bp.route("filter/return/")
@login_required
def filter_by_rfid():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    calculate_fees_and_update()

    rfid = request.args.get("rfid", "")
    data = {}
    if rfid:
        response = filter_copies_by_rfid(rfid)
        if response["status"] == "fail":
            flash(("error", response["message"]))
        else:
            data = response["data"]

    template_name = template("return")
    return render_template(template_name, data=data, rfid=rfid)


# return item from member
@staff_bp.route("return/<copy_id>/<member_id>", methods=["GET"])
@login_required
def return_items_from_member(copy_id, member_id):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    response = return_borrowed_item(copy_id, current_user.branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        calculate_fees_and_update()
        flash(("success", response["message"]))

    return redirect(url_for("staff.filter_checkout_items", m=member_id))


# view member reserved item
@staff_bp.route("reserved-items/")
@login_required
def member_reserved_items():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    branch_id = current_user.branch_id

    items = None

    response = get_reserved_items(branch_id=branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template_name = template("reserved_items")
    return render_template(template_name, items=items)


# view items to transfer to other branch
@staff_bp.route("transfer-items/")
@login_required
def items_to_transfer():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    update_transfer_status()

    branch_id = current_user.branch_id
    items = None

    status = None
    page = "Pending"
    in_transit = bool(request.args.get("in_transit"))
    completed = bool(request.args.get("completed"))

    if in_transit:
        status = TransferStatus.IN_TRANSIT.value
        page = "In Transit"
    elif completed:
        status = TransferStatus.COMPLETED.value
        page = "Completed"
    else:
        status = TransferStatus.PENDING.value

    response = transfer_items_list(branch_id, status)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template_name = template("transfer_items")
    return render_template(template_name, items=items, page=page)


# initiate transfer from current branch to original branch
@staff_bp.route("transfer")
@login_required
def initiate_item_transfer():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    transfer_id = request.args.get("transfer_id")
    copy_id = request.args.get("_copy_id")

    response = initiate_transfer(transfer_id, copy_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(url_for("staff.items_to_transfer"))


# view members by status
@staff_bp.route("members/")
@login_required
def member_getall_by_status():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    members = None
    status = MemberStatus.APPROVED.value
    response = members_get_all_by_status(status)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        members = response["data"]

    title = None
    if status == MemberStatus.PENDING.value:
        title = "Members Pending For Approval"
    else:
        title = f"{MemberStatus(status).name.capitalize()} Members"

    template_name = template("members")
    return render_template(template_name, members=members, status=status)


# view member details with borrowed items
@staff_bp.route("members/<member_id>/<status>/")
@login_required
def member_view_details(member_id, status):
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    response = get_member_with_borrowed_history(member_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("staff.member_getall_by_status", status=status))
    member = response["data"]

    template_name = template("members_details")
    return render_template(template_name, member=member)


# view transactions
@staff_bp.route("transactions/")
@login_required
def view_transactions():
    if current_user.role != "staff":
        return redirect(url_for("staff.login"))

    branch_id = current_user.branch_id
    transactions = get_all_transactions(branch_id=branch_id)
    template_name = template("transactions")
    return render_template(template_name, transactions=transactions)
