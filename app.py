from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, Namespace
import time
import threading
from flask_socketio import SocketIO
import threading
import webbrowser
from flask_cors import CORS
from rag_ui_flows import fetch_relevant_workflow

# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
socketio = SocketIO(app, cors_allowed_origins="*", ping_interval=25000, ping_timeout=60000)  # Allow all origins for WebSocket

@app.route('/')
def index():
    """Serve the HTML UI."""
    return render_template('demo_modal_test.html')

@app.route("/chat-workflows", methods=["POST"])
def chat():
    data = request.json
    user_message = data.get("message", "")
    print(f"Received message: {user_message}")
    work_flow = fetch_relevant_workflow(user_message, 1)
    return jsonify(work_flow)

class MyNamespace(Namespace):
    def on_connect(self):
        print('Client connected to /test namespace')
        print(f'Current clients: {self.server.manager.rooms["/test"]}')

    def on_disconnect(self):
        print('Client disconnected from /test namespace')

    def on_highlight(self, data):
        print(f"Received highlight event with data: {data}")
        # Re-emit to all clients in this namespace
        self.emit('highlight', data, room=None, namespace='/test')
    
    def on_ping(self):
        print('Received ping from client')
        self.emit('pong')

socketio.on_namespace(MyNamespace('/test'))

def launch_browser():
    """Launch the UI in the default browser after a short delay."""
    time.sleep(2)  # Give the server time to start
    webbrowser.open('http://127.0.0.1:5000')

def send_highlight_action(element_id):
    """Send a highlight action to all connected clients in the '/test' namespace."""
    with app.app_context():  # Ensure Flask app context
        print(f"🔥 Sending highlight event for element: {element_id}")
        socketio.emit('highlight', {'id': element_id}, namespace='/test')
        print(f"🔥 Sent highlight event for element: {element_id}")

def background_task():
    # while True:
    socketio.sleep(5)  # Non-blocking sleep
    send_highlight_action('idChatbot')

# if __name__ == '__main__':
#     # Launch the browser in a separate thread
#     threading.Thread(target=launch_browser, daemon=True).start()

#     # Start a background task to send WebSocket events (for testing)
#     threading.Thread(target=background_task, daemon=True).start()

#     # Start the Flask-SocketIO server
#     socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False)


if __name__ == '__main__':
    threading.Thread(target=launch_browser, daemon=True).start()
    socketio.start_background_task(background_task)  # Properly managed background task
    socketio.run(app, host='127.0.0.1', port=5000, debug=True, use_reloader=False)