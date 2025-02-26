"""
WSGI entry point for the Planning Poker application.
This file is used to run the application with a production WSGI server like Gunicorn.
"""
from planning_poker.app import app, socketio

# This is the WSGI application callable for Gunicorn to use
application = socketio.wsgi_app
