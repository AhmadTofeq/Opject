# app/__init__.py
from flask import Flask
from .routes import main
from back_end_process.voice_api import voice_bp  
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(voice_bp)

    return app