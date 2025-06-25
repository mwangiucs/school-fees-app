from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def init_db():
    with sqlite3.connect("database.db") as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            class TEXT,
            amount_paid INTEGER,
            balance INTEGER
        )""")

@app.route('/')
def index():
    conn = sqlite3.connect("database.db")
    students = conn.execute("SELECT * FROM students").fetchall()
    return render_template('index.html', students=students)

@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    class_name = request.form['class']
    amount_paid = int(request.form['amount_paid'])
    total_fees = 10000  # Customize this value
    balance = total_fees - amount_paid
    with sqlite3.connect("database.db") as conn:
        conn.execute("INSERT INTO students (name, class, amount_paid, balance) VALUES (?, ?, ?, ?)",
                     (name, class_name, amount_paid, balance))
    return redirect('/')

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=10000)
