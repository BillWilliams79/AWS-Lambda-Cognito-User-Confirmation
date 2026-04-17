# Lambda-Cognito Test Coverage Map

## Summary

**13 existing tests** cover ~7 of 17 distinct code paths in `lambda_function.py`. The uncovered paths are all "permissive" error handlers (domain/area/task INSERT failures) that log warnings but allow signup to succeed.

## Code Path Inventory (17 paths)

### Entry Point
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 1 | triggerSource != ConfirmSignUp | 44-45 | Return event unchanged | **Yes** (3 tests) |

### Step 1: Extract Cognito Data
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 2 | userName is None | 59-62 | Return error string (blocks signup) | **Yes** |

### Step 2: Create Profile
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 3 | INSERT succeeds | 80-81 | Commit, continue | **Yes** (happy path) |
| 4 | INSERT returns 0 rows | 82-86 | Return error (blocks signup) | No |
| 5 | INSERT raises pymysql.Error | 88-92 | Return error (blocks signup) | **Yes** (duplicate) |

### Step 3a: Create Domain
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 6 | INSERT succeeds | 110-111 | Commit, continue | **Yes** (happy path) |
| 7 | INSERT returns 0 rows | 112-116 | Warning, return event (permissive) | No |
| 8 | INSERT raises pymysql.Error | 118-122 | Warning, return event (permissive) | No |

### Step 3b: Retrieve Domain ID
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 9 | LAST_INSERT_ID succeeds | 132-133 | Fetch domain_fk, continue | **Yes** (happy path) |
| 10 | LAST_INSERT_ID returns 0 rows | 134-137 | Warning, return event (permissive) | No |
| 11 | LAST_INSERT_ID raises error | 139-142 | Warning, return event (permissive) | No |

### Step 4: Create Area
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 12 | INSERT succeeds | 161-162 | Commit, continue | **Yes** (happy path) |
| 13 | INSERT returns 0 rows | 163-167 | Warning, return event (permissive) | No |
| 14 | INSERT raises pymysql.Error | 169-173 | Warning, return event (permissive) | No |

### Step 4b: Retrieve Area ID
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 15 | LAST_INSERT_ID succeeds | 182-183 | Fetch area_fk, continue | **Yes** (happy path) |
| 16 | LAST_INSERT_ID returns 0 rows | 184-187 | Warning, return event (permissive) | No |
| 17 | LAST_INSERT_ID raises error | 189-192 | Warning, return event (permissive) | No |

### Step 5: Create Task + Success
| # | Path | Lines | Behavior | Tested? |
|---|------|-------|----------|---------|
| 18 | INSERT succeeds → return event | 212-228 | Full success | **Yes** (happy path) |
| 19 | INSERT returns 0 rows | 214-218 | Warning, return event (permissive) | No |
| 20 | INSERT raises pymysql.Error | 220-224 | Warning, return event (permissive) | No |

**Note**: Paths 7-8, 10-11, 13-14, 16-17, 19-20 all follow the same pattern: print warning, return event. They allow signup to succeed even when default data creation fails.

## Existing Test Map (13 tests)

### test_01_signup_provisioning.py (5 tests)

| Test | Paths Covered | What It Verifies |
|------|--------------|-----------------|
| test_signup_creates_profile | 3, 6, 9, 12, 15, 18 | Profile record created with correct fields |
| test_signup_creates_domain | (indirect) | "Personal" domain exists, closed=0 |
| test_signup_creates_area | (indirect) | "Home" area exists, closed=0 |
| test_signup_creates_task | (indirect) | Instructional task with priority=1 |
| test_signup_full_hierarchy_linked | (indirect) | FK chain: task → area → domain → profile JOIN |

### test_02_event_types.py (3 tests)

| Test | Paths Covered | What It Verifies |
|------|--------------|-----------------|
| test_forgot_password_is_noop | 1 | ConfirmForgotPassword creates nothing |
| test_unknown_trigger_is_noop | 1 | Unknown trigger creates nothing |
| test_missing_trigger_source_is_noop | 1 | Missing triggerSource creates nothing |

