# Lambda Cognito - Project Guide

## Overview
AWS Lambda function triggered by Amazon Cognito's **Post User Confirmation** event. When a new user signs up and confirms their account, this Lambda provisions their initial data in an RDS MySQL database: a user profile, a default "Personal" domain, a default "Home" area, and an instructional task.

## Architecture

### Trigger Flow
```
Cognito User Pool -> PostConfirmation_ConfirmSignUp -> Lambda -> RDS MySQL
```

### Data Provisioning Sequence (lambda_function.py)
1. Validate trigger source (only `PostConfirmation_ConfirmSignUp`)
2. Extract user attributes from Cognito event (name, email, userName, sub, region, userPoolId)
3. INSERT into `profiles` table (critical - failure returns error)
4. INSERT into `domains` table ("Personal" domain)
5. Retrieve domain ID via `LAST_INSERT_ID()`
6. INSERT into `areas` table ("Home" area, linked to domain)
7. Retrieve area ID via `LAST_INSERT_ID()`
8. INSERT into `tasks` table (instructional task, linked to area)
9. Return event to Cognito

### Error Handling Strategy
- Profile creation failure: returns error to Cognito (blocks signup)
- Domain/Area/Task failures: logs warning, returns event (signup succeeds with partial data)

### Database Schema (referenced tables)
- `profiles` - id, name, email, subject, userName, region, userPoolId
- `domains` - domain_name, creator_fk, closed
- `areas` - area_name, domain_fk, creator_fk, closed
- `tasks` - priority, done, description, area_fk, creator_fk

### File Structure
- `lambda_function.py` - Main Lambda handler (deployed to AWS)
- `classifier.py` - Debug utilities (varDump, pretty_print_sql)
- `rest_api_utils.py` - REST response formatter (currently unused by this Lambda)
- `lambda_cognito_test.py` - Test executor framework
- `lambda_test_runner.py` - Test case definitions
- `exports.sh` - Local env var setup for testing (DO NOT COMMIT - in .gitignore)
- `pymysql/` - Vendored PyMySQL 1.0.2 library (bundled for Lambda deployment)
- `_data_sample/` - Sample Cognito event payloads

### Environment Variables (required on AWS Lambda)
- `endpoint` - RDS MySQL hostname
- `username` - Database username
- `db_password` - Database password
- `db_name` - Database name

### Dependencies
- PyMySQL 1.0.2 (vendored in-repo, not pip-installed at deploy time)

## Known Issues

### Critical: SQL Injection Vulnerability
All SQL in `lambda_function.py` uses f-string interpolation with user-supplied values. Must migrate to parameterized queries (`cursor.execute(sql, params)`).

### Critical: Stale Database Connection
Connection is created at module scope (cold start) with no reconnection logic. RDS idle timeout or failover will break all subsequent invocations.

### Bugs
- `rest_api_utils.py:16` - `isBase64Encoded` is string `'false'` instead of boolean `False`
- `rest_api_utils.py:25,33` - Status code compared as string but cast to int; error body double-JSON-encoded
- `lambda_function.py:48` - Typo: "unavaible" -> "unavailable"
- `lambda_function.py:189` - Log label says "CREATE NEW AREA" but this is the task INSERT
- `lambda_function.py:12` (commented out) - `{endpoint, username, password, db}` is a set, not dict
- `lambda_function.py:89,138,187` - Integer columns (closed, priority, done) quoted as strings in SQL
- `.gitignore:4` - `/pymyswl` is a typo for `/pymysql`
- `lambda_test_runner.py:22` - Typo: "Postive" -> "Positive"

## Development Notes

### Local Testing
```bash
source ./exports.sh        # load DB credentials into env
python lambda_test_runner.py
```

### Deployment
Lambda is deployed as a zip bundle containing lambda_function.py, classifier.py, rest_api_utils.py, and the pymysql/ directory.

### Git Conventions
- Commit messages describe what was fixed and why
- Keep credentials out of version control (use exports.sh locally, Lambda env vars in AWS)
