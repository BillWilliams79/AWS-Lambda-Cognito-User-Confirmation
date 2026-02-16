"""
Test event type discrimination.

The Cognito lambda should only provision data for PostConfirmation_ConfirmSignUp.
All other trigger sources should be no-ops (return event unchanged).
"""
import uuid

import pytest

from conftest import build_cognito_event


def test_forgot_password_is_noop(invoke_cognito, db_connection):
    """PostConfirmation_ConfirmForgotPassword should NOT create any records."""
    user_name = f"forgot-pwd-{uuid.uuid4().hex[:6]}"
    event = build_cognito_event(
        user_name=user_name,
        trigger_source='PostConfirmation_ConfirmForgotPassword',
        name='Forgot Password User',
        email='forgot@test.com',
    )
    result = invoke_cognito(event)

    # Should return event unchanged
    assert isinstance(result, dict)
    assert result.get('userName') == user_name

    # Verify NO profile was created
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM profiles2 WHERE id = %s", (user_name,))
        assert cur.fetchone() is None


def test_unknown_trigger_is_noop(invoke_cognito, db_connection):
    """Unknown trigger source should NOT create any records."""
    user_name = f"unknown-trigger-{uuid.uuid4().hex[:6]}"
    event = build_cognito_event(
        user_name=user_name,
        trigger_source='SomeOtherTrigger',
        name='Unknown Trigger User',
        email='unknown@test.com',
    )
    result = invoke_cognito(event)

    assert isinstance(result, dict)

    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM profiles2 WHERE id = %s", (user_name,))
        assert cur.fetchone() is None


def test_missing_trigger_source_is_noop(invoke_cognito, db_connection):
    """Event with no triggerSource should NOT create any records."""
    user_name = f"no-trigger-{uuid.uuid4().hex[:6]}"
    event = {
        'version': '1',
        'region': 'us-west-1',
        'userPoolId': 'test-pool',
        'userName': user_name,
        'request': {
            'userAttributes': {
                'sub': user_name,
                'name': 'No Trigger User',
                'email': 'notrigger@test.com',
            },
        },
        'response': {},
    }
    result = invoke_cognito(event)

    assert isinstance(result, dict)

    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM profiles2 WHERE id = %s", (user_name,))
        assert cur.fetchone() is None
