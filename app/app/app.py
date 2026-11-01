import os
import time
import pymysql
from flask import Flask, request, redirect, render_template_string, flash
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "placement-secret")
metrics = PrometheusMetrics(app)

STATUSES = ["Applied", "Shortlisted", "Interview Scheduled", "Selected", "Rejected"]
BRANCHES = ["All", "CSE", "IT", "ECE", "EEE", "MECH", "CIVIL"]


def db_config(with_db=True):
    cfg = dict(
        host=os.getenv("DB_HOST", "localhost"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "password"),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )
    if with_db:
        cfg["database"] = os.getenv("DB_NAME", "placement")
    return cfg


def get_db():
    return pymysql.connect(**db_config())


def init_db():
    for _ in range(30):
        try:
            conn = pymysql.connect(**db_config(with_db=False))
            with conn.cursor() as c:
                c.execute("CREATE DATABASE IF NOT EXISTS " + os.getenv("DB_NAME", "placement"))
            conn.close()
            conn = get_db()
            with conn.cursor() as c:
                c.execute("""CREATE TABLE IF NOT EXISTS jobs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    company VARCHAR(100), role VARCHAR(100),
                    package VARCHAR(50), min_cgpa FLOAT, branch VARCHAR(20))""")
                c.execute("""CREATE TABLE IF NOT EXISTS students (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100), email VARCHAR(100),
                    branch VARCHAR(20), cgpa FLOAT)""")
                c.execute("""CREATE TABLE IF NOT EXISTS applications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    student_id INT, job_id INT,
                    status VARCHAR(30) DEFAULT 'Applied',
                    interview_date VARCHAR(50) DEFAULT '')""")
            conn.close()
            print("Database ready")
            return
        except Exception as e:
            print("Waiting for database...", e)
            time.sleep(5)


def query(sql, args=(), fetch=True):
    conn = get_db()
    try:
        with conn.cursor() as c:
            c.execute(sql, args)
            return c.fetchall() if fetch else None
    finally:
        conn.close()


BASE = """
<!doctype html>
<html><head><meta charset="utf-8"><title>Placement Tracker</title>
<style>
body{font-family:Arial,sans-serif;margin:0;background:#f4f6f9}
nav{background:#1f3a5f;padding:14px 30px}
nav a{color:#fff;margin-right:22px;text-decoration:none;font-weight:bold}
.box{max-width:1000px;margin:25px auto;background:#fff;padding:25px;border-radius:8px}
table{width:100%;border-collapse:collapse;margin-top:15px}
th,td{border:1px solid #ddd;padding:9px;text-align:left}
th{background:#e8eef6}
input,select{padding:8px;margin:4px 6px 4px 0}
button{padding:8px 16px;background:#1f3a5f;color:#fff;border:0;border-radius:4px;cursor:pointer}
.msg{padding:10px;background:#fff3cd;margin-bottom:10px;border-radius:4px}
</style></head><body>
<nav><a href="/">Jobs</a><a href="/students">Students</a>
<a href="/apply">Apply</a><a href="/applications">Interview Status</a></nav>
<div class="box">
{% with messages = get_flashed_messages() %}
{% for m in messages %}<div class="msg">{{ m }}</div>{% endfor %}
{% endwith %}
CONTENT
</div></body></html>
"""


def page(content, **ctx):
    return render_template_string(BASE.replace("CONTENT", content), **ctx)


@app.route("/health")
def health():
    return "ok"


@app.route("/", methods=["GET", "POST"])
def jobs():
    if request.method == "POST":
        f = request.form
        query("INSERT INTO jobs (company, role, package, min_cgpa, branch) VALUES (%s,%s,%s,%s,%s)",
              (f["company"], f["role"], f["package"], f["min_cgpa"], f["branch"]), fetch=False)
        flash("Job added")
        return redirect("/")
    rows = query("SELECT * FROM jobs ORDER BY id DESC")
    return page("""
    <h2>Job Listings</h2>
    <form method="post">
      <input name="company" placeholder="Company" required>
      <input name="role" placeholder="Role" required>
      <input name="package" placeholder="Package (e.g. 6 LPA)" required>
      <input name="min_cgpa" type="number" step="0.1" placeholder="Min CGPA" required>
      <select name="branch">{% for b in branches %}<option>{{ b }}</option>{% endfor %}</select>
      <button>Add Job</button>
    </form>
    <table><tr><th>ID</th><th>Company</th><th>Role</th><th>Package</th><th>Min CGPA</th><th>Branch</th></tr>
    {% for r in rows %}<tr><td>{{ r.id }}</td><td>{{ r.company }}</td><td>{{ r.role }}</td>
    <td>{{ r.package }}</td><td>{{ r.min_cgpa }}</td><td>{{ r.branch }}</td></tr>{% endfor %}
    </table>""", rows=rows, branches=BRANCHES)


