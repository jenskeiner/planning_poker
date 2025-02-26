#!/usr/bin/env python
"""
Script to run the Planning Poker application in development or production mode.
"""
import argparse
import os
import sys

def main():
    parser = argparse.ArgumentParser(description='Run Planning Poker application')
    parser.add_argument('--prod', action='store_true', help='Run in production mode with Gunicorn')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to (default: 5000)')
    args = parser.parse_args()
    
    if args.prod:
        # In production mode, use Gunicorn with eventlet
        try:
            import gunicorn
            import eventlet
        except ImportError:
            print("Error: gunicorn and eventlet are required for production mode.")
            print("Install them with: pip install gunicorn eventlet")
            sys.exit(1)
            
        # Build the Gunicorn command
        cmd = f"gunicorn --worker-class eventlet -w 1 --bind {args.host}:{args.port} wsgi:application"
        print(f"Starting in production mode: {cmd}")
        os.system(cmd)
    else:
        # In development mode, use the built-in Flask development server
        from planning_poker.app import app, socketio
        print(f"Starting in development mode on {args.host}:{args.port}")
        socketio.run(app, host=args.host, port=args.port, debug=True)

if __name__ == '__main__':
    main()
