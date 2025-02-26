import sys
import os

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from planning_poker.app import app, socketio

# Vercel requires the app to be named 'app'
app = socketio.run_wsgi_app(app)