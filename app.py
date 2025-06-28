import os
import uuid
import psycopg2
import pandas as pd
from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, send_file

app = Flask(__name__)
app.secret_key = 'supersecret'

# PostgreSQL connection for Railway (replace with os.environ.get in production)
DATABASE_URL = "postgresql://postgres:francisN1!982@db.feznbkitostzcrecuvqb.supabase.co:5432/postgres?sslmode=require"


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
    receipt_no = None

    conn = get_connection()
    cur = conn.cursor()

    # Generate next receipt number
    cur.execute("SELECT receipt_no FROM receipts ORDER BY id DESC LIMIT 1")
    last = cur.fetchone()
    if last:
        try:
            receipt_no = str(int(last[0]) + 1)
        except:
            receipt_no = str(int('17255') + 1)
    else:
        receipt_no = "17255"

    if request.method == 'POST':
        student_id = request.form['student_id']
        amount_paid = float(request.form['amount_paid'])
        received_by = request.form['received_by']

        cur.execute("SELECT * FROM students WHERE student_id=%s", (student_id,))
        student = cur.fetchone()

        if student:
            old_balance = student[9]
            new_balance = old_balance - amount_paid
            date = datetime.now().strftime("%Y-%m-%d")

            cur.execute("""
                INSERT INTO receipts (
                    date, receipt_no, student_id, name,
                    old_balance, amount_paid, new_balance, received_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (date, receipt_no, student_id, student[2],
                  old_balance, amount_paid, new_balance, received_by))

            cur.execute("UPDATE students SET balance=%s WHERE student_id=%s", (new_balance, student_id))
            conn.commit()
            conn.close()
            flash(f"✅ Payment recorded. Receipt: {receipt_no}", "success")
            return redirect('/receipts')
        else:
            flash("❌ Student ID not found.", "danger")

    conn.close()
    return render_template('make_payment.html', student=student, receipt_no=receipt_no)

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

@app.route('/make-deposit', methods=['GET', 'POST'])
def make_deposit():
    conn = get_connection()
    cur = conn.cursor()

    # Get all un-deposited receipts
    cur.execute("SELECT * FROM receipts WHERE deposited = 0 ORDER BY id ASC")
    receipts = cur.fetchall()

    if not receipts:
        flash("No un-deposited receipts available.", "warning")
        return redirect('/deposit-dashboard')

    total_amount = sum(r[6] for r in receipts)  # amount_paid is at index 6
    receipt_start = receipts[0][2]  # receipt_no
    receipt_end = receipts[-1][2]   # receipt_no
    balance_after = total_amount + (cur.execute("SELECT SUM(amount) FROM deposits").fetchone()[0] or 0)

    if request.method == 'POST':
        deposit_id = "DEP-" + str(uuid.uuid4())[:8]
        date = datetime.now().strftime("%Y-%m-%d")

        cur.execute("""
            INSERT INTO deposits (deposit_id, date, receipt_start, receipt_end, amount, balance_after)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (deposit_id, date, receipt_start, receipt_end, total_amount, balance_after))

        # Mark all these receipts as deposited
        cur.execute("UPDATE receipts SET deposited = 1 WHERE deposited = 0")

        conn.commit()
        conn.close()
        flash(f"✅ Deposit {deposit_id} recorded successfully!", "success")
        return redirect('/deposit-dashboard')

    conn.close()
    return render_template(
        'make_deposit.html',
        total_amount=total_amount,
        receipt_start=receipt_start,
        receipt_end=receipt_end,
        balance_after=balance_after
    )


@app.route('/deposit-dashboard')
def deposit_dashboard():
    conn = get_connection()
    cur = conn.cursor()

    # Total from all receipts
    cur.execute("SELECT SUM(amount_paid) FROM receipts")
    total_collected = cur.fetchone()[0] or 0

    # Total amount already deposited
    cur.execute("SELECT SUM(amount) FROM deposits")
    total_deposited = cur.fetchone()[0] or 0

    # Balance still available to deposit
    to_deposit = total_collected - total_deposited

    # Get deposit history
    cur.execute("SELECT * FROM deposits ORDER BY id DESC")
    deposits = cur.fetchall()

    conn.close()
    return render_template(
        "deposit_dashboard.html",
        total_collected=total_collected,
        total_deposited=total_deposited,
        to_deposit=to_deposit,
        deposits=deposits
    )

@app.route('/edit-receipt/<int:id>', methods=['GET', 'POST'])
def edit_receipt(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM receipts WHERE id=%s", (id,))
    receipt = cur.fetchone()

    if receipt[9] == 1:
        flash("❌ Cannot edit a deposited receipt.", "danger")
        return redirect('/receipts')

    if request.method == 'POST':
        amount_paid = float(request.form['amount_paid'])
        new_balance = float(request.form['new_balance'])

        cur.execute("""
            UPDATE receipts SET amount_paid=%s, new_balance=%s WHERE id=%s
        """, (amount_paid, new_balance, id))
        conn.commit()
        flash("✅ Receipt updated.", "success")
        return redirect('/receipts')

    return render_template('edit_receipt.html', receipt=receipt)
@app.route('/delete-receipt/<int:id>')
def delete_receipt(id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT deposited FROM receipts WHERE id=%s", (id,))
    result = cur.fetchone()
    if result and result[0] == 1:
        flash("❌ Cannot delete a deposited receipt.", "danger")
    else:
        cur.execute("DELETE FROM receipts WHERE id=%s", (id,))
        conn.commit()
        flash("🗑️ Receipt deleted.", "success")

    return redirect('/receipts')
    
@app.route('/api/student/<student_id>')
def get_student_by_id(student_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_id, name, balance FROM students WHERE student_id = %s", (student_id,))
    student = cur.fetchone()
    conn.close()

    if student:
        return {
            "student_id": student[0],
            "name": student[1],
            "balance": float(student[2])
        }
    return {}


@app.route('/init-db')
def init_db():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id SERIAL PRIMARY KEY,
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

        cur.execute("""
            CREATE TABLE IF NOT EXISTS receipts (
                id SERIAL PRIMARY KEY,
                date TEXT,
                receipt_no TEXT,
                student_id TEXT,
                name TEXT,
                old_balance REAL,
                amount_paid REAL,
                new_balance REAL,
                received_by TEXT,
                deposited INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id SERIAL PRIMARY KEY,
                deposit_id TEXT,
                date TEXT,
                receipt_start TEXT,
                receipt_end TEXT,
                amount REAL,
                balance_after REAL
            )
        """)

        conn.commit()
        conn.close()
        return "✅ Tables created successfully!"

    except Exception as e:
        return f"❌ Error: {e}"



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