### test_03_edge_cases.py (5 tests)

| Test | Paths Covered | What It Verifies |
|------|--------------|-----------------|
| test_missing_username_returns_error | 2 | Returns error string, no profile |
| test_duplicate_user_returns_error | 5 | Duplicate PK → pymysql.Error caught |
| test_missing_email_still_creates_profile | 3 (variant) | Email=None succeeds |
| test_missing_name_still_creates_profile | 3 (variant) | Name=None succeeds |
| test_empty_request_returns_error | (edge) | Empty request dict handled |

## Coverage Gaps — Prioritized

### Worth Testing (5 new tests proposed)

1. **Connection reconnect** — Verify `get_connection()` reconnects after stale connection. Exercise the ping/reconnect pattern at line 19-33.

2. **Duplicate domain creation** — Call handler twice for same user. Second call should fail at profile INSERT (path 5, already tested), but verifies no partial domain/area/task orphans remain.

3. **Profile field verification** — Current `test_signup_creates_profile` checks name/email/userName but not subject, region, userPoolId fields.

4. **Domain INSERT zero-rows** (path 7) — Would require mocking cursor.execute to return 0 for domain INSERT specifically. Medium complexity.

5. **Task INSERT pymysql.Error** (path 20) — Could trigger by inserting a task with invalid area_fk after area step succeeds. Verifies event still returned (permissive).

### Intentionally Skipped (with rationale)

- **Paths 10-11, 16-17** (LAST_INSERT_ID failures): These can only occur if MySQL's `LAST_INSERT_ID()` returns 0 rows or throws, which is extremely unlikely after a successful INSERT. The `LAST_INSERT_ID()` function is guaranteed to return a value in the same session. Testing would require cursor mock — tests the mock, not the code.

- **Paths 13-14** (area INSERT failure): Very difficult to trigger naturally. Would need domain creation to succeed but area INSERT to fail — hard without schema manipulation.

## PatchedCursor Issues

### Current Implementation (conftest.py:163-170)
```python
def execute(self, sql, args=None):
    for prod, test in self.TABLE_MAP.items():
        sql = sql.replace(f' {prod} ', f' {test} ')
        sql = sql.replace(f' {prod}\n', f' {test}\n')
        sql = sql.replace(f'INTO {prod} ', f'INTO {test} ')
        sql = sql.replace(f'INTO {prod}\n', f'INTO {test}\n')
    return self._cursor.execute(sql, args)
```

### Problems
1. **Fragile string matching**: Relies on exact whitespace around table names. Won't match `FROM profiles` at end of line without trailing space/newline.
2. **Multiple replacement variants**: 4 patterns per table = 16 total replacements — easy to miss edge cases.
3. **No word boundary**: Could match partial names if any future table contains "profiles" as substring.

### Recommended Fix
Replace with single regex using word boundaries:
```python
import re

def execute(self, sql, args=None):
    for prod, test in self.TABLE_MAP.items():
        sql = re.sub(r'\b' + prod + r'\b', test, sql)
    return self._cursor.execute(sql, args)
```

## Cleanup Issues

### Current Implementation (conftest.py:221-230)
Only cleans up by `test_user_name`:
```python
cur.execute("DELETE FROM profiles2 WHERE id = %s", (test_user_name,))
```

### Problem
Tests in `test_02_event_types.py` and `test_03_edge_cases.py` create users with dynamic UUIDs:
- `forgot-pwd-{uuid}`, `unknown-trigger-{uuid}`, `no-trigger-{uuid}`
- `no-email-{uuid}`, `no-name-{uuid}`, `empty-req-{uuid}`

These tests have inline cleanup, but if a test fails mid-execution, the cleanup code may not run, leaving orphaned records.

### Recommended Fix
Track all created user IDs in a session-scoped list and clean them all up:
```python
@pytest.fixture(scope="session")
def created_users():
    return []

# In cleanup fixture, delete by all tracked IDs
```
