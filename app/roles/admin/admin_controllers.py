import json
import uuid
from flask import (
    Blueprint,
    flash,
    jsonify,
    render_template,
    redirect,
    request,
    session,
    url_for,
)
from flask_login import login_required, current_user, login_user
from werkzeug.security import check_password_hash

from app.roles.member.member_services import (
    get_member_with_borrowed_history,
    get_member_with_borrowed_items,
    get_reserved_items,
    reserved_items,
)
from app.roles.staff.staff_services import transfer_items_list, update_transfer_status
from app.services.library_items_copy_services import (
    get_copy_item_by_rfid,
    library_item_copy_add,
    library_item_copy_get,
    copies_getby_itemId,
    library_item_copy_update,
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
from app.utils.enums import LibraryItemAvailabilityType, MemberStatus, TransferStatus
from app.utils.auth import User
from app.utils.database import db
from .admin_services import (
    branch_add,
    branch_get,
    branch_get_all,
    branch_set_inactive,
    branch_update,
    delete_branch_service,
    delete_library_item,
    members_get_all_by_status,
    members_update_by_status,
    staff_add_service,
    staff_get,
    staff_get_all_service,
    staff_set_inactive,
    staff_update,
)

from app.services.library_items_services import (
    get_all_library_items,
    library_item_add,
    library_item_get,
    library_item_update,
)

admin_bp = Blueprint("admin", __name__, template_folder="templates")


@admin_bp.route("/")
def admin_home():
    if current_user.is_authenticated and current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    else:
        return redirect(url_for("admin.login"))


@admin_bp.route("/login/", methods=["GET", "POST"])
def login():

    calculate_fees_and_update()
    # Handle POST
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin_collection = db.get_collection("admin")
        admin_data = admin_collection.find_one({"username": username})

        if admin_data and check_password_hash(admin_data["password"], password):
            user = User(
                str(admin_data["_id"]), admin_data["fullname"], admin_data["role"]
            )
            login_user(user)  # Sets `current_user`
            return redirect(url_for("admin.dashboard"))
        else:
            flash(("error", "Invalid login credentials!", "Login Failed"))
            return redirect(url_for("admin.login"))

    # print(current_app.config['UPLOAD_FOLDER'])
    return render_template("login.html")


@admin_bp.route("/dashboard/")
@login_required
def dashboard():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    calculate_fees_and_update()
    update_transfer_status()
    return render_template("dashboard.html")


@admin_bp.route("/staffs/")
@login_required
def staffs_view():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    staffs = staff_get_all_service()
    return render_template("staffs.html", staffs=staffs)


@admin_bp.route("/staffs/add/", methods=["GET", "POST"])
@login_required
def admin_add_staff():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    staff = None
    if request.method == "POST":
        try:
            data = request.form
            response = staff_add_service(data)
            if response["status"] == "success":
                flash(("success", response["message"]))
                return redirect(url_for("admin.staffs_view"))
            else:
                flash(("error", response["message"]))
                responseData = response["data"]
                del responseData["password"]
                return render_template("staff_form.html", staff=responseData)
        except Exception as e:
            print(e)
            flash(("error", f"An error occurred: {str(e)}", "Error"))

        return redirect(url_for("admin.admin_add_staff"))

    return render_template("staff_form.html", staff=staff)


@admin_bp.route("/staffs/<staff_id>/edit/", methods=["GET", "POST"])
@login_required
def admin_edit_staff(staff_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    # Update Staff Details
    if request.method == "POST":
        try:
            data = request.form
            response = staff_update(data, staff_id)
            if response["status"] == "success":
                flash(("success", response["message"]))
                return redirect(url_for("admin.staffs_view"))
            else:
                flash(("error", response["message"]))
        except Exception as e:
            print(e)
            flash(("error", f"An error occurred: {str(e)}", "Error"))

    response = staff_get(staff_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.staffs_view"))

    staff = response["data"]
    return render_template("staff_form.html", staff=staff)


@admin_bp.route("/staffs/<staff_id>/delete/")
@login_required
def staff_delete(staff_id):
    try:
        response = staff_set_inactive(staff_id)
        if response["status"] == "success":
            flash(("success", response["message"]))
        else:
            flash(("error", response["message"]))
    except Exception as e:
        print(e)
        flash(("error", f"An error occurred: {str(e)}", "Error"))

    return redirect(url_for("admin.staffs_view"))


@admin_bp.route("/branches/")
@login_required
def branches():
    branches = branch_get_all()
    return render_template("branches.html", branches=branches)


@admin_bp.route("/branches/add/", methods=["GET", "POST"])
@login_required
def branches_add():
    branch = None
    # Add Branch
    if request.method == "POST":
        data = request.form
        response = branch_add(data)
        if response["status"] == "success":
            flash(("success", response["message"]))
            return redirect(url_for("admin.branches"))
        else:
            flash(("error", response["message"]))
    # End of Add Branch
    staffs = staff_get_all_service()
    return render_template("branch_form.html", branch=branch, staffs=staffs, str=str)


@admin_bp.route("/branches/<branch_id>/edit/", methods=["GET", "POST"])
@login_required
def branches_update(branch_id):
    response = branch_get(branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    branch = response["data"] or None
    # Add Branch
    if request.method == "POST":
        data = request.form
        response = branch_update(data, branch_id)
        if response["status"] == "success":
            flash(("success", response["message"]))
            return redirect(url_for("admin.branches"))
        else:
            flash(("error", response["message"]))
    # End of Add Branch
    staffs = staff_get_all_service()
    return render_template("branch_form.html", branch=branch, staffs=staffs, str=str)


@admin_bp.route("/branches/<branch_id>/delete/")
@login_required
def branch_delete(branch_id):
    try:
        response = delete_branch_service(branch_id)
        if response["status"] == "success":
            flash(("success", response["message"]))
        else:
            flash(("error", response["message"]))
    except Exception as e:
        print(e)
        flash(("error", f"An error occurred: {str(e)}", "Error"))

    return redirect(url_for("admin.branches"))


# View Library items by item type
@admin_bp.route("/library-items/<type>/")
@login_required
def library_items(type):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    items = None
    response = get_all_library_items(type)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template = f"{type}s/{type}s.html"
    return render_template(template, items=items, type=type)


# Delete Library items by item type
@admin_bp.route("/library-items/<type>/<item_id>/delete/")
@login_required
def library_item_delete(type, item_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    response = delete_library_item(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))
    return redirect(url_for("admin.library_items", type=type))


# Add Library items by item type
@admin_bp.route("/library-items/<type>/add/", methods=["GET", "POST"])
@login_required
def add_library_items(type):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    item = None
    if request.method == "POST":
        data = request.form
        files = request.files
        response = library_item_add(data, files, type)
        if response["status"] == "success":
            flash(("success", response["message"]))
            return redirect(url_for("admin.library_items", type=type))
        else:
            flash(("error", response["message"]))

    template = f"{type}s/{type}s_form.html"
    return render_template(template, item=item, type=type)


# Update Library items by item type
@admin_bp.route("/library-items/<type>/<item_id>/edit/", methods=["GET", "POST"])
@login_required
def update_library_items(type, item_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    item = None
    resp = library_item_get(item_id)
    if resp["status"] == "success":
        item = resp["data"]
    else:
        flash(("error", resp["message"]))

    if request.method == "POST":
        data = request.form
        files = request.files
        response = library_item_update(item_id, data, files, type)
        if response["status"] == "success":
            flash(("success", response["message"]))
            return redirect(url_for("admin.library_items", type=type))
        else:
            flash(("error", response["message"]))

    template = f"{type}s/{type}s_form.html"
    return render_template(template, item=item, type=type)


# View Library Items
@admin_bp.route("/library-items/<type>/<item_id>/view/")
@login_required
def view_library_items_details(type, item_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.library_items", type=type))

    item = response["data"]
    template = f"{type}s/{type}s_details.html"
    return render_template(template, type=type, item=item)


# view copies by item id
@admin_bp.route("/library-items/<type>/<item_id>/copies/")
@login_required
def view_library_items_copies(type, item_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.library_items", type=type))

    item = response["data"]

    copies = None
    response = copies_getby_itemId(item_id)
    if response["status"] == "fail":
        flash(("error", copies["message"]))
    else:
        copies = response["data"]

    template = f"{type}s/{type}s_copies.html"
    return render_template(template, item=item, copies=copies)


# view copy details
@admin_bp.route("/library-items/<type>/<item_id>/copies/<copy_id>/")
@login_required
def view_library_items_copy_byid(type, item_id, copy_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    # get library item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.library_items", type=type))

    item = response["data"]

    # get copy details
    copy_resp = library_item_copy_get(copy_id)
    if copy_resp["status"] == "fail":
        flash(("error", copy_resp["message"]))
        return redirect(
            url_for("admin.view_library_items_copies", type=type, item_id=item_id)
        )

    copy = copy_resp["data"]

    template_name = f"{type}s/{type}s_copy_details.html"

    return render_template(template_name, item=item, copy=copy)


# add item copy GET
@admin_bp.route("/library-items/<type>/<item_id>/copies/add/", methods=["GET"])
@login_required
def add_item_copy(type, item_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    # get item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.library_items", type=type))

    item = response["data"]

    # get all branches
    branches = branch_get_all()

    rfid = uuid.uuid4().hex.upper()
    copy = None
    template = f"{type}s/{type}s_copies_form.html"
    return render_template(
        template,
        type=type,
        item=item,
        copy=copy,
        branches=branches,
        str=str,
        rfid=rfid,
    )


# add item copy post
@admin_bp.route("/library-items/<type>/<item_id>/copies/add/", methods=["POST"])
@login_required
def add_item_copy_post(type, item_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    data = request.form
    resp = library_item_copy_add(data)
    if resp["status"] == "fail":
        flash(("error", resp["message"]))
        return redirect(url_for("admin.add_item_copy", type=type, item_id=item_id))
    flash(("success", resp["message"]))
    return redirect(
        url_for("admin.view_library_items_copies", type=type, item_id=item_id)
    )


# edit item copy
@admin_bp.route(
    "/library-items/<type>/<item_id>/copies/<copy_id>/edit/", methods=["GET"]
)
@login_required
def edit_item_copy(type, item_id, copy_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    # get item
    response = library_item_get(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.library_items", type=type))

    item = response["data"]

    # get all branches
    branches = branch_get_all()

    # get copy
    response = library_item_copy_get(copy_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(
            url_for("admin.view_library_items_copies", type=type, item_id=item_id)
        )

    copy = response["data"]
    template = f"{type}s/{type}s_copies_form.html"
    return render_template(
        template, type=type, item=item, copy=copy, branches=branches, str=str
    )


# edit item copy post
@admin_bp.route(
    "/library-items/<type>/<item_id>/copies/<copy_id>/edit/", methods=["POST"]
)
@login_required
def edit_item_copy_post(type, item_id, copy_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    data = request.form
    resp = library_item_copy_update(data, copy_id)
    if resp["status"] == "fail":
        flash(("error", resp["message"]))
        return redirect(
            url_for("admin.edit_item_copy", type=type, item_id=item_id, copy_id=copy_id)
        )

    flash(("success", resp["message"]))
    return redirect(
        url_for("admin.view_library_items_copies", type=type, item_id=item_id)
    )


# Delete Copy
@admin_bp.route("/library-items/<type>/<item_id>/copies/<copy_id>/delete/")
@login_required
def delete_library_item_copy(type, item_id, copy_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    response = delete_copy(copy_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(
        url_for(
            "admin.view_library_items_copies",
            type=type,
            item_id=item_id,
        )
    )


# view members by status
@admin_bp.route("members/<status>/")
@login_required
def member_getall_by_status(status):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    members = None
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
    return render_template(
        "members/members.html", members=members, title=title, status=status
    )


# update member by status
@admin_bp.route("members/<status>/", methods=["POST"])
@login_required
def member_update_by_status(status):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    data = request.form
    response = members_update_by_status(data)
    if response["status"] == "success":
        flash(("success", response["message"]))
    else:
        flash(("error", response["message"]))
    return redirect(url_for("admin.member_getall_by_status", status=status))


# view member details with borrowed history
@admin_bp.route("members/<member_id>/<status>/")
@login_required
def member_view_details(member_id, status):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    response = get_member_with_borrowed_history(member_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("admin.member_getall_by_status", status=status))
    member = response["data"]
    return render_template("members/members_details.html", member=member)


# select the branch to checkout items
@admin_bp.route("select-branch/check-out", methods=["GET", "POST"])
@login_required
def select_branch_checkout():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    calculate_fees_and_update()

    session.pop("checkout_branch_id", None)
    session.pop("checkout_branch", None)

    if request.method == "POST":
        branch = None
        branch_id = request.form.get("branch_id")
        response = branch_get(branch_id)
        if response["status"] == "fail":
            flash(("error", response["message"]))
        else:
            branch = response["data"]
            session["checkout_branch_id"] = str(branch["_id"])
            session["checkout_branch"] = branch["name"]
            return redirect(url_for("admin.filter_checkout_items"))

    branches = branch_get_all()
    return render_template("select_checkout_branch.html", branches=branches)


# filter checkout datas
@admin_bp.route("filter/check-out", methods=["GET"])
@login_required
def filter_checkout_items():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    member = None
    copies = None

    member_id = request.args.get("m") if request.args.get("m") else ""
    branch_id = (
        session["checkout_branch_id"] if "checkout_branch_id" in session else None
    )

    response = filter_checkout(member_id, branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        member, copies = response["data"].values()

    return render_template(
        "checkout.html",
        member_id=member_id,
        member=member,
        branch_id=branch_id,
        copies=copies,
        str=str,
    )


@admin_bp.route("checkout-items", methods=["POST"])
@login_required
def checkout_items():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    member_id = request.form.get("member_id")
    if member_id == "" or None:
        flash(("error", "Please add a member to checkout"))
        return redirect(url_for("admin.filter_checkout_items"))

    rfid_list = request.form.getlist("rfids")

    if not rfid_list:
        flash(("error", "Please select atleast one item to checkout"))
        return redirect(url_for("admin.filter_checkout_items", m=member_id))

    response = checkout(member_id, rfid_list)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(url_for("admin.filter_checkout_items", m=member_id))


# filter return item by rfid
@admin_bp.route("filter/return/")
@login_required
def filter_by_rfid():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    calculate_fees_and_update()

    rfid = request.args.get("rfid", "")
    data = {}
    if rfid:
        response = filter_copies_by_rfid(rfid)
        if response["status"] == "fail":
            flash(("error", response["message"]))
        else:
            data = response["data"]

    template_name = "return.html"
    return render_template(template_name, data=data, rfid=rfid)


# return item
@admin_bp.route("return/<copy_id>/<member_id>", methods=["GET"])
@login_required
def return_items(copy_id, member_id):
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    response = return_borrowed_item(copy_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        calculate_fees_and_update()
        flash(("success", response["message"]))

    return redirect(url_for("admin.filter_checkout_items", m=member_id))


# view member reserved item
@admin_bp.route("reserved-items/")
@login_required
def member_reserved_items():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))
    items = None

    response = get_reserved_items()
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template_name = "members/member_reserved_items.html"
    return render_template(template_name, items=items)


# view items to transfer to other branch
@admin_bp.route("transfer-items/")
@login_required
def items_to_transfer():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    update_transfer_status()

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

    response = transfer_items_list(status=status)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template_name = "transfer_items.html"
    return render_template(template_name, items=items, page=page)


# view items to transfer to other branch
@admin_bp.route("transactions/")
@login_required
def transactions():
    if current_user.role != "admin":
        return redirect(url_for("admin.login"))

    transactions = get_all_transactions()
    template_name = "transactions.html"
    return render_template(template_name, transactions=transactions)
