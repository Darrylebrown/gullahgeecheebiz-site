#!/usr/bin/env python3
"""
Gullah Hearth Platform - Fixed Version
A cultural preservation and community platform for Gullah Geechee heritage.
"""

import json
import sqlite3
import os
import sys
import time
import logging
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import requests
import hashlib
import uuid
import omniroute_shim  # OMNIROUTE_MIGRATED

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/gullah-hearth/server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration
PORT = 8085
DB_PATH = '/Users/darrylsmac/gullahgeecheebiz-site/ggb-engine/headquarters/logs/gullah-hearth/hearth.db'
OMNIROUTE_BASE_URL = 'http://localhost:20128'
OMNIROUTE_API_KEY = ''

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.ensure_db_directory()
        self.init_database()
    
    def ensure_db_directory(self):
        """Ensure the database directory exists"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            logger.info(f"Database directory ensured: {os.path.dirname(self.db_path)}")
        except Exception as e:
            logger.error(f"Failed to create database directory: {e}")
            raise
    
    def init_database(self):
        """Initialize database with proper error handling"""
        try:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.cursor()
                
                # Create tables
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS soul_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT UNIQUE NOT NULL,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE,
                        heritage_story TEXT,
                        family_connections TEXT,
                        cultural_interests TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS community_posts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category TEXT DEFAULT 'general',
                        likes INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS chat_messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        username TEXT NOT NULL,
                        message TEXT NOT NULL,
                        room TEXT DEFAULT 'general',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS kinship_subscriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        plan_type TEXT NOT NULL,
                        status TEXT DEFAULT 'active',
                        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS concierge_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        session_id TEXT UNIQUE NOT NULL,
                        messages TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def get_connection(self):
        """Get database connection with timeout"""
        try:
            return sqlite3.connect(self.db_path, timeout=10)
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise

class AIService:
    def __init__(self):
        # Route through OmniRoute with compression and auto-fallback
        self.omniroute = True

    def get_binyah_response(self, user_message, context=""):
        """Get AI response via OmniRoute with compression and auto-fallback"""
        try:
            system_prompt = """You are Binyah, a wise Gullah Geechee cultural concierge. You help people connect with their heritage, 
            learn about Gullah Geechee culture, traditions, food, language, and history. Speak with warmth and wisdom, 
            occasionally using Gullah phrases when appropriate. Keep responses helpful and culturally authentic."""
            
            response = omniroute_shim.call_ai(
                f"{context}\n\n{system_prompt}\n\nUser: {user_message}",
                max_tokens=500
            )
            if response:
                return response
            else:
                logger.error("AI OmniRoute returned empty response")
                return "I'm having trouble connecting right now. Please try again in a moment."
        except Exception as e:
            logger.error(f"AI service error: {e}")
            return "I'm experiencing some difficulties. Please try again later."

class GullahHearthHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, db_manager=None, ai_service=None, **kwargs):
        self.db_manager = db_manager
        self.ai_service = ai_service
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to use our logger"""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            query_params = parse_qs(parsed_path.query)
            
            logger.info(f"GET request: {path}")
            
            if path == '/health':
                self.handle_health_check()
            elif path == '/':
                self.serve_homepage()
            elif path == '/api/soul-profiles':
                self.handle_get_soul_profiles()
            elif path == '/api/community/posts':
                self.handle_get_community_posts()
            elif path == '/api/chat/messages':
                self.handle_get_chat_messages(query_params)
            elif path.startswith('/static/') or path.endswith(('.css', '.js', '.png', '.jpg', '.ico')):
                self.serve_static_file(path)
            else:
                self.serve_homepage()  # Default to homepage for SPA routing
                
        except Exception as e:
            logger.error(f"Error handling GET request: {e}")
            self.send_error_response(500, "Internal server error")
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            parsed_path = urlparse(self.path)
            path = parsed_path.path
            
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            logger.info(f"POST request: {path}")
            
            try:
                data = json.loads(post_data.decode('utf-8')) if post_data else {}
            except json.JSONDecodeError:
                self.send_error_response(400, "Invalid JSON")
                return
            
            if path == '/api/soul-profiles':
                self.handle_create_soul_profile(data)
            elif path == '/api/binyah/chat':
                self.handle_binyah_chat(data)
            elif path == '/api/community/posts':
                self.handle_create_community_post(data)
            elif path == '/api/chat/send':
                self.handle_send_chat_message(data)
            elif path == '/api/kinship/subscribe':
                self.handle_kinship_subscription(data)
            else:
                self.send_error_response(404, "Not found")
                
        except Exception as e:
            logger.error(f"Error handling POST request: {e}")
            self.send_error_response(500, "Internal server error")
    
    def handle_health_check(self):
        """Health check endpoint"""
        try:
            # Quick database check
            with self.db_manager.get_connection() as conn:
                conn.execute("SELECT 1")
            
            response = {"status": "ok", "timestamp": datetime.now().isoformat()}
            self.send_json_response(response)
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            self.send_error_response(503, "Service unavailable")
    
    def serve_homepage(self):
        """Serve the main homepage"""
        html_content = self.get_homepage_html()
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))
    
    def serve_static_file(self, path):
        """Serve static files with basic MIME type detection"""
        try:
            # Simple static file serving (in production, use nginx or similar)
            if path.endswith('.css'):
                content_type = 'text/css'
            elif path.endswith('.js'):
                content_type = 'application/javascript'
            elif path.endswith('.png'):
                content_type = 'image/png'
            elif path.endswith('.jpg') or path.endswith('.jpeg'):
                content_type = 'image/jpeg'
            else:
                content_type = 'text/plain'
            
            # For now, return a simple response
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.end_headers()
            self.wfile.write(b'/* Static file placeholder */')
            
        except Exception as e:
            logger.error(f"Error serving static file {path}: {e}")
            self.send_error_response(404, "File not found")
    
    def handle_get_soul_profiles(self):
        """Get soul profiles"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM soul_profiles ORDER BY created_at DESC LIMIT 10")
                profiles = cursor.fetchall()
                
                # Convert to dict format
                profile_list = []
                for profile in profiles:
                    profile_dict = {
                        'id': profile[0],
                        'user_id': profile[1],
                        'name': profile[2],
                        'heritage_story': profile[4],
                        'created_at': profile[7]
                    }
                    profile_list.append(profile_dict)
                
                self.send_json_response({"profiles": profile_list})
                
        except Exception as e:
            logger.error(f"Error getting soul profiles: {e}")
            self.send_error_response(500, "Database error")
    
    def handle_create_soul_profile(self, data):
        """Create a new soul profile"""
        try:
            required_fields = ['name', 'email']
            if not all(field in data for field in required_fields):
                self.send_error_response(400, "Missing required fields")
                return
            
            user_id = str(uuid.uuid4())
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO soul_profiles (user_id, name, email, heritage_story, family_connections, cultural_interests)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    data['name'],
                    data['email'],
                    data.get('heritage_story', ''),
                    data.get('family_connections', ''),
                    data.get('cultural_interests', '')
                ))
                conn.commit()
                
                self.send_json_response({"success": True, "user_id": user_id})
                
        except sqlite3.IntegrityError:
            self.send_error_response(400, "Email already exists")
        except Exception as e:
            logger.error(f"Error creating soul profile: {e}")
            self.send_error_response(500, "Database error")
    
    def handle_binyah_chat(self, data):
        """Handle Binyah Concierge chat"""
        try:
            if 'message' not in data:
                self.send_error_response(400, "Message required")
                return
            
            user_message = data['message']
            user_id = data.get('user_id', 'anonymous')
            
            # Get AI response
            response = self.ai_service.get_binyah_response(user_message)
            
            # Store session (optional, for conversation history)
            session_id = data.get('session_id', str(uuid.uuid4()))
            
            try:
                with self.db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    messages = json.dumps([
                        {'role': 'user', 'content': user_message, 'timestamp': datetime.now().isoformat()},
                        {'role': 'assistant', 'content': response, 'timestamp': datetime.now().isoformat()}
                    ])
                    
                    cursor.execute('''
                        INSERT OR REPLACE INTO concierge_sessions (user_id, session_id, messages, updated_at)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, session_id, messages, datetime.now().isoformat()))
                    conn.commit()
            except Exception as db_error:
                logger.error(f"Error storing chat session: {db_error}")
                # Continue even if storage fails
            
            self.send_json_response({
                "response": response,
                "session_id": session_id
            })
            
        except Exception as e:
            logger.error(f"Error in Binyah chat: {e}")
            self.send_error_response(500, "Chat service error")
    
    def handle_get_community_posts(self):
        """Get community posts"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, user_id, title, content, category, likes, created_at 
                    FROM community_posts 
                    ORDER BY created_at DESC LIMIT 20
                ''')
                posts = cursor.fetchall()
                
                post_list = []
                for post in posts:
                    post_dict = {
                        'id': post[0],
                        'user_id': post[1],
                        'title': post[2],
                        'content': post[3],
                        'category': post[4],
                        'likes': post[5],
                        'created_at': post[6]
                    }
                    post_list.append(post_dict)
                
                self.send_json_response({"posts": post_list})
                
        except Exception as e:
            logger.error(f"Error getting community posts: {e}")
            self.send_error_response(500, "Database error")
    
    def handle_create_community_post(self, data):
        """Create a community post"""
        try:
            required_fields = ['title', 'content', 'user_id']
            if not all(field in data for field in required_fields):
                self.send_error_response(400, "Missing required fields")
                return
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO community_posts (user_id, title, content, category)
                    VALUES (?, ?, ?, ?)
                ''', (
                    data['user_id'],
                    data['title'],
                    data['content'],
                    data.get('category', 'general')
                ))
                conn.commit()
                post_id = cursor.lastrowid
                
                self.send_json_response({"success": True, "post_id": post_id})
                
        except Exception as e:
            logger.error(f"Error creating community post: {e}")
            self.send_error_response(500, "Database error")
    
    def handle_get_chat_messages(self, query_params):
        """Get chat messages"""
        try:
            room = query_params.get('room', ['general'])[0]
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, user_id, username, message, room, created_at 
                    FROM chat_messages 
                    WHERE room = ? 
                    ORDER BY created_at DESC LIMIT 50
                ''', (room,))
                messages = cursor.fetchall()
                
                message_list = []
                for msg in reversed(messages):  # Reverse to show chronological order
                    message_dict = {
                        'id': msg[0],
                        'user_id': msg[1],
                        'username': msg[2],
                        'message': msg[3],
                        'room': msg[4],
                        'created_at': msg[5]
                    }
                    message_list.append(message_dict)
                
                self.send_json_response({"messages": message_list})
                
        except Exception as e:
            logger.error(f"Error getting chat messages: {e}")
            self.send_error_response(500, "Database error")
    
    def handle_send_chat_message(self, data):
        """Send a chat message"""
        try:
            required_fields = ['message', 'username']
            if not all(field in data for field in required_fields):
                self.send_error_response(400, "Missing required fields")
                return
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO chat_messages (user_id, username, message, room)
                    VALUES (?, ?, ?, ?)
                ''', (
                    data.get('user_id', 'anonymous'),
                    data['username'],
                    data['message'],
                    data.get('room', 'general')
                ))
                conn.commit()
                message_id = cursor.lastrowid
                
                self.send_json_response({"success": True, "message_id": message_id})
                
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
            self.send_error_response(500, "Database error")
    
    def handle_kinship_subscription(self, data):
        """Handle kinship subscription"""
        try:
            required_fields = ['user_id', 'plan_type']
            if not all(field in data for field in required_fields):
                self.send_error_response(400, "Missing required fields")
                return
            
            expires_at = datetime.now() + timedelta(days=30)  # 30-day subscription
            
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO kinship_subscriptions (user_id, plan_type, expires_at)
                    VALUES (?, ?, ?)
                ''', (
                    data['user_id'],
                    data['plan_type'],
                    expires_at.isoformat()
                ))
                conn.commit()
                subscription_id = cursor.lastrowid
                
                self.send_json_response({
                    "success": True, 
                    "subscription_id": subscription_id,
                    "expires_at": expires_at.isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            self.send_error_response(500, "Database error")
    
    def send_json_response(self, data):
        """Send JSON response"""
        response_data = json.dumps(data)
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))
    
    def send_error_response(self, status_code, message):
        """Send error response"""
        error_data = json.dumps({"error": message})
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(error_data)))
        self.end_headers()
        self.wfile.write(error_data.encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def get_homepage_html(self):
        """Get homepage HTML content"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gullah Hearth - Cultural Preservation Platform</title>
    <style>
        body {
            font-family: 'Georgia', serif;
            line-height: 1.6;
            margin: 0;
            padding: 0;
            background-color: #f5f5dc;
            color: #2c1810;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #8b4513;
            color: white;
            text-align: center;
            padding: 2rem 0;
            margin-bottom: 2rem;
        }
        .welcome-section {
            background-color: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin: 2rem 0;
        }
        .feature-card {
            background-color: white;
            border-radius: 10px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .feature-card:hover {
            transform: translateY(-5px);
        }
        .feature-card h3 {
            color: #8b4513;
            margin-bottom: 1rem;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            background-color: #4caf50;
            border-radius: 50%;
            margin-right: 8px;
        }
        .btn {
            background-color: #8b4513;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            margin: 5px;
        }
        .btn:hover {
            background-color: #a0522d;
        }
        .health-status {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #4caf50;
            color: white;
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="health-status">
        <span class="status-indicator"></span>
        Server Online
    </div>
    
    <header>
        <h1>Gullah Hearth</h1>
        <p>Preserving Heritage, Building Community</p>
    </header>
    
    <div class="container">
        <div class="welcome-section">
            <h2>Welcome to Gullah Hearth</h2>
            <p>A digital sanctuary for Gullah Geechee culture, connecting families, preserving stories, and celebrating the rich heritage of our coastal communities. From the Sea Islands to the world, we keep our traditions alive.</p>
        </div>
        
        <div class="features-grid">
            <div class="feature-card">
                <h3>🏠 Soul Profiles</h3>
                <p>Create your cultural identity profile. Share your heritage story, family connections, and cultural interests with the community.</p>
                <a href="#" class="btn">Create Profile</a>
            </div>
            
            <div class="feature-card">
                <h3>🌟 Binyah Concierge</h3>
                <p>Your AI cultural guide powered by generations of wisdom. Ask about traditions, recipes, language, and family history.</p>
                <a href="#" class="btn">Chat with Binyah</a>
            </div>
            
            <div class="feature-card">
                <h3>🤝 Community Hub</h3>
                <p>Connect with fellow community members, share stories, ask questions, and celebrate our shared heritage together.</p>
                <a href="#" class="btn">Join Community</a>
            </div>
            
            <div class="feature-card">
                <h3>💬 Common Chat</h3>
                <p>Real-time conversations with community members. Share daily life, cultural events, and stay connected.</p>
                <a href="#" class="btn">Enter Chat</a>
            </div>
            
            <div class="feature-card">
                <h3>👨‍👩‍👧‍👦 Kinship Network</h3>
                <p>Premium genealogy and family connection services. Discover relatives, trace family trees, and preserve family stories.</p>
                <a href="#" class="btn">Explore Kinship</a>
            </div>
            
            <div class="feature-card">
                <h3>📚 Cultural Resources</h3>
                <p>Access our library of Gullah Geechee traditions, language guides, historical documents, and cultural education materials.</p>
                <a href="#" class="btn">Browse Resources</a>
            </div>
        </div>
        
        <div class="welcome-section">
            <h3>Platform Status</h3>
            <p><span class="status-indicator"></span> All systems operational</p>
            <p><span class="status-indicator"></span> Database connected</p>
            <p><span class="status-indicator"></span> AI services available</p>
            <p><span class="status-indicator"></span> Community features active</p>
        </div>
    </div>
    
    <script>
        // Simple health check
        setInterval(async () => {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                console.log('Health check:', data);
            } catch (error) {
                console.error('Health check failed:', error);
            }
        }, 30000);
    </script>
</body>
</html>'''

