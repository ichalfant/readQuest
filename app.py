from datetime import datetime
import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Enum, create_engine, func, text
from werkzeug.security import generate_password_hash, check_password_hash
from flask import flash
from flask import current_app

app = Flask(__name__)
app.secret_key = 'your_secret_key'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Set isolation level to RAUTOCOMMIT in SQLAlchemy engine options
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'isolation_level': 'AUTOCOMMIT'
}

# Initialize the SQLAlchemy object
db = SQLAlchemy(app)

'''
DATABASE MODEL
'''
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Relationships
    books = db.relationship('UserBook', backref='user', lazy=True)
    
class Book(db.Model):
    __tablename__ = 'books'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    cover_image_path = db.Column(db.String(255), nullable=True)
    date_added = db.Column(db.DateTime, default=db.func.current_timestamp())
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Constraint to prevent duplicate book entries
    __table_args__ = (db.UniqueConstraint('title', 'author'),)

    # Relationships
    user_books = db.relationship('UserBook', backref='associated_book', lazy=True)

class UserBook(db.Model):
    __tablename__ = 'user_books'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id'), nullable=False)

    read_instances = db.relationship('ReadInstance', backref='user_book', lazy=True)
    

class ReadInstance(db.Model):
    __tablename__ ='read_instances'

    id = db.Column(db.Integer, primary_key=True)
    user_book_id = db.Column(db.Integer, db.ForeignKey('user_books.id'), nullable=False)

    status = db.Column(Enum('to read', 'in progress', 'completed', 'dropped'), nullable=False)
    format = db.Column(Enum('paperback', 'hardcover', 'e-book', 'audiobook'), nullable=False)

    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)
    drop_date = db.Column(db.DateTime, nullable=True)
    added_to_read_date = db.Column(db.DateTime, nullable=True)

class Goal(db.Model):
    __tablename__ = 'goals'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    #column for date time year
    year = db.Column(db.Integer, nullable=False)
    target_books = db.Column(db.Integer, nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'year', name='uq_user_year'),)
'''
ROUTING
'''

@app.route('/')
def index():
    if 'user_id' not in session or 'user' not in session:
        return redirect(url_for('login'))
    
    current_year = datetime.now().year
    user_id = session.get('user_id')

    stmt = text("""
        SELECT ri.id AS reading_instance_id, ub.id AS user_book_id, b.title, b.author, b.cover_image_path, ri.status, ri.format
        FROM read_instances ri
        JOIN user_books ub ON ri.user_book_id = ub.id
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = :user_id AND ri.status = 'in progress'
        LIMIT 5
    """)

    results = db.session.execute(stmt, {'user_id': user_id}).fetchall()

    reading_instances_in_progress = [
        {
            'reading_instance_id': row.reading_instance_id,
            'user_book_id': row.user_book_id, 
            'title': row.title, 
            'author': row.author, 
            'cover_image_path': row.cover_image_path, 
            'status': row.status, 
            'format': row.format
        } 
        for row in results]
    existing_goal = Goal.query.filter_by(user_id=user_id, year=current_year).first()
    return render_template('index.html', username=session.get('user'), reading_instances_in_progress=reading_instances_in_progress, existing_goal=existing_goal)

@app.route('/api/goal', methods=['GET'])
def get_goal():
    user_id = session.get('user_id')
    current_year = datetime.now().year
    current_goal = Goal.query.filter_by(user_id=user_id, year=current_year).first()
    if current_goal:
        return jsonify(goal=current_goal.target_books)
    else:
        return jsonify(goal=None)
    
@app.route('/api/goal', methods=['POST'])
def set_goal():
    user_id = session.get('user_id')
    data = request.get_json()
    goal_value = data.get('goal')
    current_year = datetime.now().year

    if not isinstance(goal_value, int) or goal_value < 0:
        return jsonify({'success': False, 'message': 'Invalid goal value.'}), 400
    
    existing_goal = Goal.query.filter_by(user_id=user_id, year=current_year).first()

    if existing_goal:
        existing_goal.target_books = goal_value
    else:
        new_goal = Goal(user_id=user_id, year=current_year, target_books=goal_value)
        db.session.add(new_goal)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Goal set successfully.', 'goal': goal_value})

