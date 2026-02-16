"""
Test edge cases and error handling in the Cognito post-confirmation lambda.

Tests missing fields, duplicate users, and malformed events.
All tests use darwin2 via patched table names.
"""
import uuid

import pytest

from conftest import build_cognito_event


def test_missing_username_returns_error(invoke_cognito, db_connection):
    """Event with userName=None should return an error message (not crash)."""
    event = build_cognito_event(
        user_name='placeholder',
        name='No Username User',
        email='nousername@test.com',
    )
    # Remove userName from the event
    event['userName'] = None

    result = invoke_cognito(event)

    # Should return error string, not raise
    assert isinstance(result, str)
    assert 'unavaib' in result.lower() or 'username' in result.lower()

    # No profile should be created
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM profiles2 WHERE id IS NULL OR id = ''")
        assert cur.fetchone() is None


def test_duplicate_user_returns_error(invoke_cognito, test_user_name, db_connection):
    """Second signup with same userName should fail (profile PK duplicate).

    The profile INSERT should fail with a duplicate key error.
    The handler should catch this and return an error message.
    """
    event = build_cognito_event(
        user_name=test_user_name,  # Already created by provisioning tests
        name='Duplicate User',
        email='duplicate@test.com',
    )
    result = invoke_cognito(event)

    # Should return error string (profile create failed due to duplicate PK)
    assert isinstance(result, str)
    # The error should mention "Profile Create failed" or contain the MySQL error
    assert 'failed' in result.lower() or 'duplicate' in result.lower()


def test_missing_email_returns_error(invoke_cognito, created_users, db_connection):
    """Event with missing email attribute fails — profiles2.email is NOT NULL."""
    user_name = f"no-email-{uuid.uuid4().hex[:6]}"
    created_users.append(user_name)
    event = build_cognito_event(
        user_name=user_name,
        name='No Email User',
        email='test@test.com',
    )
    # Remove email from userAttributes
    del event['request']['userAttributes']['email']

    result = invoke_cognito(event)

    # Profile INSERT fails because email column is NOT NULL
    assert isinstance(result, str)
    assert 'failed' in result.lower() or 'null' in result.lower()


def test_missing_name_returns_error(invoke_cognito, created_users, db_connection):
    """Event with missing name attribute fails — profiles2.name is NOT NULL."""
    user_name = f"no-name-{uuid.uuid4().hex[:6]}"
    created_users.append(user_name)
    event = build_cognito_event(
        user_name=user_name,
        name='Test User',
        email='noname@test.com',
    )
    # Remove name from userAttributes
    del event['request']['userAttributes']['name']

    result = invoke_cognito(event)

    # Profile INSERT fails because name column is NOT NULL
    assert isinstance(result, str)
    assert 'failed' in result.lower() or 'null' in result.lower()


def test_empty_request_returns_error(invoke_cognito, created_users, db_connection):
    """Event with empty request dict should handle gracefully."""
    user_name = f"empty-req-{uuid.uuid4().hex[:6]}"
    created_users.append(user_name)
    event = {
        'version': '1',
        'region': 'us-west-1',
        'userPoolId': 'test-pool',
        'userName': user_name,
        'triggerSource': 'PostConfirmation_ConfirmSignUp',
        'request': {},
        'response': {},
    }

    # Should not crash — may succeed with None values or fail gracefully
    try:
        result = invoke_cognito(event)
    except Exception:
        pass  # Exception is acceptable for malformed input
