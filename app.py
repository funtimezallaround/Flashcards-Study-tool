from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY', 'default-dev-key-change-in-prod')
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
    title = db.Column(db.String(150), default='My Flashcards')
    cards = db.relationship('Card', backref='user', lazy=True)
    topics = db.relationship('Topic', backref='user', lazy=True)


class Topic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)
    order = db.Column(db.Integer, default=0)
    children = db.relationship('Topic', backref=db.backref('parent', remote_side=[id]), lazy=True)
    cards = db.relationship('Card', backref='topic', lazy=True)


class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    front = db.Column(db.Text, nullable=False)
    back = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topic.id'), nullable=True)


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
            new_user = User(username=username,
                            password=generate_password_hash(password))

            db.session.add(new_user)
            db.session.commit()
            
            # Create Default Topic
            default_topic = Topic(name="My Flashcards", user_id=new_user.id, order=0)
            db.session.add(default_topic)
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
    topic_id = request.args.get('topic_id')
    query = Card.query.filter_by(user_id=current_user.id)
    
    # Helper to get all descendant IDs including self
    def get_topic_scope(root_id):
        all_topics = Topic.query.filter_by(user_id=current_user.id).all()
        # Build map
        children_map = {}
        for t in all_topics:
            if t.parent_id not in children_map:
                children_map[t.parent_id] = []
            children_map[t.parent_id].append(t.id)
            
        scope = [root_id]
        stack = [root_id]
        while stack:
            curr = stack.pop()
            if curr in children_map:
                children = children_map[curr]
                scope.extend(children)
                stack.extend(children)
        return scope

    if topic_id:
        # Include subtopics
        target_ids = get_topic_scope(int(topic_id))
        query = query.filter(Card.topic_id.in_(target_ids))
    else:
        # If no topic specified, look for "My Flashcards"
        default_topic = Topic.query.filter_by(user_id=current_user.id, name="My Flashcards").first()
        if default_topic:
             # Cards in default topic tree OR orphans
             target_ids = get_topic_scope(default_topic.id)
             from sqlalchemy import or_
             query = query.filter(or_(Card.topic_id.in_(target_ids), Card.topic_id == None))
        else:
             # No default topic found? Only return orphans
             query = query.filter_by(topic_id=None)

    cards = query.all()
    return jsonify([{
        'id': c.id,
        'category': c.category,
        'front': c.front,
        'back': c.back,
        'topic_id': c.topic_id
    } for c in cards])


@app.route('/api/cards', methods=['POST'])
@login_required
def add_card():
    data = request.json
    topic_id = data.get('topic_id')
    
    # Validation: Ensure topic belongs to user
    if topic_id:
        topic = Topic.query.get(topic_id)
        if not topic or topic.user_id != current_user.id:
            return jsonify({'error': 'Invalid topic'}), 403
    else:
         # Fallback to default
         default_topic = Topic.query.filter_by(user_id=current_user.id, name="My Flashcards").first()
         topic_id = default_topic.id if default_topic else None

    new_card = Card(
        category=data.get('category', 'General'),
        front=data.get('front'),
        back=data.get('back'),
        user_id=current_user.id,
        topic_id=topic_id
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


@app.route('/api/cards/<int:id>', methods=['PUT'])
@login_required
def update_card(id):
    card = Card.query.get_or_404(id)
    if card.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    card.category = data.get('category', card.category)
    card.front = data.get('front', card.front)
    card.back = data.get('back', card.back)
    
    if 'topic_id' in data:
        topic_id = data['topic_id']
        if topic_id is None:
            # Fallback to default topic if removing from a specific one
            default_topic = Topic.query.filter_by(user_id=current_user.id, name="My Flashcards").first()
            card.topic_id = default_topic.id if default_topic else None
        else:
            # Validate ownership
            topic = Topic.query.get(topic_id)
            if topic and topic.user_id == current_user.id:
                card.topic_id = topic_id
            else:
                return jsonify({'error': 'Invalid topic'}), 400

    db.session.commit()
    return jsonify({'message': 'Card updated'})


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

            forced_topic_id = request.form.get('topic_id')
            if forced_topic_id:
                try:
                    forced_topic_id = int(forced_topic_id)
                except:
                    forced_topic_id = None

            count = 0
            for card_data in cards_data:
                front = None
                back = None
                if 'prompt' in card_data and 'completion' in card_data:
                     front = card_data['prompt']
                     back = card_data['completion']
                elif 'front' in card_data and 'back' in card_data:
                     front = card_data['front']
                     back = card_data['back']
                
                if front and back:
                    # Determine topic
                    card_topic_id = forced_topic_id
                    
                    # If not forced, check JSON for topic name
                    if card_topic_id is None and 'topic' in card_data and card_data['topic']:
                        topic_name = card_data['topic']
                        topic = Topic.query.filter_by(user_id=current_user.id, name=topic_name).first()
                        if not topic:
                            topic = Topic(name=topic_name, user_id=current_user.id, order=999)
                            db.session.add(topic)
                            # We need to commit here to get the new topic ID
                            db.session.commit()
                        card_topic_id = topic.id
                    
                    # Fallback to default
                    if card_topic_id is None:
                         default_topic = Topic.query.filter_by(user_id=current_user.id, name="My Flashcards").first()
                         card_topic_id = default_topic.id if default_topic else None

                    new_card = Card(
                        category=card_data.get('category', 'Imported'),
                        front=front,
                        back=back,
                        user_id=current_user.id,
                        topic_id=card_topic_id
                    )
                    db.session.add(new_card)
                    count += 1

            db.session.commit()
            return jsonify({'message': f'Successfully imported {count} cards!'}), 201
        except Exception as e:
            return jsonify({'error': f'Failed to process file: {str(e)}'}), 500

# Topic Routes

@app.route('/api/topics/reorder', methods=['PUT'])
@login_required
def reorder_topics():
    data = request.json
    if not isinstance(data, list):
        return jsonify({'error': 'Invalid data'}), 400
        
    for item in data:
        topic = Topic.query.get(item['id'])
        if topic and topic.user_id == current_user.id:
            topic.order = item['order']
            if 'parent_id' in item:
                # Prevent circular parent assignment
                if item['parent_id'] != topic.id: 
                    topic.parent_id = item['parent_id']
            
    db.session.commit()
    return jsonify({'message': 'Topics reordered'})

@app.route('/api/topics', methods=['GET'])
@login_required
def get_topics():
    topics = Topic.query.filter_by(user_id=current_user.id).order_by(Topic.order).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'parent_id': t.parent_id,
        'order': t.order
    } for t in topics])

