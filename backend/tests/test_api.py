"""Run:  python -m unittest discover -s tests -v"""
import unittest
from datetime import date, timedelta

import store
from app import create_app


def day(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        store.seed()
        self.client = create_app().test_client()

    # helpers
    def student(self, **kw):
        data = {"name": "Test Student", "rollNo": "22AD100", "email": "t@college.edu",
                "department": "CSE", "cgpa": 8.0, "backlogs": 0, "year": 4, "skills": "Python", "placed": False}
        data.update(kw)
        return data

    def job(self, **kw):
        data = {"company": "Acme", "role": "Dev", "package": 10, "location": "Chennai", "minCgpa": 7,
                "maxBacklogs": 0, "departments": ["CSE"], "deadline": day(30), "status": "Open"}
        data.update(kw)
        return data


class TestBasics(ApiTestCase):
    def test_health(self):
        r = self.client.get("/api/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})

    def test_unknown_route_returns_json_404(self):
        r = self.client.get("/api/nothing")
        self.assertEqual(r.status_code, 404)
        self.assertIn("error", r.get_json())

    def test_wrong_method_returns_json_405(self):
        r = self.client.delete("/api/students")
        self.assertEqual(r.status_code, 405)
        self.assertIn("error", r.get_json())

    def test_invalid_json_body(self):
        r = self.client.post("/api/students", data="not json", content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_cors_allowed_and_blocked_origin(self):
        ok = self.client.get("/api/health", headers={"Origin": "http://localhost:5500"})
        self.assertEqual(ok.headers.get("Access-Control-Allow-Origin"), "http://localhost:5500")
        bad = self.client.get("/api/health", headers={"Origin": "http://evil.com"})
        self.assertIsNone(bad.headers.get("Access-Control-Allow-Origin"))


class TestStudents(ApiTestCase):
    def test_list_seed_and_filters(self):
        self.assertEqual(len(self.client.get("/api/students").get_json()), 6)
        self.assertEqual(len(self.client.get("/api/students?department=CSE").get_json()), 1)
        self.assertEqual(len(self.client.get("/api/students?q=priya").get_json()), 1)

    def test_create_get_update_delete(self):
        r = self.client.post("/api/students", json=self.student())
        self.assertEqual(r.status_code, 201)
        sid = r.get_json()["id"]
        self.assertEqual(self.client.get(f"/api/students/{sid}").get_json()["rollNo"], "22AD100")
        r = self.client.put(f"/api/students/{sid}", json=self.student(name="Renamed", cgpa=9.1))
        self.assertEqual(r.get_json()["name"], "Renamed")
        self.assertEqual(self.client.delete(f"/api/students/{sid}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/students/{sid}").status_code, 404)

    def test_validation_errors(self):
        r = self.client.post("/api/students", json=self.student(name="A", cgpa=11, email="bad", department="XYZ"))
        self.assertEqual(r.status_code, 422)
        details = r.get_json()["details"]
        for field in ("name", "cgpa", "email", "department"):
            self.assertIn(field, details)

    def test_wrong_types_rejected(self):
        r = self.client.post("/api/students", json=self.student(cgpa="eight", backlogs=True))
        self.assertEqual(r.status_code, 422)
        self.assertIn("cgpa", r.get_json()["details"])
        self.assertIn("backlogs", r.get_json()["details"])

    def test_duplicate_roll_and_email(self):
        r = self.client.post("/api/students", json=self.student(rollNo="21ad001", email="aarav@college.edu"))
        self.assertEqual(r.status_code, 409)
        self.assertIn("rollNo", r.get_json()["details"])
        self.assertIn("email", r.get_json()["details"])

    def test_update_can_keep_own_roll_number(self):
        r = self.client.put("/api/students/1", json=self.student(rollNo="21AD001", email="aarav@college.edu"))
        self.assertEqual(r.status_code, 200)

    def test_not_found(self):
        self.assertEqual(self.client.get("/api/students/999").status_code, 404)
        self.assertEqual(self.client.put("/api/students/999", json=self.student()).status_code, 404)
        self.assertEqual(self.client.delete("/api/students/999").status_code, 404)

    def test_delete_student_cascades(self):
        self.client.delete("/api/students/2")  # Priya has 2 applications + 1 interview
        apps = self.client.get("/api/applications").get_json()
        self.assertFalse(any(a["studentId"] == 2 for a in apps))
        self.assertEqual(len(self.client.get("/api/interviews").get_json()), 1)


class TestJobs(ApiTestCase):
    def test_crud(self):
        r = self.client.post("/api/jobs", json=self.job())
        self.assertEqual(r.status_code, 201)
        jid = r.get_json()["id"]
        r = self.client.put(f"/api/jobs/{jid}", json=self.job(package=12.5, status="Closed"))
        self.assertEqual(r.get_json()["status"], "Closed")
        self.assertEqual(self.client.delete(f"/api/jobs/{jid}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/jobs/{jid}").status_code, 404)

    def test_validation(self):
        r = self.client.post("/api/jobs", json=self.job(company="", package=-5, departments=[], deadline="31-12-2026"))
        self.assertEqual(r.status_code, 422)
        for field in ("company", "package", "departments", "deadline"):
            self.assertIn(field, r.get_json()["details"])

    def test_status_filter(self):
        self.assertEqual(len(self.client.get("/api/jobs?status=Closed").get_json()), 1)
        self.assertEqual(self.client.get("/api/jobs?status=Nope").status_code, 400)

    def test_delete_job_updates_placed(self):
        # Aarav is placed only through TCS (job 1); deleting the job un-places him
        self.client.delete("/api/jobs/1")
        self.assertFalse(self.client.get("/api/students/1").get_json()["placed"])


class TestEligibility(ApiTestCase):
    def check(self, sid, jid):
        return self.client.get(f"/api/eligibility/check?studentId={sid}&jobId={jid}").get_json()

    def test_eligible(self):
        self.assertTrue(self.check(2, 4)["eligible"])  # Priya -> Amazon

    def test_low_cgpa_and_backlogs(self):
        res = self.check(5, 2)  # Karthik -> Zoho
        self.assertFalse(res["eligible"])
        failed = [c["label"] for c in res["checks"] if not c["ok"]]
        self.assertIn("CGPA", failed)
        self.assertIn("Backlogs", failed)

    def test_closed_job(self):
        res = self.check(2, 3)  # Infosys is closed
        self.assertFalse(res["eligible"])
        self.assertFalse([c for c in res["checks"] if c["label"] == "Job open"][0]["ok"])

    def test_wrong_department(self):
        r = self.client.post("/api/jobs", json=self.job(departments=["ECE"]))
        jid = r.get_json()["id"]
        self.assertFalse(self.check(2, jid)["eligible"])

    def test_bad_params(self):
        self.assertEqual(self.client.get("/api/eligibility/check").status_code, 400)
        self.assertEqual(self.client.get("/api/eligibility/check?studentId=1&jobId=999").status_code, 404)

    def test_students_for_job_and_jobs_for_student(self):
        self.assertEqual(len(self.client.get("/api/eligibility/job/1").get_json()), 6)
        self.assertEqual(len(self.client.get("/api/eligibility/student/2").get_json()), 4)


class TestApplications(ApiTestCase):
    def test_apply_success(self):
        r = self.client.post("/api/applications", json={"studentId": 2, "jobId": 1})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.get_json()["status"], "Applied")

    def test_duplicate_blocked(self):
        r = self.client.post("/api/applications", json={"studentId": 2, "jobId": 2})
        self.assertEqual(r.status_code, 409)

    def test_ineligible_blocked(self):
        r = self.client.post("/api/applications", json={"studentId": 5, "jobId": 2})
        self.assertEqual(r.status_code, 422)
        self.assertIn("not eligible", r.get_json()["error"])

    def test_missing_references(self):
        self.assertEqual(self.client.post("/api/applications", json={"studentId": 99, "jobId": 1}).status_code, 404)
        self.assertEqual(self.client.post("/api/applications", json={"studentId": 1}).status_code, 422)

    def test_filters(self):
        self.assertEqual(len(self.client.get("/api/applications?studentId=2").get_json()), 2)
        self.assertEqual(len(self.client.get("/api/applications?status=Selected").get_json()), 2)
        self.assertEqual(self.client.get("/api/applications?studentId=abc").status_code, 400)

    def test_status_flow(self):
        ok = self.client.patch("/api/applications/4/status", json={"status": "Shortlisted"})  # Applied -> Shortlisted
        self.assertEqual(ok.status_code, 200)
        bad = self.client.patch("/api/applications/4/status", json={"status": "Applied"})
        self.assertEqual(bad.status_code, 422)
        same = self.client.patch("/api/applications/4/status", json={"status": "Shortlisted"})
        self.assertEqual(same.status_code, 409)
        junk = self.client.patch("/api/applications/4/status", json={"status": "Hired"})
        self.assertEqual(junk.status_code, 422)

    def test_cannot_jump_to_interview_without_interview(self):
        self.client.patch("/api/applications/4/status", json={"status": "Shortlisted"})
        r = self.client.patch("/api/applications/4/status", json={"status": "Interview Scheduled"})
        self.assertEqual(r.status_code, 409)

    def test_selected_marks_student_placed(self):
        self.client.patch("/api/applications/3/status", json={"status": "Selected"})  # Priya -> Amazon
        self.assertTrue(self.client.get("/api/students/2").get_json()["placed"])
        self.client.patch("/api/applications/3/status", json={"status": "Rejected"})
        self.assertFalse(self.client.get("/api/students/2").get_json()["placed"])

    def test_withdraw_removes_interview(self):
        self.client.delete("/api/applications/2")
        self.assertEqual(len(self.client.get("/api/interviews").get_json()), 1)
        self.assertEqual(self.client.delete("/api/applications/2").status_code, 404)


class TestInterviews(ApiTestCase):
    def iv(self, **kw):
        data = {"applicationId": 3, "date": day(5), "time": "11:00", "mode": "Online", "venue": "Zoom"}
        data.update(kw)
        return data

    def test_schedule_sets_status(self):
        r = self.client.post("/api/interviews", json=self.iv())
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.client.get("/api/applications/3").get_json()["status"], "Interview Scheduled")

    def test_only_shortlisted(self):
        r = self.client.post("/api/interviews", json=self.iv(applicationId=4))  # status Applied
        self.assertEqual(r.status_code, 422)

    def test_duplicate_interview_blocked(self):
        r = self.client.post("/api/interviews", json=self.iv(applicationId=2))  # already has one
        self.assertIn(r.status_code, (409, 422))

    def test_past_date_and_bad_time(self):
        r = self.client.post("/api/interviews", json=self.iv(date=day(-1), time="25:99", mode="Phone", venue=""))
        self.assertEqual(r.status_code, 422)
        for field in ("date", "time", "mode", "venue"):
            self.assertIn(field, r.get_json()["details"])

    def test_clash_blocked(self):
        # Priya (student 2) already interviews at day(4) 10:00 for application 2
        r = self.client.post("/api/interviews", json=self.iv(date=day(4), time="10:00"))
        self.assertEqual(r.status_code, 409)

    def test_reschedule_and_cancel(self):
        r = self.client.put("/api/interviews/1", json={"date": day(9), "time": "09:30", "mode": "Offline", "venue": "Hall B"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["venue"], "Hall B")
        self.client.delete("/api/interviews/1")
        self.assertEqual(self.client.get("/api/applications/2").get_json()["status"], "Shortlisted")
        self.assertEqual(self.client.get("/api/interviews/1").status_code, 404)


class TestDashboard(ApiTestCase):
    def test_summary(self):
        s = self.client.get("/api/dashboard/summary").get_json()
        self.assertEqual(s["totalStudents"], 6)
        self.assertEqual(s["placedStudents"], 2)
        self.assertEqual(s["placementRate"], 33)
        self.assertEqual(s["openJobs"], 3)
        self.assertEqual(s["totalApplications"], 7)
        self.assertEqual(s["upcomingInterviews"], 2)

    def test_analytics(self):
        a = self.client.get("/api/dashboard/analytics").get_json()
        self.assertIn("departmentStats", a)
        self.assertIn("salaryStats", a)
        self.assertIn("statusFunnel", a)
        self.assertGreater(a["salaryStats"]["highest"], 0)


class TestAuth(ApiTestCase):
    def test_student_registration_and_login(self):
        # Register
        data = self.student(rollNo="23CS888", email="newuser@college.edu")
        reg = self.client.post("/api/auth/register", json=data)
        self.assertEqual(reg.status_code, 201)
        self.assertIn("token", reg.get_json())

        # Login with email
        login1 = self.client.post("/api/auth/login", json={"email": "newuser@college.edu"})
        self.assertEqual(login1.status_code, 200)
        self.assertEqual(login1.get_json()["role"], "student")

        # Login with rollNo via /api/students/login
        login2 = self.client.post("/api/students/login", json={"rollNo": "23CS888"})
        self.assertEqual(login2.status_code, 200)

        # Admin login
        admin_login = self.client.post("/api/auth/login", json={"email": "admin@college.edu"})
        self.assertEqual(admin_login.status_code, 200)
        self.assertEqual(admin_login.get_json()["role"], "admin")

        # Invalid credentials
        bad = self.client.post("/api/auth/login", json={"email": "nonexistent@college.edu"})
        self.assertEqual(bad.status_code, 401)


if __name__ == "__main__":
    unittest.main()