@app.route('/api/finished_books', methods=['GET'])
def get_finished_books():
    user_id = session.get('user_id')

    if not user_id:
        return jsonify({'success': False, 'message': 'User not logged in.'}), 403
    
    stmt = text("""
        SELECT b.id, b.title, b.author, ri.status, ri.format
        FROM books b
        JOIN user_books ub ON b.id = ub.book_id
        JOIN read_instances ri ON ub.id = ri.user_book_id
        WHERE ub.user_id = :user_id AND ri.status = 'completed'
    """)
    result = db.session.execute(stmt, {'user_id': user_id}).fetchall()

    finished_books = [row[0] for row in result]
    finished_count = len(finished_books)

    return jsonify({'success': True, 'finished_count': finished_count, 'finished_books': finished_books})

@app.route('/update_reading_instance/<int:reading_instance_id>', methods=['GET', 'POST'])
def update_reading_instance(reading_instance_id):
    if 'user' not in session or 'user_id' not in session:
        return redirect(url_for('login'))
    
    read_instance = ReadInstance.query.get(reading_instance_id)

    if not read_instance:
        flash('Reading instance not found.')
    
    if read_instance.user_book.user_id != session['user_id']:
        flash('You are not authorized to edit this reading instance.')
    
    if request.method == 'POST':
        status = request.form.get('status')
        format = request.form.get('format')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        drop_date = request.form.get('drop_date')
        added_to_read_date = request.form.get('added_to_read_date')

        try:
            read_instance.status = status
            read_instance.format = format

            if status == 'in progress':
                if start_date:
                    read_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
                else:
                    read_instance.start_date = db.func.current_date()
            elif status == 'to read':
                if added_to_read_date:
                    read_instance.added_to_read_date = datetime.strptime(added_to_read_date, "%Y-%m-%d")
                else:
                    read_instance.added_to_read_date = db.func.current_date()
            elif status == 'completed':
                if start_date:
                    read_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
                else:
                    read_instance.start_date = db.func.current_date()
                if end_date:
                    read_instance.end_date = datetime.strptime(end_date, "%Y-%m-%d")
                else:
                    read_instance.end_date = db.func.current_date()
            elif status == 'dropped':
                if start_date:
                    read_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
                else:
                    read_instance.start_date = db.func.current_date()
                if drop_date:
                    read_instance.drop_date = datetime.strptime(drop_date, "%Y-%m-%d")
                else:
                    read_instance.drop_date = db.func.current_date()

            db.session.commit()
            flash('Reading instance updated successfully!')
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}")
        finally:
            db.session.close()

        return redirect(request.referrer or url_for('library'))
    
    return render_template('update_reading_instance.html', read_instance=read_instance)

@app.route('/delete_reading_instance/<int:reading_instance_id>', methods=['POST'])
def delete_reading_instance(reading_instance_id):
    if 'user' not in session or 'user_id' not in session:
        return redirect(url_for('login'))
    
    read_instance = ReadInstance.query.get(reading_instance_id)

    if not read_instance:
        flash('Reading instance not found.')
        return redirect(url_for('library'))
    if read_instance.user_book.user_id != session['user_id']:
        flash('You are not authorized ot delete this reading instance.')
        return redirect(url_for('library'))
    
    try:
        db.session.delete(read_instance)
        db.session.commit()
        flash('Reading instance deleted successfully!')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred while deleting the reading instance: {str(e)}')
    return redirect(url_for('library'))
