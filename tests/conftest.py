"""
Lambda-Cognito pytest shared fixtures.

All tests use darwin_dev test database. Never touches darwin production.

Since darwin_dev uses production-identical table names (profiles, domains,
areas, tasks), we only need to patch get_connection() to point at darwin_dev.
No SQL rewriting or table name translation needed.
"""
import sys
import os
import uuid

import pymysql
import pytest

# Add Lambda-Cognito root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_connection():
    """Direct pymysql connection to darwin_dev test database."""
    conn = pymysql.connect(
        host=os.environ['endpoint'],
        user=os.environ['username'],
        password=os.environ['db_password'],
        database='darwin_dev',
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
# Patched lambda invocation (darwin_dev database)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def invoke_cognito():
    """Invoke lambda_handler with connection patched to darwin_dev.

    The real lambda_function.py uses get_connection() which connects to the
    production darwin database. This fixture patches get_connection() to
    connect to darwin_dev instead. Since darwin_dev uses production-identical
    table names, no SQL rewriting is needed.

    Returns a callable: invoke_cognito(event) -> result
    """
    import lambda_function

    original_handler = lambda_function.lambda_handler

    def patched_handler(event, context=None):
        """Call lambda_handler with connection pointed at darwin_dev."""
        original_get_connection = lambda_function.get_connection

        def patched_get_connection():
            return pymysql.connect(
                host=os.environ['endpoint'],
                user=os.environ['username'],
                password=os.environ['db_password'],
                database='darwin_dev',
            )

        # Patch get_connection and reset module connection
        lambda_function.get_connection = patched_get_connection
        lambda_function.connection = None

        try:
            result = original_handler(event, context or {})
        finally:
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
            cur.execute("DELETE FROM tasks WHERE creator_fk = %s", (user_id,))
            cur.execute("DELETE FROM areas WHERE creator_fk = %s", (user_id,))
            cur.execute("DELETE FROM domains WHERE creator_fk = %s", (user_id,))
            cur.execute("DELETE FROM profiles WHERE id = %s", (user_id,))
    db_connection.commit()
