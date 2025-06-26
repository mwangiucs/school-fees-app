import os
import uuid
import psycopg2
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, send_file

app = Flask(__name__)
app.secret_key = 'supersecret'

# PostgreSQL connection for Railway (replace with os.environ.get in production)
DATABASE_URL = "postgresql://postgres:IxwqtVNsgNdaDKVkhiSRKSmgCdgOtqcK@shortline.proxy.rlwy.net:35709/railway"


def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/students')
def students():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM students")
    students = cur.fetchall()
    conn.close()
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
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO students (
                student_id, name, reg_date, completion_date, column1,
                balance_bf, total_balance, amount_paid, balance
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, data)
        conn.commit()
        conn.close()
        return redirect('/students')
    return render_template('add_student.html')

@app.route('/edit-student/<int:id>', methods=['GET', 'POST'])
def edit_student(id):
    conn = get_connection()
    cur = conn.cursor()
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
        cur.execute("""
            UPDATE students SET
            student_id=%s, name=%s, reg_date=%s, completion_date=%s, column1=%s,
            balance_bf=%s, total_balance=%s, amount_paid=%s, balance=%s
            WHERE id=%s
        """, data)
        conn.commit()
        conn.close()
        return redirect('/students')
    cur.execute("SELECT * FROM students WHERE id=%s", (id,))
    student = cur.fetchone()
    conn.close()
    return render_template('edit_student.html', student=student)

@app.route('/delete-student/<int:id>')
def delete_student(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s", (id,))
    conn.commit()
    conn.close()
    return redirect('/students')

@app.route('/import', methods=['GET', 'POST'])
def import_excel():
    if request.method == 'POST':
        file = request.files['excel_file']
        if file:
            try:
                df = pd.read_excel(file)
                records = df.values.tolist()
                conn = get_connection()
                cur = conn.cursor()
                cur.executemany("""
                    INSERT INTO students (
                        student_id, name, reg_date, completion_date, column1,
                        balance_bf, total_balance, amount_paid, balance
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, records)
                conn.commit()
                conn.close()
                flash("Data imported successfully!", "success")
            except Exception as e:
                flash(f"Error importing data: {str(e)}", "danger")
        return redirect('/students')
    return render_template('import.html')

@app.route('/export')
def export_excel():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM students", conn)
    file_path = "students_export.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/make-payment', methods=['GET', 'POST'])
def make_payment():
    student = None
    if request.method == 'POST':
        student_id = request.form['student_id']
        amount_paid = float(request.form['amount_paid'])
        received_by = request.form['received_by']

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
        student = cur.fetchone()

        if student:
            old_balance = student[9]
            new_balance = old_balance - amount_paid
            receipt_no = "RCPT-" + str(uuid.uuid4())[:8]
            date = datetime.now().strftime("%Y-%m-%d")

            cur.execute("""
                INSERT INTO receipts (date, receipt_no, student_id, name, old_balance, amount_paid, new_balance, received_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (date, receipt_no, student_id, student[2], old_balance, amount_paid, new_balance, received_by))

            cur.execute("UPDATE students SET balance=%s WHERE student_id=%s", (new_balance, student_id))
            conn.commit()
            conn.close()
            return redirect('/receipts')
        else:
            flash("Student ID not found.", "danger")

    return render_template('make_payment.html', student=student)

@app.route('/receipts')
def receipts():
    query = request.args.get('query', '').strip()
    conn = get_connection()
    cur = conn.cursor()
    if query:
        cur.execute("""
            SELECT * FROM receipts
            WHERE student_id ILIKE %s OR name ILIKE %s OR receipt_no ILIKE %s
            ORDER BY id DESC
        """, (f'%{query}%', f'%{query}%', f'%{query}%'))
    else:
        cur.execute("SELECT * FROM receipts ORDER BY id DESC")
    receipts = cur.fetchall()
    conn.close()
    return render_template("receipts.html", receipts=receipts, query=query)

@app.route('/print-receipt/<int:id>')
def print_receipt(id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM receipts WHERE id=%s", (id,))
    receipt = cur.fetchone()
    conn.close()
    return render_template("print_receipt.html", receipt=receipt)



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
