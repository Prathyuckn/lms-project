from flask_pymongo import PyMongo
from flask import current_app

class Database:
    def __init__(self, app=None):
        self.mongo = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the database connection with the Flask app."""
        self.mongo = PyMongo(app).db

    def get_collection(self, collection_name):
        """Retrieve a specific collection."""
        if self.mongo is None:
            raise Exception("Database connection is not initialized.")
        return self.mongo[collection_name]

# Initialize the Database instance
db = Database()
