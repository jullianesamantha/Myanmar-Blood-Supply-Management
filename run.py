#!/usr/bin/env python3
"""
Launcher script for Myanmar Blood Supply Chain System
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, init_db

if __name__ == '__main__':
    print("🚀 Starting Myanmar Blood Supply Chain Management System...")
    with app.app_context():
        init_db()
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"✅ System ready!")
    print(f"📍 Access at: http://localhost:{port}")
    print(f"🐛 Debug mode: {debug}")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
