import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'secret_key_for_session'

DATABASE = 'database.db'

# ------------------ DATABASE SETUP ------------------

def init_db():
    if not os.path.exists(DATABASE):
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT,
                    role TEXT
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    teacher TEXT,
                    subject TEXT,
                    attendance_pct INTEGER,
                    quizzes_pct INTEGER,
                    performance_pct INTEGER,
                    exams_pct INTEGER
                )
            ''')
            c.execute('''
                CREATE TABLE IF NOT EXISTS grades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student TEXT,
                    class_id INTEGER,
                    attendance INTEGER,
                    quizzes INTEGER,
                    performance INTEGER,
                    exams INTEGER,
                    final_grade REAL
                )
            ''')

            # Insert sample users only if they don't exist
            c.execute("SELECT * FROM users WHERE username = 'teacher1'")
            if not c.fetchone():
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('teacher1', 'pass', 'teacher'))
            c.execute("SELECT * FROM users WHERE username = 'student1'")
            if not c.fetchone():
                c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('student1', 'pass', 'student'))

            conn.commit()
            print("Database initialized.")

# ------------------ ROUTES ------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['username']
        pw = request.form['password']
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username=? AND password=?", (uname, pw))
            user = c.fetchone()
            if user:
                session['username'] = user[1]
                session['role'] = user[3]
                return redirect(url_for('dashboard'))
            else:
                return "Invalid login!"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'role' not in session:
        return redirect(url_for('login'))
    if session['role'] == 'teacher':
        return redirect(url_for('teacher_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ------------------ TEACHER PANEL ------------------

@app.route('/teacher')
def teacher_dashboard():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    return render_template('teacher_dashboard.html')

@app.route('/create_class', methods=['GET', 'POST'])
def create_class():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    if request.method == 'POST':
        subject = request.form['subject']
        a = int(request.form['a'])
        q = int(request.form['q'])
        p = int(request.form['p'])
        e = int(request.form['e'])
        if a + q + p + e != 100:
            return "Total percentage must be 100%"
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute('''
                INSERT INTO classes (teacher, subject, attendance_pct, quizzes_pct, performance_pct, exams_pct)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (session['username'], subject, a, q, p, e))
            conn.commit()
        return redirect(url_for('teacher_dashboard'))
    return render_template('create_class.html')

@app.route('/input_grades', methods=['GET', 'POST'])
def input_grades():
    if session.get('role') != 'teacher':
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM classes WHERE teacher=?", (session['username'],))
        classes = c.fetchall()
    if request.method == 'POST':
        student = request.form['student']
        class_id = int(request.form['class_id'])
        a = int(request.form['attendance'])
        q = int(request.form['quizzes'])
        p = int(request.form['performance'])
        e = int(request.form['exams'])
        with sqlite3.connect(DATABASE) as conn:
            c = conn.cursor()
            c.execute("SELECT attendance_pct, quizzes_pct, performance_pct, exams_pct FROM classes WHERE id=?", (class_id,))
            weights = c.fetchone()
            final = (a * weights[0] + q * weights[1] + p * weights[2] + e * weights[3]) / 100
            c.execute('''
                INSERT INTO grades (student, class_id, attendance, quizzes, performance, exams, final_grade)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (student, class_id, a, q, p, e, final))
            conn.commit()
        return "Grades submitted successfully."
    return render_template('input_grades.html', classes=classes)

# ------------------ STUDENT PANEL ------------------

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    with sqlite3.connect(DATABASE) as conn:
        c = conn.cursor()
        c.execute('''
            SELECT c.subject, g.attendance, g.quizzes, g.performance, g.exams, g.final_grade
            FROM grades g
            JOIN classes c ON g.class_id = c.id
            WHERE g.student=?
        ''', (session['username'],))
        grades = c.fetchall()
    return render_template('student_dashboard.html', grades=grades)

# ------------------ MAIN ------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
