import os
import uuid
from flask import current_app
from werkzeug.utils import secure_filename


def upload_file_util(file, upload_folder, allowed_extensions):
    BASE_FOLDER = current_app.config["UPLOAD_FOLDER"]

    """Handles file validation and saving."""
    if not file:
        return "No file provided", None
    if file.filename == "":
        return "No filename provided", None
    if (
        "." not in file.filename
        or file.filename.rsplit(".", 1)[1].lower() not in allowed_extensions
    ):
        return "File type not allowed", None

    # Extract the file extension
    file_extension = file.filename.rsplit(".", 1)[1].lower()

    # Generate a unique filename
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"

    # Secure the filename and construct the file path
    filepath = os.path.join(
        BASE_FOLDER, upload_folder, secure_filename(unique_filename)
    )
    file.save(filepath)
    return None, unique_filename
