from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from textblob import TextBlob
import spacy
import json
import os

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Secret key for session management

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Load knowledge base
def load_knowledge_base(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"questions": []}

# Load users
def load_users(file_path):
    try:
        with open(file_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"users": []}

# Normalize input
def normalize_input(user_input):
    normalized = user_input.strip().capitalize()
    tokens = [token.text for token in nlp(normalized)]
    return normalized, tokens

# Sentiment analysis
def get_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity, blob.sentiment.subjectivity

# Check for greetings
def is_greeting(user_input):
    greetings = ['hello', 'hi', 'hey']
    return any(greeting in user_input.lower() for greeting in greetings)

# Find best match for questions
def find_best_match(user_question, questions):
    user_tokens = set([token.text.lower() for token in nlp(user_question)])
    question_matches = {}

    for question in questions:
        question_tokens = set([token.text.lower() for token in nlp(question)])
        overlap = user_tokens.intersection(question_tokens)
        if overlap:
            question_matches[question] = len(overlap) / len(question_tokens)

    return max(question_matches, key=question_matches.get, default=None)

# Get bot response
def get_bot_response(user_input, knowledge_base):
    normalized_input, _ = normalize_input(user_input)
    best_match = find_best_match(normalized_input, [q['question'] for q in knowledge_base['questions']])

    if best_match:
        return next(q['answer'] for q in knowledge_base['questions'] if q['question'] == best_match)
    else:
        return "I don't know the answer. Can you teach me?"

# Save conversation
def save_conversation(conversation):
    with open('conversation.json', 'w') as file:
        json.dump(conversation, file)

# Load last conversation
def load_last_conversation():
    try:
        with open('conversation.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return []

# Home route
@app.route('/')
def home():
    if 'username' in session:
        return render_template('chat.html', last_conversation=load_last_conversation())
    return redirect(url_for('signin'))

# Sign-in route
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_users('users.json')

        # Check if the user exists and the password matches
        for user in users['users']:
            if user['username'] == username and user['password'] == password:
                session['username'] = username
                return redirect(url_for('home'))
        return render_template('signin.html', error="Invalid username or password.")
    return render_template('signin.html')

# Sign-out route
@app.route('/signout')
def signout():
    save_conversation(session.get('conversation', []))
    session.pop('username', None)
    session.pop('conversation', None)
    return redirect(url_for('signin'))

# API for chat interaction
@app.route('/chat', methods=['POST'])
def chat():
    if 'username' not in session:
        return jsonify({"response": "Please sign in first."})

    data = request.json
    user_input = data.get('message', '')

    if not user_input:
        return jsonify({"response": "Please enter a message."})

    knowledge_base = load_knowledge_base('knowledge_base.json')

    if is_greeting(user_input):
        response = "Hello! 😊 How can I assist you today?"
    else:
        sentiment_polarity, _ = get_sentiment(user_input)
        response = get_bot_response(user_input, knowledge_base)

    # Save the conversation in the session
    conversation = session.get('conversation', [])
    conversation.append({"user": user_input, "bot": response})
    session['conversation'] = conversation

    return jsonify({"response": response})

if __name__ == '__main__':
    # Use environment variables for configuration
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("DEBUG", "false").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug_mode)