'''
@app.route('/update-reading-instance/<int:reading_instance_id>', methods=['POST']) 
def update_reading_instance(reading_instance_id):
    data = request.get_json()
    status = data.get('status')
    format = data.get('format')

    start_date = data.get('start_date')
    end_date = data.get('end_date')
    drop_date = data.get('drop_date')
    added_to_read_date = data.get('added_to_read_date')

    def format_date(date_string):
        try:
            if date_string:
                return datetime.strptime(date_string, '%Y-%m-%d').date()
            return None
        except ValueError:
            return None

    reading_instance = ReadInstance.query.get(reading_instance_id)

    try:
        db.session.begin()
        if status:
            reading_instance.status = status

        if status == 'in progress':
            if start_date:
                reading_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                reading_instance.start_date = db.func.current_date()
        elif status == 'to read':
            if added_to_read_date:
                reading_instance.added_to_read_date = datetime.strptime(added_to_read_date, "%Y-%m-%d")
            else:
                reading_instance.added_to_read_date = db.func.current_date()
        elif status == 'completed':
            if start_date:
                reading_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                reading_instance.start_date = db.func.current_date()
            if end_date:
                reading_instance.end_date = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                reading_instance.end_date = db.func.current_date()
        elif status == 'dropped':
            if start_date:
                reading_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                reading_instance.start_date = db.func.current_date()
            if drop_date:
                reading_instance.drop_date = datetime.strptime(drop_date, "%Y-%m-%d")
            else:
                reading_instance.drop_date = db.func.current_date()
        if format:
            reading_instance.format = format

        db.session.commit()
        flash('Reading instance updated successfully!')

    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred: {str(e)}")
    return jsonify({'success': True, 'message': 'Read updated successfully.'})
'''
'''
@app.route('/delete-reading-instance/<int:reading_instance_id>', methods=['DELETE'])
def delete_reading_instance(reading_instance_id):
    user_id = session.get('user_id')

    read_instance = ReadInstance.query.get(reading_instance_id)
    if not read_instance:
        return jsonify({'success': False, 'message': 'Reading instance not found.'}), 404
    
    user_book = UserBook.query.get(read_instance.user_book_id)
    if user_book.user_id != user_id:
        return jsonify({'success': False, 'message': 'Unauthorized to delete this reading instance.'}), 403
    
    db.session.delete(read_instance)
    db.session.commit()

    remaining_instance = ReadInstance.query.filter_by(user_book_id=user_book.id).count()
    if remaining_instance == 0:
        db.session.delete(user_book)
        db.session.commit()

    return jsonify({'success': True, 'message': 'Reading instance deleted successfully.'})
''' 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user'] = username
            return redirect(url_for('index'))
        else:
            if not user:
                flash('Account not found. Please check your username and password.', 'error')
            elif not check_password_hash(user.password_hash, password):
                flash('Incorrect password. Please try again.', 'error')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        hashed_password = generate_password_hash(password)

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.', 'error')
            return redirect(url_for('signup'))
        
        new_user = User(username=username, password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/library')
def library():
    if 'user_id' not in session or 'user' not in session:
        return redirect(url_for('login'))
    username = session.get('user')
    user_id = session.get('user_id')

    def parse_date(date_string):
    # Strip any time or other characters from the string if necessary
        if date_string:
            date_string = date_string.split()[0]  # Take only the date part (if there is a time part)
            return datetime.strptime(date_string, '%Y-%m-%d')
        return None

    stmt_in_progress = text("""
        SELECT ri.id AS reading_instance_id, ub.id AS user_book_id, b.title, b.author, b.cover_image_path, ri.status, ri.format, ri.start_date
        FROM read_instances ri
        JOIN user_books ub ON ri.user_book_id = ub.id
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = :user_id AND ri.status = 'in progress'
        ORDER BY ri.start_date DESC
        LIMIT 5
    """)

    stmt_in_progress_results = db.session.execute(stmt_in_progress, {'user_id': user_id}).fetchall()
    books_in_progress = [
        {
        'reading_instance_id': row.reading_instance_id,
        'user_book_id': row.user_book_id, 
        'title': row.title, 
        'author': row.author, 
        'cover_image_path': row.cover_image_path, 
        'status': row.status, 
        'format': row.format, 
        'start_date': parse_date(row.start_date)
        } 
        for row in stmt_in_progress_results]

    stmt_to_read = text("""
        SELECT ri.id AS reading_instance_id, ub.id AS user_book_id, b.title, b.author, b.cover_image_path, ri.status, ri.format, ri.added_to_read_date
        FROM read_instances ri
        JOIN user_books ub ON ri.user_book_id = ub.id
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = :user_id AND ri.status = 'to read'
        ORDER BY ri.added_to_read_date DESC
        LIMIT 5
    """)

    stmt_to_read_results = db.session.execute(stmt_to_read, {'user_id': user_id}).fetchall()
    books_to_read = [
        {
        'reading_instance_id': row.reading_instance_id, 
        'user_book_id': row.user_book_id,
        'title': row.title, 
        'author': row.author, 
        'cover_image_path': row.cover_image_path, 
        'status': row.status, 
        'format': row.format, 
        'added_to_read_date': parse_date(row.added_to_read_date)
        } 
        for row in stmt_to_read_results]

    stmt_completed = text("""
        SELECT ri.id AS reading_instance_id, ub.id AS user_book_id, b.title, b.author, b.cover_image_path, ri.status, ri.format, ri.start_date, ri.end_date
        FROM read_instances ri
        JOIN user_books ub ON ri.user_book_id = ub.id
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = :user_id AND ri.status = 'completed'
        ORDER BY ri.end_date DESC
        LIMIT 5
    """)

    stmt_completed_results = db.session.execute(stmt_completed, {'user_id': user_id}).fetchall()
    books_completed = [
        {
        'reading_instance_id': row.reading_instance_id, 
        'user_book_id': row.user_book_id,
        'title': row.title, 
        'author': row.author, 
        'cover_image_path': row.cover_image_path, 
        'status': row.status, 
        'format': row.format, 
        'start_date': parse_date(row.start_date), 
        'end_date': parse_date(row.end_date)
        } 
        for row in stmt_completed_results]
    
    return render_template('library.html', username=username, books_in_progress=books_in_progress, books_to_read=books_to_read, books_completed=books_completed)

@app.route('/see-more/<status>', methods=['GET'])
def see_more(status):
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    def parse_date(date_string):
    # Strip any time or other characters from the string if necessary
        if date_string:
            date_string = date_string.split()[0]  # Take only the date part (if there is a time part)
            return datetime.strptime(date_string, '%Y-%m-%d')
        return None
    
    offset = (page - 1) * per_page

    stmt = text("""
        SELECT ri.id AS reading_instance_id, ub.id AS user_book_id, b.title, b.author, b.cover_image_path, ri.status, ri.format,
            ri.start_date, ri.end_date, ri.drop_date, ri.added_to_read_date
        FROM read_instances ri
        JOIN user_books ub ON ri.user_book_id = ub.id
        JOIN books b ON ub.book_id = b.id
        WHERE ub.user_id = :user_id AND ri.status = :status
        ORDER BY ri.end_date DESC, ri.drop_date DESC, ri.start_date DESC, ri.added_to_read_date DESC
        LIMIT :per_page OFFSET :offset
    """)

    books_query = db.session.execute(stmt, {
        'user_id': user_id,
        'status': status,
        'per_page': per_page,
        'offset': offset
    })

    books = [{
        'reading_instance_id': row.reading_instance_id,
        'user_book_id': row.user_book_id,
        'title': row.title,
        'author': row.author,
        'cover_image_path': row.cover_image_path,
        'status': row.status,
        'format': row.format,
        'start_date': parse_date(row.start_date),
        'end_date': parse_date(row.end_date),
        'drop_date': parse_date(row.drop_date),
        'added_to_read_date': parse_date(row.added_to_read_date)
    } for row in books_query]

    total_books = db.session.execute(text("""
        SELECT COUNT(*) FROM read_instances ri
        JOIN user_books ub ON ub.id = ri.user_book_id
        WHERE ub.user_id = :user_id AND ri.status = :status
    """), {'user_id': user_id, 'status': status}).scalar()

    return render_template('see_more.html', status=status, books=books, total_books=total_books, page=page, per_page=per_page)

@app.route('/api/books/<status>', methods=['GET'])
def get_books(status):
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    stmt = ("""
        SELECT b.id, b.title, b.author, b.cover_image_path, ri.status, ri.format,
            ri.start_date, ri.end_date, ri.drop_date, ri.added_to_read_date
        FROM books b
        JOIN user_books ub ON b.id = ub.book_id
        JOIN read_instances ri ON ub.id = ri.user_book_id
        WHERE ub.user_id = :user_id AND ri.status = :status
        LIMIT :limit OFFSET :offset
    """)
    offset = (page - 1) * per_page

    result = db.session.execute(stmt, {
        'user_id': user_id,  
        'status': status, 
        'limit': per_page, 
        'offset': offset
    }).fetchall()

    books = [{
        'id': row.id, 
        'title': row.title, 
        'author': row.author, 
        'cover_image_path': row.cover_image_path, 
        'status': row.status, 
        'format': row.format, 
        'start_date': row.start_date, 
        'end_date': row.end_date, 
        'drop_date': row.drop_date, 
        'added_to_read_date': row.added_to_read_date
    } for row in result]

    total_books = db.session.execute(text("""
            SELECT COUNT(*) FROM read_instances ri
            JOIN user_books ub ON ub.id = ri.user_book_id
            WHERE ub.user_id = :user_id AND ri.status = :status
    """), {'user_id': user_id, 'status': status}).scalar()

    response = {
        'success': True,
        'books': books,
        'total_books': total_books,
        'page': page,
        'per_page': per_page
    }
    return jsonify(response)

@app.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'user' not in session or 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        format = request.form.get('format')
        status = request.form.get('status')
        cover_image = request.files.get('cover_image')

        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        drop_date = request.form.get('drop_date')
        added_to_read_date = request.form.get('added_to_read_date')

        upload_folder = os.path.join(current_app.root_path, 'static', 'cover_images')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        cover_image_path = None
        if cover_image:
            cover_image_path = f'cover_images/{cover_image.filename}'
            cover_image.save(os.path.join(current_app.root_path, 'static', cover_image_path))

        user_id = session.get('user_id')

        try: 
            db.session.begin()
            existing_book = Book.query.filter_by(title=title, author=author).first()

            if existing_book:
                flash('This book already exists in the catalog.')
            
                existing_user_book = UserBook.query.filter_by(user_id=user_id, book_id=existing_book.id).first()
                if existing_user_book:
                    flash('You already have this book in your library so a new Read Instance was created for the re-read.')
                    add_read_instance(existing_user_book.id, status, format, start_date, end_date, drop_date, added_to_read_date)
                else:
                    user_book = UserBook(user_id=user_id, book_id=existing_book.id)
                    db.session.add(user_book)
                    db.session.commit()

                    add_read_instance(user_book.id, status, format, start_date, end_date, drop_date, added_to_read_date)

                    flash('You have added this book to your library.')

                return redirect(url_for('add_book'))
        
            new_book = Book(title=title, author=author, uploaded_by=user_id)
            if cover_image_path:
                new_book.cover_image_path = cover_image_path
            db.session.add(new_book)
            db.session.flush()

            user_book = UserBook(user_id=user_id, book_id=new_book.id)
            db.session.add(user_book)
            db.session.commit()

            add_read_instance(user_book.id, status, format, start_date, end_date, drop_date, added_to_read_date)

            flash('Book added successfully to the database and your library!')

        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}")
            return redirect(url_for('add_book'))
        finally:
            db.session.close()

        return redirect(url_for('add_book'))
    
    return render_template('add_book.html')

