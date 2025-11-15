import os
from flask import current_app


def remove_file_util(delete_folder, file):
    BASE_FOLDER = current_app.config["UPLOAD_FOLDER"]
    file_path = os.path.join(BASE_FOLDER, delete_folder, file)
    os.remove(file_path)
