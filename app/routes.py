from flask import Flask, render_template, jsonify, request,Blueprint
import random
from datetime import datetime
import threading
import time
main = Blueprint('main', __name__)
@main.route('/')
def index():
    return render_template('index.html')