@app.route("/students", methods=["GET", "POST"])
def students():
    if request.method == "POST":
        f = request.form
        query("INSERT INTO students (name, email, branch, cgpa) VALUES (%s,%s,%s,%s)",
              (f["name"], f["email"], f["branch"], f["cgpa"]), fetch=False)
        flash("Student added")
        return redirect("/students")
    rows = query("SELECT * FROM students ORDER BY id DESC")
    return page("""
    <h2>Students</h2>
    <form method="post">
      <input name="name" placeholder="Name" required>
      <input name="email" placeholder="Email" required>
      <select name="branch">{% for b in branches[1:] %}<option>{{ b }}</option>{% endfor %}</select>
      <input name="cgpa" type="number" step="0.1" placeholder="CGPA" required>
      <button>Add Student</button>
    </form>
    <table><tr><th>ID</th><th>Name</th><th>Email</th><th>Branch</th><th>CGPA</th></tr>
    {% for r in rows %}<tr><td>{{ r.id }}</td><td>{{ r.name }}</td><td>{{ r.email }}</td>
    <td>{{ r.branch }}</td><td>{{ r.cgpa }}</td></tr>{% endfor %}
    </table>""", rows=rows, branches=BRANCHES)


@app.route("/apply", methods=["GET", "POST"])
def apply_job():
    if request.method == "POST":
        sid, jid = request.form["student_id"], request.form["job_id"]
        s = query("SELECT * FROM students WHERE id=%s", (sid,))[0]
        j = query("SELECT * FROM jobs WHERE id=%s", (jid,))[0]
        if s["cgpa"] < j["min_cgpa"]:
            flash("Not eligible: CGPA is below the minimum required")
        elif j["branch"] != "All" and j["branch"] != s["branch"]:
            flash("Not eligible: branch does not match")
        elif query("SELECT id FROM applications WHERE student_id=%s AND job_id=%s", (sid, jid)):
            flash("Already applied to this job")
        else:
            query("INSERT INTO applications (student_id, job_id) VALUES (%s,%s)", (sid, jid), fetch=False)
            flash("Application submitted")
        return redirect("/apply")
    studs = query("SELECT * FROM students")
    jobs_ = query("SELECT * FROM jobs")
    return page("""
    <h2>Apply for a Job</h2>
    <form method="post">
      <select name="student_id" required>
        {% for s in studs %}<option value="{{ s.id }}">{{ s.name }} ({{ s.branch }}, {{ s.cgpa }})</option>{% endfor %}
      </select>
      <select name="job_id" required>
        {% for j in jobs_ %}<option value="{{ j.id }}">{{ j.company }} - {{ j.role }}</option>{% endfor %}
      </select>
      <button>Apply</button>
    </form>
    <p>Eligibility (CGPA and branch) is checked automatically.</p>""", studs=studs, jobs_=jobs_)


@app.route("/applications")
def applications():
    rows = query("""SELECT a.id, s.name, j.company, j.role, a.status, a.interview_date
                    FROM applications a JOIN students s ON a.student_id=s.id
                    JOIN jobs j ON a.job_id=j.id ORDER BY a.id DESC""")
    return page("""
    <h2>Interview Status</h2>
    <table><tr><th>Student</th><th>Company</th><th>Role</th><th>Status</th><th>Interview Date</th><th>Update</th></tr>
    {% for r in rows %}<tr><td>{{ r.name }}</td><td>{{ r.company }}</td><td>{{ r.role }}</td>
    <td><b>{{ r.status }}</b></td><td>{{ r.interview_date }}</td>
    <td><form method="post" action="/update/{{ r.id }}">
      <select name="status">{% for s in statuses %}<option {{ 'selected' if s == r.status }}>{{ s }}</option>{% endfor %}</select>
      <input name="interview_date" value="{{ r.interview_date }}" placeholder="Date / time">
      <button>Save</button></form></td></tr>{% endfor %}
    </table>""", rows=rows, statuses=STATUSES)


@app.route("/update/<int:app_id>", methods=["POST"])
def update(app_id):
    query("UPDATE applications SET status=%s, interview_date=%s WHERE id=%s",
          (request.form["status"], request.form["interview_date"], app_id), fetch=False)
    flash("Status updated")
    return redirect("/applications")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