def add_read_instance(user_book_id, status, format, start_date=None, end_date=None, drop_date=None, added_to_read_date=None):
    try:
        read_instance = ReadInstance(user_book_id=user_book_id, status=status, format=format,)
        if status == 'in progress':
            if start_date:
                read_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                read_instance.start_date = db.func.current_date()
        elif status == 'to read':
            if added_to_read_date:
                read_instance.added_to_read_date = datetime.strptime(added_to_read_date, "%Y-%m-%d")
            else:
                read_instance.added_to_read_date = db.func.current_date()
        elif status == 'completed':
            if start_date:
                read_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                read_instance.start_date = db.func.current_date()
            if end_date:
                read_instance.end_date = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                read_instance.end_date = db.func.current_date()
        elif status == 'dropped':
            if start_date:
                read_instance.start_date = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                read_instance.start_date = db.func.current_date()
            if drop_date:
                read_instance.drop_date = datetime.strptime(drop_date, "%Y-%m-%d")
            else:
                read_instance.drop_date = db.func.current_date()

        db.session.add(read_instance)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise

@app.route('/statistics', methods=['GET','POST'])
def statistics():
    # get distinct years
    years = db.session.query(
        db.extract('year', func.coalesce(
            ReadInstance.start_date,
            ReadInstance.end_date,
            ReadInstance.drop_date,
            ReadInstance.added_to_read_date
        )).label('year')
    ).distinct().order_by(db.desc('year')).all()

    months = [
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December")
    ]

    completed_books = 0
    avg_time_to_finish = 0
    to_read_books = 0
    dropped_books = 0
    selected_year = None
    selected_month = None

    if request.method == 'POST':
        selected_year = request.form.get('year')
        selected_month = request.form.get('month')

        # get stats for selected year and month
        if selected_year and selected_month:
            # number of completed books
            completed_books = db.session.query(ReadInstance).filter(
                db.extract('year', ReadInstance.end_date) == selected_year,
                db.extract('month', ReadInstance.end_date) == selected_month,
                ReadInstance.status == 'completed'
            ).count()

            # average time to finish a book (time betwen start_date and end_date)
            avg_time_to_finish = db.session.query(func.avg(
                        func.julianday(ReadInstance.end_date) - func.julianday(ReadInstance.start_date)
                    )).filter(
                        db.extract('year', ReadInstance.end_date) == selected_year,
                        db.extract('month', ReadInstance.end_date) == selected_month,
                        ReadInstance.status == 'completed',
                        ReadInstance.start_date.isnot(None),
                        ReadInstance.end_date.isnot(None)
                    ).scalar()
            
            # number of books added to "to read" status
            to_read_books = db.session.query(ReadInstance).filter(
                db.extract('year', ReadInstance.added_to_read_date) == selected_year,
                db.extract('month', ReadInstance.added_to_read_date) == selected_month,
                ReadInstance.status == 'to read'
            ).count()

            # number of books dropped that month
            dropped_books = db.session.query(ReadInstance).filter(
                db.extract('year', ReadInstance.drop_date) == selected_year,
                db.extract('month', ReadInstance.drop_date) == selected_month,
                ReadInstance.status == 'dropped'
            ).count()

            # Format to 2 decimal points
        if avg_time_to_finish is not None:
            avg_time_to_finish = round(avg_time_to_finish, 2)
    return render_template('statistics.html',
                           years=years,
                           months=months,
                           selected_year=selected_year,
                           selected_month = selected_month,
                           completed_books=completed_books,
                           avg_time_to_finish=avg_time_to_finish,
                           to_read_books=to_read_books,
                           dropped_books=dropped_books)

    

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)