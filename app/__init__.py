# app/__init__.py
from flask import Flask
from .routes import main
from back_end_process.voice_api import voice_bp  
from .config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(main)
    app.register_blueprint(voice_bp)  # Register the voice API

    return app
