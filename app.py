from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-dev-key-change-in-prod')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///flashcards.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    cards = db.relationship('Card', backref='user', lazy=True)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    front = db.Column(db.Text, nullable=False)
    back = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', 'error')
        else:
            # Using simple hash for demo if needed, but generate_password_hash defaults are good.
            new_user = User(username=username, password=generate_password_hash(password))
            
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# API Routes for React
@app.route('/api/cards', methods=['GET'])
@login_required
def get_cards():
    cards = Card.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': c.id,
        'category': c.category,
        'front': c.front,
        'back': c.back
    } for c in cards])

@app.route('/api/cards', methods=['POST'])
@login_required
def add_card():
    data = request.json
    new_card = Card(
        category=data.get('category', 'General'),
        front=data.get('front'),
        back=data.get('back'),
        user_id=current_user.id
    )
    db.session.add(new_card)
    db.session.commit()
    return jsonify({'message': 'Card added!', 'id': new_card.id}), 201

@app.route('/api/cards/<int:id>', methods=['DELETE'])
@login_required
def delete_card(id):
    card = Card.query.get_or_404(id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(card)
    db.session.commit()
    return jsonify({'message': 'Card deleted'})

@app.route('/api/cards/import', methods=['POST'])
@login_required
def import_cards():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file:
        import json
        try:
            cards_data = json.load(file)
            if not isinstance(cards_data, list):
                 return jsonify({'error': 'Invalid JSON format. Expected a list of cards.'}), 400
            
            count = 0
            for card_data in cards_data:
                if 'front' in card_data and 'back' in card_data:
                    new_card = Card(
                        category=card_data.get('category', 'Imported'),
                        front=card_data['front'],
                        back=card_data['back'],
                        user_id=current_user.id
                    )
                    db.session.add(new_card)
                    count += 1
            
            db.session.commit()
            return jsonify({'message': f'Successfully imported {count} cards!'}), 201
        except Exception as e:
            return jsonify({'error': f'Failed to process file: {str(e)}'}), 500

# Utility for creating DB
def create_db():
    with app.app_context():
        db.create_all()

if __name__ == '__main__':
    create_db()
    # Host 0.0.0.0 allows access from local network
    app.run(debug=True, host='0.0.0.0', port=5000)
