"""
Lambda-Cognito pytest shared fixtures.

All tests use darwin2 test database. Never touches darwin production.

The Cognito lambda_function.py hardcodes production table names (profiles,
domains, areas, tasks). For testing against darwin2, we provide an
`invoke_cognito` fixture that patches the function to use darwin2 table
names (profiles2, domains2, areas2, tasks2) before calling lambda_handler.
"""
import sys
import os
import re
import uuid
import importlib
from unittest.mock import patch

import pymysql
import pytest

# Add Lambda-Cognito root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_connection():
    """Direct pymysql connection to darwin2 test database."""
    conn = pymysql.connect(
        host=os.environ['endpoint'],
        user=os.environ['username'],
        password=os.environ['db_password'],
        database='darwin2',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Test data isolation
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def test_user_name():
    """Unique userName for test isolation (acts as creator_fk/profile id)."""
    return f"cognito-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session")
def created_users():
    """Track all user IDs created during the session for comprehensive cleanup."""
    return []


# ---------------------------------------------------------------------------
# Cognito event builder
# ---------------------------------------------------------------------------

def build_cognito_event(
    user_name,
    trigger_source='PostConfirmation_ConfirmSignUp',
    name='Test User',
    email='test@test.com',
    sub=None,
    region='us-west-1',
    user_pool_id='us-west-1_testpool',
):
    """Build a Cognito PostConfirmation event dict."""
    return {
        'version': '1',
        'region': region,
        'userPoolId': user_pool_id,
        'userName': user_name,
        'callerContext': {
            'awsSdkVersion': 'aws-sdk-unknown-unknown',
            'clientId': 'test-client-id',
        },
        'triggerSource': trigger_source,
        'request': {
            'userAttributes': {
                'sub': sub or user_name,
                'email_verified': 'true',
                'cognito:user_status': 'CONFIRMED',
                'cognito:email_alias': email,
                'name': name,
                'email': email,
            },
        },
        'response': {},
    }


# ---------------------------------------------------------------------------
# Patched lambda invocation (darwin2 table names)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def invoke_cognito():
    """Invoke lambda_handler with table names patched to darwin2 (*2 suffix).

    The real lambda_function.py uses hardcoded table names (profiles, domains,
    areas, tasks) targeting the production darwin database. This fixture patches
    the function source to use darwin2 table names instead.

    Returns a callable: invoke_cognito(event) -> result
    """
    # Import the module fresh so we can intercept it
    import lambda_function

    # Save original handler
    original_handler = lambda_function.lambda_handler

    def patched_handler(event, context=None):
        """Call lambda_handler with table names rewritten to *2 variants."""
        # Monkey-patch the module's get_connection to use darwin2
        original_get_connection = lambda_function.get_connection

        def patched_get_connection():
            global _test_conn
            conn = pymysql.connect(
                host=os.environ['endpoint'],
                user=os.environ['username'],
                password=os.environ['db_password'],
                database='darwin2',
            )
            return conn

        # Temporarily replace get_connection and intercept SQL execution
        lambda_function.get_connection = patched_get_connection

        # Patch cursor.execute to rewrite table names in SQL
        original_connect = pymysql.connect

        class PatchedConnection:
            """Wraps a real connection, rewriting table names in execute() calls."""

            def __init__(self, conn):
                self._conn = conn

            def cursor(self):
                return PatchedCursor(self._conn.cursor())

            def commit(self):
                return self._conn.commit()

            def ping(self, **kwargs):
                return self._conn.ping(**kwargs)

            def close(self):
                return self._conn.close()

        class PatchedCursor:
            """Wraps a cursor, rewriting table names in SQL."""

            TABLE_MAP = {
                'profiles': 'profiles2',
                'domains': 'domains2',
                'areas': 'areas2',
                'tasks': 'tasks2',
            }

            def __init__(self, cursor):
                self._cursor = cursor

            def execute(self, sql, args=None):
                # Rewrite production table names to darwin2 test equivalents
                # Uses word-boundary regex to avoid partial matches and
                # handle all positions (after FROM, INTO, JOIN, etc.)
                for prod, test in self.TABLE_MAP.items():
                    sql = re.sub(r'\b' + prod + r'\b', test, sql)
                return self._cursor.execute(sql, args)

            def fetchone(self):
                return self._cursor.fetchone()

            def fetchall(self):
                return self._cursor.fetchall()

            def close(self):
                return self._cursor.close()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self._cursor.close()

        def patched_connect(**kwargs):
            kwargs['database'] = 'darwin2'
            real_conn = original_connect(**kwargs)
            return PatchedConnection(real_conn)

        # Apply patches
        lambda_function.get_connection = lambda: PatchedConnection(
            pymysql.connect(
                host=os.environ['endpoint'],
                user=os.environ['username'],
                password=os.environ['db_password'],
                database='darwin2',
            )
        )

        # Reset module connection so it gets a fresh patched one
        lambda_function.connection = None

        try:
            result = original_handler(event, context or {})
        finally:
            # Restore original
            lambda_function.get_connection = original_get_connection
            lambda_function.connection = None

        return result

    return patched_handler


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data(db_connection, test_user_name, created_users):
    """Clean up all test data after session completes.

    Deletes data for both the primary test_user_name and any additional
    users tracked in the created_users list (from event type and edge
    case tests that create users with dynamic UUIDs).
    """
    yield
    # Collect all user IDs to clean up
    all_users = list(set([test_user_name] + created_users))
    with db_connection.cursor() as cur:
        for user_id in all_users:
            cur.execute("DELETE FROM tasks2 WHERE creator_fk = %s", (user_id,))
            cur.execute("DELETE FROM areas2 WHERE creator_fk = %s", (user_id,))
            cur.execute("DELETE FROM domains2 WHERE creator_fk = %s", (user_id,))
            cur.execute("DELETE FROM profiles2 WHERE id = %s", (user_id,))
    db_connection.commit()
