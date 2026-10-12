# Employee Attendance & Analytics API

## How to run

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables (or place in a .env file)
export MONGO_URI="mongodb://localhost:27017"
export MONGO_DB="attendance_db"

# 3. (Optional) seed the sample data
python sample_seed.py

# 4. Start the server
uvicorn app.main:app --port 8000
```

`GET http://localhost:8000/health` returns `{"status": "ok"}` when MongoDB is reachable.

Interactive API docs are available at `http://localhost:8000/docs`.

## What is implemented

All endpoints defined in `openapi.yaml`:

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | 503 when MongoDB is unavailable |
| POST | `/employees` | Race-safe via unique index |
| GET | `/employees` | Paginated, sorted by `emp_code` |
| POST | `/attendance/punch-in` | R1 (overnight), R2 (late minutes), race-safe |
| POST | `/attendance/punch-out` | R3–R5, race-safe via `find_one_and_update` |
| GET | `/attendance` | DB-level sort/skip/limit, index-backed |
| PATCH | `/attendance/{emp_code}/{date}` | Recomputes derived fields, appends history, optimistic concurrency lock |
| GET | `/analytics/employees/{emp_code}/monthly` | Aggregation pipeline |
| GET | `/analytics/departments/summary` | Cross-collection pipeline; zero-log employees counted |
| GET | `/analytics/leaderboard/late` | `$rank` window function; ties handled correctly |
| GET | `/analytics/departments/{department}/trend` | `$densify` gap-filling; 7-day moving average |
| GET | `/admin/explain/{endpoint}` | `executionStats` explain; all plans use IXSCAN |

## Notes

- All indexes are created at startup idempotently — no manual steps required.
- `MONGO_URI` and `MONGO_DB` are read from environment variables; the `.env` file is a convenience fallback.
- Timestamps in the API are always epoch **milliseconds**. Values outside `[100_000_000_000, 4_102_444_800_000]` are rejected with 422.
- The `$densify` stage requires MongoDB 5.1+; Atlas free tier (M0) supports it on MongoDB 6.0+.
