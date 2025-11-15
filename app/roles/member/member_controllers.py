from datetime import datetime
from email.utils import format_datetime
import os
from flask import Blueprint, flash, render_template, redirect, request, url_for
from flask_login import login_required, current_user

from app.roles.member.member_services import (
    delete_notification,
    delete_reservation,
    get_member_by_id,
    get_member_with_borrowed_items,
    get_notifications,
    get_reserved_items,
    member_get_borrowed_items,
    member_login,
    member_update,
    member_update_password,
    registration,
    renew_borrowed_item,
    reserve_library_item,
    reserved_items,
)
from app.roles.staff.staff_services import update_transfer_status
from app.services.library_items_services import (
    get_all_library_items,
    library_item_details_with_copies_count_branchwise,
)
from app.services.shared_services import calculate_fees_and_update, get_all_transactions
from app.utils.format_datetime import format_notification_datetime

member_bp = Blueprint("member", __name__, template_folder="templates")


def template(filename):
    return f"member/{filename}.html"


@member_bp.route("/registration/", methods=["GET", "POST"])
def member_registration():
    # POST Data
    if request.method == "POST":
        data = request.form
        response = registration(data)
        if response["status"] == "fail":
            flash(("error", response["message"]))
        else:
            flash(("success", response["message"]))

            return redirect(url_for("member.login"))

    return render_template(template("registration"))


@member_bp.route("/login/", methods=["GET", "POST"])
def login():
    error_msg = None
    # Handle POST
    if request.method == "POST":
        data = request.form
        response = member_login(data)
        if response["status"] == "success":
            return redirect(url_for("member.dashboard"))
        else:
            error_msg = response["message"]

    return render_template(template("member_login_form"), error_msg=error_msg)


@member_bp.route("/forget-password/", methods=["GET", "POST"])
def member_forget_password():
    if request.method == "POST":
        member_id = request.form.get("member_id")
        password = request.form.get("password")
        response = member_update_password(member_id, password)
        if response["status"] == "success":
            flash(("success", response["message"]))
        else:
            flash(("error", response["message"]))
        return redirect(url_for("member.login"))

    template_name = template("forget_password_form")
    return render_template(template_name)


@member_bp.route("/change-password/", methods=["GET", "POST"])
def member_change_password():
    if request.method == "POST":
        user_id = current_user.id
        resp = get_member_by_id(user_id)
        member = resp["data"]

        password = request.form.get("password")

        response = member_update_password(member["member_id"], password)
        if response["status"] == "success":
            flash(("success", response["message"]))
        else:
            flash(("error", response["message"]))
        return redirect(url_for("member.member_change_password"))

    template_name = template("change_password")
    return render_template(template_name)


@member_bp.route("/profile/", methods=["GET", "POST"])
def member_profile():
    member_id = current_user.id
    if request.method == "POST":
        data = request.form
        resp = member_update(member_id, data)
        if resp["status"] == "fail":
            flash(("error", resp["message"]))
        else:
            flash(("success", resp["message"]))
        return redirect(url_for("member.member_profile"))

    response = get_member_by_id(member_id)
    member = None
    if response["status"] == "fail":
        flash(("error", "Something went wrong"))
    else:
        member = response["data"]
    template_name = template("profile")
    return render_template(template_name, member=member)


@member_bp.route("/dashboard/")
@login_required
def dashboard():
    if current_user.role != "member":
        return redirect(url_for("login"))

    calculate_fees_and_update()
    update_transfer_status()
    return render_template(template("dashboard"))


@member_bp.route("/library-items/")
@login_required
def library_items():
    if current_user.role != "member":
        return redirect(url_for("login"))

    return render_template(template("library_items"))


# filter and view items eg: list of books or dvds
@member_bp.route("/library-items/<type>/")
@login_required
def library_item_list(type):
    if current_user.role != "member":
        return redirect(url_for("login"))

    items = None
    response = get_all_library_items(type)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template_name = template(f"{type}/{type}_list")
    return render_template(template_name, items=items)


# filter and view items eg: list of books or dvds
@member_bp.route("/library-items/<type>/<item_id>/")
@login_required
def library_item_details(type, item_id):
    if current_user.role != "member":
        return redirect(url_for("login"))

    item = None
    copies = None
    response = library_item_details_with_copies_count_branchwise(item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(url_for("member.library_item_list", type=type))
    else:
        item = response["item"]
        copies = response["copies"]

    template_name = template(f"{type}/{type}_details")
    return render_template(template_name, item=item, copies=copies)


# Reserve library item for specific branch
@member_bp.route("/library-items/<type>/<item_id>/branch/<branch_id>/reserve/")
@login_required
def member_reserve_library_item(type, item_id, branch_id):
    if current_user.role != "member":
        return redirect(url_for("login"))

    member_id = current_user.id
    response = reserve_library_item(member_id, item_id, branch_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
        return redirect(
            url_for("member.library_item_details", type=type, item_id=item_id)
        )
    else:
        flash(("success", response["message"]))

    return redirect(url_for("member.member_reserved_items", type=type, item_id=item_id))


# view reserved items
@member_bp.route("/reserved-items/")
@login_required
def member_reserved_items():
    if current_user.role != "member":
        return redirect(url_for("login"))

    member_id = current_user.id

    items = None

    response = get_reserved_items(member_id=member_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        items = response["data"]

    template_name = template("reserved_items")
    return render_template(template_name, items=items)


# view reserved items
@member_bp.route("/reserved-items/<id>/delete/")
@login_required
def delete_reserved_items(id):
    if current_user.role != "member":
        return redirect(url_for("login"))

    response = delete_reservation(id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(url_for("member.member_reserved_items"))


# view borrowed items
@member_bp.route("/borrowed-items/")
@login_required
def member_borrowed_items():
    if current_user.role != "member":
        return redirect(url_for("login"))

    member_id = current_user.id
    returned = bool(request.args.get("returned"))

    response = member_get_borrowed_items(member_id, returned)
    items = None
    if response["status"] == "success":
        items = response["data"]
    else:
        flash(("error", response["message"]))
    template_name = template("borrowed_items")
    today = datetime.now()
    return render_template(template_name, items=items, returned=returned, today=today)


# view borrowed items
@member_bp.route("/borrowed-items/<item_id>/renew/")
@login_required
def member_renew_borrowed_item(item_id):
    if current_user.role != "member":
        return redirect(url_for("login"))

    member_id = current_user.id
    response = renew_borrowed_item(member_id, item_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        calculate_fees_and_update()
        flash(("success", response["message"]))
    return redirect(url_for("member.member_borrowed_items"))


# view transactions
@member_bp.route("transactions/")
@login_required
def view_transactions():
    if current_user.role != "member":
        return redirect(url_for("member.login"))

    member_id = current_user.id
    transactions = get_all_transactions(member_id=member_id)
    template_name = template("transactions")
    return render_template(template_name, transactions=transactions)


# view notification
@member_bp.route("notifications/")
@login_required
def view_notifications():
    if current_user.role != "member":
        return redirect(url_for("member.login"))

    member_id = current_user.id
    notifications = None
    response = get_notifications(member_id=member_id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        notifications = response["data"]

    time = format_notification_datetime
    template_name = template("notifications")
    return render_template(template_name, notifications=notifications, time=time)


# delete notification
@member_bp.route("notifications/<id>/delete/")
@login_required
def delete_notifications(id):
    if current_user.role != "member":
        return redirect(url_for("member.login"))

    response = delete_notification(id)
    if response["status"] == "fail":
        flash(("error", response["message"]))
    else:
        flash(("success", response["message"]))

    return redirect(url_for("member.view_notifications"))