def create_handler_class(db_manager, ai_service):
    """Create handler class with dependencies"""
    class Handler(GullahHearthHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, db_manager=db_manager, ai_service=ai_service, **kwargs)
    return Handler

def main():
    """Main server function with proper error handling"""
    logger.info("Starting Gullah Hearth Platform...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        db_manager = DatabaseManager(DB_PATH)
        logger.info("Database initialized successfully")
        
        # Initialize AI service
        logger.info("Initializing AI service...")
        ai_service = AIService(OPENROUTER_API_KEY)
        if OPENROUTER_API_KEY:
            logger.info("AI service initialized with API key")
        else:
            logger.warning("AI service initialized without API key - limited functionality")
        
        # Create server
        handler_class = create_handler_class(db_manager, ai_service)
        server = HTTPServer(('0.0.0.0', PORT), handler_class)
        
        logger.info(f"Server starting on port {PORT}")
        logger.info(f"Health check available at http://localhost:{PORT}/health")
        logger.info(f"Homepage available at http://localhost:{PORT}/")
        
        print(f"\n🌟 Gullah Hearth Platform is now running!")
        print(f"🌐 Server: http://localhost:{PORT}")
        print(f"❤️  Health: http://localhost:{PORT}/health")
        print(f"🏠 Homepage: http://localhost:{PORT}/")
        print(f"📁 Database: {DB_PATH}")
        print(f"🤖 AI Service: {'Enabled' if OPENROUTER_API_KEY else 'Disabled (no API key)'}")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        # Start server
        server.serve_forever()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
        print("\n🛑 Server shutting down...")
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {PORT} is already in use. Please stop the existing service or use a different port.")
            print(f"\n❌ Error: Port {PORT} is already in use!")
            print("Try: sudo lsof -ti:8085 | xargs kill -9")
        else:
            logger.error(f"Server error: {e}")
            print(f"\n❌ Server error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
    finally:
        logger.info("Gullah Hearth Platform stopped")

if __name__ == "__main__":
    main()