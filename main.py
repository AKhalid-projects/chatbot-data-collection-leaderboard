from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chatbot_data_collection.db'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    questions_added = db.relationship('Question', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_text = db.Column(db.String(300), nullable=False)
    answer_text = db.Column(db.String(300), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    answer_text = db.Column(db.Text, nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey(
        'question.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


def create_database(app):
    with app.app_context():
        db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid credentials")  # Add this line to display a message
            return redirect(url_for('login'))
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another one.')
            return redirect(url_for('register'))
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('dashboard'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        data = request.get_json()
        question_text = data['question']
        answer_text = data['answer']
        question = Question(question_text=question_text, user=current_user)
        answer = Answer(answer_text=answer_text,
                        question=question, user=current_user)
        db.session.add(question)
        db.session.add(answer)
        db.session.commit()
        return jsonify(status='success')
    return render_template('dashboard.html')


@app.route('/add_question', methods=['POST'])
@login_required
def add_question():
    if request.method == 'POST':
        question_text = request.form.get('question')
        answer_text = request.form.get('answer')

        # Create a new Question instance
        new_question = Question(
            question_text=question_text, answer_text=answer_text, user_id=current_user.id)

        # Add the new_question instance to the database session
        db.session.add(new_question)

        # Commit the session to save the changes
        db.session.commit()

        flash('Question and answer added successfully.', 'success')
        return redirect(url_for('dashboard'))


@app.route('/leaderboard', methods=['GET'])
@login_required
def leaderboard():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    questions = Question.query.order_by(
        Question.id.desc()).paginate(page=page, per_page=per_page)

    # Query the top 3 users who submitted the most questions
    top_users = db.session.query(User, func.count(Question.id).label('total_questions'))\
        .join(Question)\
        .group_by(User)\
        .order_by(func.count(Question.id).desc())\
        .limit(3)\
        .all()

    return render_template('leaderboard.html', questions=questions, top_users=top_users, enumerate=enumerate)


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


if __name__ == '__main__':
    create_database(app)
    app.run(debug=True)
