from flask import Flask, render_template, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import Tool, initialize_agent
from pydantic import BaseModel
import os
import uuid
from pydantic import BaseModel, Field
from langchain.agents import tool

# Flask app setup
app = Flask(__name__)
app.secret_key = 'mississippi6269'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Pydantic model for AI Agent input
class QueryInput(BaseModel):
    "Extracts story from user input if present"
    query: str = Field(..., description="story to be titled")

# Example AI tool
@tool
def example_tool(input_text: str) -> str:
    """
    This function takes an input string and returns it formatted as a one word title.

    Args:
        input_text (str): The input text to be formatted as a title.

    Returns:
        str: The formatted one word title string.
    """
    return f"Title: {input_text}"

# Initialize LangChain agent
llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key="AIzaSyDlm5KhhPDVbGo_Hsvp27-DrlUwER9IrYI"
        )
agent = initialize_agent([example_tool], llm, agent="zero-shot-react-description")

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect('/chat')
    return redirect('/login')

# Modify the User model to include first name and last name
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password = db.Column(db.String(150), nullable=False)

# Route to delete the users.db file
@app.route('/delete_db')
def delete_db():
    if os.path.exists('users.db'):
        os.remove('users.db')
        return 'Database deleted!'
    return 'Database file not found!'

# Update the registration route to handle first name and last name
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=email).first():
            return 'User already exists!'

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(first_name=first_name, last_name=last_name, username=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')

# Templates setup (register.html, login.html, chat.html)
register_html = """
<!doctype html>
<html>
<head>
    <title>Register</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1 class="center-align">Register</h1>
        <form method="post" class="col s12">
            <div class="row">
                <div class="input-field col s6">
                    <input id="first_name" type="text" name="first_name" class="validate" required>
                    <label for="first_name">First Name</label>
                </div>
                <div class="input-field col s6">
                    <input id="last_name" type="text" name="last_name" class="validate" required>
                    <label for="last_name">Last Name</label>
                </div>
            </div>
            <div class="row">
                <div class="input-field col s12">
                    <input id="email" type="email" name="email" class="validate" required>
                    <label for="email">Email</label>
                </div>
            </div>
            <div class="row">
                <div class="input-field col s12">
                    <input id="password" type="password" name="password" class="validate" required>
                    <label for="password">Password</label>
                </div>
            </div>
            <div class="row center-align">
                <button type="submit" class="btn waves-effect waves-light">Register</button>
            </div>
        </form>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect('/chat')

        return 'Invalid credentials!'

    return render_template('login.html')

login_html = """
<!doctype html>
<html>
<head>
    <title>Login</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css" rel="stylesheet">
</head>
<body>
    <div class="container">
        <h1 class="center-align">Login</h1>
        <form method="post" class="col s12">
            <div class="row">
                <div class="input-field col s12">
                    <input id="email" type="email" name="username" class="validate" required>
                    <label for="email">Email</label>
                </div>
            </div>
            <div class="row">
                <div class="input-field col s12">
                    <input id="password" type="password" name="password" class="validate" required>
                    <label for="password">Password</label>
                </div>
            </div>
            <div class="row center-align">
                <button type="submit" class="btn waves-effect waves-light">Login</button>
            </div>
        </form>
    </div>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
"""

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/login')

class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chat_id = db.Column(db.String, nullable=False, unique=True)

class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_id = db.Column(db.String, db.ForeignKey('chat.chat_id'), nullable=False)
    message = db.Column(db.String, nullable=False)
    response = db.Column(db.String, nullable=False)
    chat = db.relationship('Chat', backref=db.backref('history', lazy=True))

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    chat_id = request.args.get('chat_id')

    if request.method == 'POST':
        user_input = request.json.get('query')
        try:
            flag = False
            if not chat_id or chat_id == 'None':
                chat_id = str(uuid.uuid4())
                chat = Chat(user_id=user_id, chat_id=chat_id)
                db.session.add(chat)
                db.session.commit()
                flag = True
            result = agent.run(QueryInput(query=user_input).query)
            chat_history = ChatHistory(chat_id=chat_id, message=user_input, response=result)
            db.session.add(chat_history)
            db.session.commit()
            if flag:
                return jsonify({"chat_id": chat_id})
                
            return jsonify({"response": result})
        except Exception as e:
            return jsonify({"error": str(e)})

    chat_history = ChatHistory.query.filter_by(chat_id=chat_id).all()
    history = [{"message": chat.message, "response": chat.response} for chat in chat_history]
    user_chats = Chat.query.filter_by(user_id=user_id).all()
    return render_template('chat.html', history=history, chat_id=chat_id, user_chats=user_chats)

chat_html = """
<!doctype html>
<html>
<head>
    <title>Chat</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css" rel="stylesheet">
    <style>
        body {
            display: flex;
            height: 100vh;
            background-color: #f5f5f5;
        }
        .chat-container {
            flex: 1;
            display: flex;
            flex-direction: column;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            transition: margin-left 0.3s;
        }
        #chat-box {
            flex: 1;
            overflow-y: scroll;
            border: 1px solid #ddd;
            padding: 10px;
            margin-bottom: 20px;
        }
        .message {
            margin-bottom: 10px;
        }
        .message strong {
            color: #007bff;
        }
        .side-nav {
            width: 250px;
            background: #fff;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            padding: 20px;
            position: fixed;
            left: 0;
            top: 0;
            bottom: 0;
            overflow-y: auto;
            transform: translateX(-100%);
            transition: transform 0.3s;
        }
        .side-nav.hidden {
            transform: translateX(0);
        }
        .side-nav a {
            display: block;
            margin-bottom: 10px;
        }
        .toggle-nav {
            position: fixed;
            top: 10px;
            left: 20px;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <button class="toggle-nav btn waves-effect waves-light">Toggle Nav</button>
    <div class="side-nav">
        <br><br>
        <a href="/chat" class="btn waves-effect waves-light green">New Chat</a>
        {% for chat in user_chats %}
            <a href="/chat?chat_id={{ chat.chat_id }}" class="btn waves-effect waves-light blue">
                {{ chat.history[0].message if chat.history else 'Chat ' ~ chat.chat_id }}
            </a>
        {% endfor %}
        <a href="/logout" class="btn waves-effect waves-light red">Log Out</a>
    </div>
    <div class="chat-container">
        <h4 class="center-align">Chat Interface</h4>
        <div id="chat-box">
            {% for entry in history %}
                <div class="message"><strong>You:</strong> {{ entry.message }}</div>
                <div class="message"><strong>AI:</strong> {{ entry.response }}</div>
            {% endfor %}
        </div>
        <form id="chat-form">
            <div class="row">
                <div class="input-field col s10">
                    <input type="text" id="query" placeholder="Enter your message" class="validate" required>
                </div>
                <div class="input-field col s2">
                    <button type="submit" class="btn waves-effect waves-light">Send</button>
                </div>
            </div>
            <div class="file-field input-field">
                <div class="btn">
                    <span>Attach File</span>
                    <input type="file" id="file-input">
                </div>
                <div class="file-path-wrapper">
                    <input class="file-path validate" type="text" placeholder="Upload file">
                </div>
            </div>
        </form>
    </div>
    <script>
        const form = document.getElementById('chat-form');
        const chatBox = document.getElementById('chat-box');
        const toggleNavButton = document.querySelector('.toggle-nav');
        const sideNav = document.querySelector('.side-nav');
        const chatContainer = document.querySelector('.chat-container');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const queryInput = document.getElementById('query');
            const query = queryInput.value;
            const response = await fetch('/chat?chat_id={{ chat_id }}', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            });
            const data = await response.json();
            if (data.chat_id) {
                window.location.href = `/chat?chat_id=${data.chat_id}`;
            }
            chatBox.innerHTML += `<div class="message"><strong>You:</strong> ${query}</div>`;
            chatBox.innerHTML += `<div class="message"><strong>AI:</strong> ${data.response || data.error}</div>`;
            chatBox.scrollTop = chatBox.scrollHeight;
            queryInput.value = ''; // Clear the input field
        });

        toggleNavButton.addEventListener('click', () => {
            sideNav.classList.toggle('hidden');
            if (sideNav.classList.contains('hidden')) {
                chatContainer.style.marginLeft = '250px';
            } else {
                chatContainer.style.marginLeft = '0px';
            }
        });
    </script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
</body>
</html>
"""

# Save templates to files
os.makedirs('templates', exist_ok=True)
with open('templates/register.html', 'w') as f:
    f.write(register_html)
with open('templates/login.html', 'w') as f:
    f.write(login_html)
with open('templates/chat.html', 'w') as f:
    f.write(chat_html)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
