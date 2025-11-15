from flask import Flask
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_toastr import Toastr

from app.utils.database import db
from app.utils.enums import LibraryItemTypes
from app.utils.init_roles import (
    init_sequence_collection,
    init_staff_sequence_collection,
    init_user_roles,
)

login_manager = LoginManager()
bcrypt = Bcrypt()
toastr = Toastr()


def create_app():
    app = Flask(__name__)
    app.config.from_object("config.Config")

    # Initialize extensions
    db.init_app(app)  # Initialize the database connection
    login_manager.init_app(app)
    bcrypt.init_app(app)
    toastr.init_app(app)

    # Register blueprints for roles
    from app.roles.admin.admin_controllers import admin_bp
    from app.roles.staff.staff_controllers import staff_bp
    from app.roles.member.member_controllers import member_bp

    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(staff_bp, url_prefix="/staff")
    app.register_blueprint(member_bp, url_prefix="/member")

    # Injecting Enums Globally
    @app.context_processor
    def inject_enums():
        return dict(LibraryItemTypes=LibraryItemTypes)

    with app.app_context():  # Ensure proper app context for database operations
        init_user_roles(db)
        init_sequence_collection(db)
        init_staff_sequence_collection(db)

    return app