@app.route('/api/topics', methods=['POST'])
@login_required
def create_topic():
    data = request.json
    parent_id = data.get('parent_id')
    name = data.get('name')
    
    # Validate parent if exists
    if parent_id:
        parent = Topic.query.get(parent_id)
        if not parent or parent.user_id != current_user.id:
            return jsonify({'error': 'Invalid parent'}), 400
            
    new_topic = Topic(
        name=name,
        user_id=current_user.id,
        parent_id=parent_id,
        order=999
    )
    db.session.add(new_topic)
    db.session.commit()
    return jsonify({'message': 'Topic created', 'id': new_topic.id})

@app.route('/api/topics/<int:id>', methods=['PUT'])
@login_required
def update_topic(id):
    topic = Topic.query.get_or_404(id)
    if topic.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    if 'name' in data:
        topic.name = data['name']
    
    if 'order' in data:
        topic.order = data['order']
        
    if 'parent_id' in data:
        new_parent = data['parent_id']
        if new_parent == topic.id:
             return jsonify({'error': 'Cannot set parent to self'}), 400
        topic.parent_id = new_parent

    db.session.commit()
    return jsonify({'message': 'Topic updated'})

@app.route('/api/topics/<int:id>', methods=['DELETE'])
@login_required
def delete_topic(id):
    topic = Topic.query.get_or_404(id)
    if topic.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    def delete_recursive(t):
        children = Topic.query.filter_by(parent_id=t.id).all()
        for child in children:
            delete_recursive(child)
        cards = Card.query.filter_by(topic_id=t.id).all()
        for card in cards:
            db.session.delete(card)
        db.session.delete(t)
        
    delete_recursive(topic)
    db.session.commit()
    return jsonify({'message': 'Topic deleted'})

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            new_username = request.form.get('username')
            if new_username and new_username != current_user.username:
                existing = User.query.filter_by(username=new_username).first()
                if existing:
                    flash('Username already taken.', 'error')
                else:
                    current_user.username = new_username
                    db.session.commit()
                    flash('Username updated successfully.', 'success')

        elif action == 'update_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not check_password_hash(current_user.password, current_password):
                flash('Incorrect current password.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                current_user.password = generate_password_hash(new_password)
                db.session.commit()
                flash('Password updated successfully.', 'success')

    return render_template('account.html')


@app.route('/account/export')
@login_required
def export_cards():
    cards = Card.query.filter_by(user_id=current_user.id).all()
    cards_data = []
    for c in cards:
        card_item = {
            'category': c.category,
            'front': c.front,
            'back': c.back
        }
        if c.topic:
            card_item['topic'] = c.topic.name
        cards_data.append(card_item)

    import json
    from flask import Response

    return Response(
        json.dumps(cards_data, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=my_flashcards.json"}
    )


@app.route('/api/user/title', methods=['PUT'])
@login_required
def update_title():
    data = request.json
    new_title = data.get('title')
    if new_title:
        current_user.title = new_title
        db.session.commit()
        return jsonify({'message': 'Title updated successfully'})
    return jsonify({'error': 'No title provided'}), 400


# Utility for creating DB


def create_db():
    with app.app_context():
        db.create_all()
        # Migration logic
        inspector = db.inspect(db.engine)
        
        # User title migration
        user_columns = [c['name'] for c in inspector.get_columns('user')]
        if 'title' not in user_columns:
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE user ADD COLUMN title VARCHAR(150) DEFAULT "My Flashcards"'))
                conn.commit()
            print("Added 'title' column to User table.")

        # Card topic_id migration
        card_columns = [c['name'] for c in inspector.get_columns('card')]
        if 'topic_id' not in card_columns:
            with db.engine.connect() as conn:
                # SQLite doesn't support adding foreign key constraints easily via ALTER TABLE
                # So we just add the integer column. SQLAlchemy will handle the relationship logic.
                conn.execute(db.text('ALTER TABLE card ADD COLUMN topic_id INTEGER'))
                conn.commit()
            print("Added 'topic_id' column to Card table.")


if __name__ == '__main__':
    create_db()
    # Host 0.0.0.0 allows access from local network
    app.run(debug=True, host='0.0.0.0', port=5000)
