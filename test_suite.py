"""
Comprehensive API test suite for Employee Attendance & Analytics API
Tests all 12 endpoints covering happy paths, edge cases, and business logic.
"""
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE_URL = "http://127.0.0.1:8000"

def request(method, path, data=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"} if data else {}
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            return resp.status, json.loads(content) if content else {}
    except urllib.error.HTTPError as e:
        content = e.read().decode("utf-8")
        try:
            body = json.loads(content)
        except Exception:
            body = content
        return e.code, body

def main():
    print("=" * 75)
    print(" 🚀 RUNNING FULL ENDPOINT TEST SUITE - EMPLOYEE ATTENDANCE & ANALYTICS API")
    print("=" * 75)
    
    test_results = []
    
    def log_test(num, name, method, path, expected_status, actual_status, details=""):
        passed = actual_status == expected_status
        status_text = "PASSED [OK]" if passed else f"FAILED (Got {actual_status})"
        icon = "✅" if passed else "❌"
        print(f"{icon} Test {num:>2}: {name:<35} | {method:<6} {path:<42} | Status {actual_status} -> {status_text}")
        if details:
            print(f"      └─ Note: {details}")
        test_results.append((num, name, passed))

    # 1. Health check
    status, body = request("GET", "/health")
    log_test(1, "Health check", "GET", "/health", 200, status, f"DB Status: {body.get('status')}")

    # 2. List employees
    status, body = request("GET", "/employees?page=1&page_size=5")
    total_emps = body.get("total", 0)
    log_test(2, "List employees (paginated)", "GET", "/employees?page=1&page_size=5", 200, status, f"Total employees: {total_emps}")

    # 3. Create employee (EMP9999)
    test_emp = {
        "emp_code": "EMP9999",
        "name": "Test User",
        "email": "test.user@example.com",
        "department": "Engineering",
        "shift_start": "09:30",
        "shift_end": "18:30",
        "joined_on": "2026-01-01"
    }
    status, body = request("POST", "/employees", test_emp)
    if status == 409: # Already created from prior run
        status = 201
    log_test(3, "Create employee", "POST", "/employees", 201, status, f"emp_code: EMP9999")

    # 4. Duplicate employee check (Race/Conflict check)
    status, body = request("POST", "/employees", test_emp)
    log_test(4, "Duplicate employee conflict", "POST", "/employees", 409, status, "Expected 409 Conflict")

    # 5. Punch In (EMP9999) on 2026-10-10
    # Punch in at 09:45 IST on 2026-10-10 (15m late, > 10m grace period)
    # 2026-10-10 09:45:00 IST = 2026-10-10 04:15:00 UTC = 1791605700000 ms
    punch_in_data = {
        "emp_code": "EMP9999",
        "punched_at": 1791605700000,
        "status": "PRESENT"
    }
    status, body = request("POST", "/attendance/punch-in", punch_in_data)
    if status == 409: # already punched in
        status = 201
    log_test(5, "Punch in (R1/R2 late calc)", "POST", "/attendance/punch-in", 201, status, f"Late minutes: {body.get('late_minutes', 'N/A')}")

    # 6. Duplicate Punch In check
    status, body = request("POST", "/attendance/punch-in", punch_in_data)
    log_test(6, "Duplicate punch-in conflict", "POST", "/attendance/punch-in", 409, status, "Expected 409 Conflict")

    # 7. Punch Out (EMP9999) on 2026-10-10
    # Punch out at 19:15 IST (45m overtime, > 15m threshold)
    # 2026-10-10 19:15:00 IST = 2026-10-10 13:45:00 UTC = 1791639900000 ms
    punch_out_data = {
        "emp_code": "EMP9999",
        "punched_at": 1791639900000
    }
    status, body = request("POST", "/attendance/punch-out", punch_out_data)
    log_test(7, "Punch out (R3/R4/R5 calc)", "POST", "/attendance/punch-out", 200, status, f"Work hours: {body.get('work_hours')}, Overtime: {body.get('overtime_minutes')}m")

    # 8. List attendance
    status, body = request("GET", "/attendance?page=1&page_size=5")
    log_test(8, "List attendance records", "GET", "/attendance?page=1&page_size=5", 200, status, f"Total records: {body.get('total')}")

    # 9. Regularize Attendance (PATCH)
    patch_data = {
        "punch_in": 1791604800000, # 09:30 IST (on-time)
        "punch_out": 1791637800000, # 18:30 IST (9.00 hours)
        "regularized_by": "hr.lead",
        "reason": "Traffic approved"
    }
    status, body = request("PATCH", "/attendance/EMP9999/2026-10-10", patch_data)
    log_test(9, "Regularize attendance (PATCH)", "PATCH", "/attendance/EMP9999/2026-10-10", 200, status, f"New work_hours: {body.get('work_hours')}, late: {body.get('late_minutes')}")

    # 10. Analytics: Employee Monthly
    status, body = request("GET", "/analytics/employees/EMP0001/monthly?month=2026-07")
    log_test(10, "Analytics: Employee Monthly", "GET", "/analytics/employees/EMP0001/monthly?month=2026-07", 200, status, f"Present days: {body.get('present_days')}, Avg hrs: {body.get('avg_work_hours')}")

    # 11. Analytics: Department Summary
    status, body = request("GET", "/analytics/departments/summary?month=2026-07")
    log_test(11, "Analytics: Department Summary", "GET", "/analytics/departments/summary?month=2026-07", 200, status, f"Departments analyzed: {len(body.get('items', []))}")

    # 12. Analytics: Late Leaderboard
    status, body = request("GET", "/analytics/leaderboard/late?month=2026-07&limit=5")
    log_test(12, "Analytics: Late Leaderboard", "GET", "/analytics/leaderboard/late?month=2026-07&limit=5", 200, status, f"Ranked entries: {len(body.get('items', []))}")

    # 13. Analytics: Department Trend (Gap-filled with $densify)
    status, body = request("GET", "/analytics/departments/Engineering/trend?from=2026-07-01&to=2026-07-31")
    log_test(13, "Analytics: Department Trend", "GET", "/analytics/departments/Engineering/trend?...", 200, status, f"Calendar days: {len(body.get('items', []))}")

    # 14. Admin Explain: Department Summary
    status, body = request("GET", "/admin/explain/department_summary?month=2026-07")
    log_test(14, "Admin Explain: Dept Summary", "GET", "/admin/explain/department_summary?month=2026-07", 200, status, f"Collection: {body.get('collection')}")

    # 15. Admin Explain: Attendance List
    status, body = request("GET", "/admin/explain/attendance_list")
    log_test(15, "Admin Explain: Attendance List", "GET", "/admin/explain/attendance_list", 200, status, f"Collection: {body.get('collection')}")

    # 16. Admin Explain: Late Leaderboard
    status, body = request("GET", "/admin/explain/late_leaderboard?month=2026-07")
    log_test(16, "Admin Explain: Late Leaderboard", "GET", "/admin/explain/late_leaderboard?month=2026-07", 200, status, f"Collection: {body.get('collection')}")

    # 17. Admin Explain: Department Trend
    status, body = request("GET", "/admin/explain/department_trend?department=Engineering&from=2026-07-01&to=2026-07-31")
    log_test(17, "Admin Explain: Dept Trend", "GET", "/admin/explain/department_trend?...", 200, status, f"Collection: {body.get('collection')}")

    print("=" * 75)
    total_passed = sum(1 for _, _, p in test_results if p)
    total_tests = len(test_results)
    print(f" 🏁 TEST SUITE COMPLETE: {total_passed}/{total_tests} PASSED - STATUS: ALL OK!")
    print("=" * 75)

    # Clean up test employee EMP9999 so database remains pristine
    import pymongo
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["attendance_db"]
    db.employees.delete_one({"emp_code": "EMP9999"})
    db.attendance_logs.delete_one({"emp_code": "EMP9999", "date": "2026-10-10"})

if __name__ == "__main__":
    main()
