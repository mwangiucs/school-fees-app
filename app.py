import os
from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)
...
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))


def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT,
                name TEXT,
                reg_date TEXT,
                completion_date TEXT,
                column1 TEXT,
                balance_bf REAL,
                total_balance REAL,
                amount_paid REAL,
                balance REAL
            )
        """)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/students')
def students():
    conn = sqlite3.connect("database.db")
    students = conn.execute("SELECT * FROM students").fetchall()
    return render_template("students.html", students=students)

@app.route('/add-student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        data = (
            request.form['student_id'],
            request.form['name'],
            request.form['reg_date'],
            request.form['completion_date'],
            request.form['column1'],
            float(request.form['balance_bf']),
            float(request.form['total_balance']),
            float(request.form['amount_paid']),
            float(request.form['balance'])
        )
        with sqlite3.connect("database.db") as conn:
            conn.execute("""INSERT INTO students (
                student_id, name, reg_date, completion_date, column1,
                balance_bf, total_balance, amount_paid, balance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", data)
        return redirect('/students')
    return render_template('add_student.html')

@app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = sqlite3.connect("database.db")
    if request.method == 'POST':
        data = (
            request.form['student_id'],
            request.form['name'],
            request.form['reg_date'],
            request.form['completion_date'],
            request.form['column1'],
            float(request.form['balance_bf']),
            float(request.form['total_balance']),
            float(request.form['amount_paid']),
            float(request.form['balance']),
            id
        )
        conn.execute("""UPDATE students SET
            student_id=?, name=?, reg_date=?, completion_date=?, column1=?,
            balance_bf=?, total_balance=?, amount_paid=?, balance=?
            WHERE id=?""", data)
        conn.commit()
        return redirect('/students')

    student = conn.execute("SELECT * FROM students WHERE id=?", (id,)).fetchone()
    return render_template('edit_student.html', student=student)

@app.route('/delete-student/<int:id>')
def delete_student(id):
    with sqlite3.connect("database.db") as conn:
        conn.execute("DELETE FROM students WHERE id=?", (id,))
    return redirect('/students')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
