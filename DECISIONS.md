# DECISIONS.md

1. **Indexes.**  
   I created six indexes at startup. On `employees`: `emp_code` (unique) to enforce identity and make employee lookups O(log n); `joined_on` and the composite `(department, joined_on)` to support the headcount filter in department summary without scanning the whole collection. On `attendance_logs`: the compound unique `(emp_code, date)` to enforce one record per employee-day and make the punch-in race-safe atomically; `(date DESC, emp_code ASC)` to serve the list endpoint's required sort without a sort-in-memory step; and `date ASC` to support analytics pipelines that filter by date range. I considered a `status` index but rejected it: status is low-cardinality (five values), selectivity is poor, and the date index already narrows the scan before status is checked.

2. **Punch-in race.**  
   Two identical punch-in requests arrive simultaneously. Both skip the old `find_one` check (removed) and call `insert_one` with the same `(emp_code, date)`. MongoDB enforces a unique index on that pair. Exactly one insert succeeds (201 returned); the other hits a `DuplicateKeyError`, which the code catches and converts to a 409. No application-level lock, no sleep, no retry — the database does the work atomically.

3. **Ties.**  
   `$setWindowFields` with `$rank` assigns the same rank to employees with equal `total_late_minutes`. The `limit` filter is applied as `{"$match": {"rank": {"$lte": limit}}}` after ranking. If two employees are tied exactly at the cutoff rank (say rank 10 with `limit=10`), both are included in the response even though that means the result has more than `limit` rows. Rows within the same rank are ordered by `emp_code` ascending, as the contract requires.

4. **Headcount.**  
   The department summary pipeline starts from the `employees` collection (not `attendance_logs`), matching employees whose `joined_on` is on or before the last day of the month. A `$lookup` then brings in their logs. Because the pipeline starts from employees, every matched employee contributes 1 to `headcount` in the `$group` stage regardless of whether the lookup returns any logs — an empty `logs` array still increments the counter.

5. **One change for 100× the data.**  
   The department trend endpoint currently resolves per-day headcount in Python by iterating over all department employees for each day. At 100× scale, with large departments and 92-day ranges, that inner loop could be slow. I would move it into MongoDB by pre-computing a lookup that aggregates each employee's `joined_on` against the densified date series, letting the database do the counting with a proper index scan rather than transferring employee documents to the application layer.
