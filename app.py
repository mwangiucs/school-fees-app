import os
from flask import Flask, render_template, request, redirect, flash, send_file
import sqlite3
import pandas as pd

app = Flask(__name__)
app.secret_key = 'supersecret'

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
    def to_float(val):
        try:
            return float(val)
        except:
            return 0.0

    if request.method == 'POST':
        data = (
            request.form['student_id'],
            request.form['name'],
            request.form['reg_date'],
            request.form['completion_date'],
            request.form['column1'],
            to_float(request.form['balance_bf']),
            to_float(request.form['total_balance']),
            to_float(request.form['amount_paid']),
            to_float(request.form['balance'])
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

@app.route('/import', methods=['GET', 'POST'])
def import_excel():
    if request.method == 'POST':
        file = request.files['excel_file']
        if file:
            try:
                df = pd.read_excel(file)
                records = df.values.tolist()
                with sqlite3.connect("database.db") as conn:
                    conn.executemany("""
                        INSERT INTO students (
                            student_id, name, reg_date, completion_date, column1,
                            balance_bf, total_balance, amount_paid, balance
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, records)
                flash("Data imported successfully!", "success")
            except Exception as e:
                flash(f"Error importing data: {str(e)}", "danger")
        return redirect('/students')
    return render_template('import.html')

@app.route('/export')
def export_excel():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT * FROM students", conn)
    file_path = "students_export.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))

