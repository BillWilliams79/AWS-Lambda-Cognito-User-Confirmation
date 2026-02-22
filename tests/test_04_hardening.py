"""
Additional test hardening for Lambda-Cognito.

Tests cover: profile field verification, connection reconnect,
duplicate signup with no orphans, and second invocation idempotency.
"""
import uuid

import pytest

from conftest import build_cognito_event


def test_profile_fields_complete(invoke_cognito, test_user_name, db_connection):
    """Verify all profile fields are populated correctly after signup.

    The provisioning tests check name/email/userName but not subject,
    region, or userPoolId. This test verifies the full field set.
    """
    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT id, name, email, subject, userName, region, userPoolId "
            "FROM profiles WHERE id = %s",
            (test_user_name,),
        )
        profile = cur.fetchone()

    assert profile is not None, "Profile should exist from provisioning tests"
    assert profile['id'] == test_user_name
    assert profile['userName'] == test_user_name
    assert profile['subject'] == test_user_name  # sub defaults to user_name in builder
    assert profile['region'] == 'us-west-1'
    assert profile['userPoolId'] == 'us-west-1_testpool'


def test_duplicate_signup_no_orphans(invoke_cognito, test_user_name, db_connection):
    """Duplicate signup fails at profile INSERT and leaves no orphan records.

    When a user signs up twice, the profile INSERT fails with a duplicate PK.
    This should NOT leave orphaned domains, areas, or tasks.
    """
    # Count existing records before duplicate attempt
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM domains WHERE creator_fk = %s", (test_user_name,))
        domains_before = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM areas WHERE creator_fk = %s", (test_user_name,))
        areas_before = cur.fetchone()['cnt']
        cur.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE creator_fk = %s", (test_user_name,))
        tasks_before = cur.fetchone()['cnt']

    # Attempt duplicate signup
    event = build_cognito_event(
        user_name=test_user_name,
        name='Duplicate Orphan Check',
        email='orphan-check@test.com',
    )
    result = invoke_cognito(event)

    # Should fail (profile duplicate)
    assert isinstance(result, str)

    # Verify no new records were created (no orphans)
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM domains WHERE creator_fk = %s", (test_user_name,))
        assert cur.fetchone()['cnt'] == domains_before
        cur.execute("SELECT COUNT(*) AS cnt FROM areas WHERE creator_fk = %s", (test_user_name,))
        assert cur.fetchone()['cnt'] == areas_before
        cur.execute("SELECT COUNT(*) AS cnt FROM tasks WHERE creator_fk = %s", (test_user_name,))
        assert cur.fetchone()['cnt'] == tasks_before


def test_signup_with_special_chars_in_name(invoke_cognito, created_users, db_connection):
    """Signup with special characters in name/email should succeed.

    Tests that parameterized queries handle special chars correctly.
    """
    user_name = f"cognito-test-special-{uuid.uuid4().hex[:6]}"
    created_users.append(user_name)
    event = build_cognito_event(
        user_name=user_name,
        name="O'Brien-Smith",
        email='obriensmith@test.com',
    )
    result = invoke_cognito(event)

    # Should succeed
    assert isinstance(result, dict)
    assert result.get('triggerSource') == 'PostConfirmation_ConfirmSignUp'

    # Verify the name was stored correctly
    with db_connection.cursor() as cur:
        cur.execute("SELECT name FROM profiles WHERE id = %s", (user_name,))
        profile = cur.fetchone()

    assert profile is not None
    assert profile['name'] == "O'Brien-Smith"


def test_provisioned_task_content(invoke_cognito, test_user_name, db_connection):
    """Verify the instructional task has expected content and field values.

    The instructional task should mention Domains and Areas, have priority=1,
    done=0, and be linked to the Home area via area_fk.
    """
    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT t.description, t.priority, t.done, a.area_name "
            "FROM tasks t JOIN areas a ON t.area_fk = a.id "
            "WHERE t.creator_fk = %s",
            (test_user_name,),
        )
        task = cur.fetchone()

    assert task is not None
    assert 'Domains' in task['description']
    assert 'Areas' in task['description']
    assert task['priority'] == 1
    assert task['done'] == 0
    assert task['area_name'] == 'Home'


def test_connection_reuse_across_invocations(invoke_cognito, created_users, db_connection):
    """Two sequential signups should both succeed (connection reuse/reconnect).

    Verifies the get_connection() ping/reconnect pattern works across
    multiple lambda invocations within the same process.
    """
    user1 = f"cognito-test-conn1-{uuid.uuid4().hex[:6]}"
    user2 = f"cognito-test-conn2-{uuid.uuid4().hex[:6]}"
    created_users.extend([user1, user2])

    # First invocation
    event1 = build_cognito_event(user_name=user1, name='Conn Test 1', email='conn1@test.com')
    result1 = invoke_cognito(event1)
    assert isinstance(result1, dict)

    # Second invocation — should reuse or reconnect
    event2 = build_cognito_event(user_name=user2, name='Conn Test 2', email='conn2@test.com')
    result2 = invoke_cognito(event2)
    assert isinstance(result2, dict)

    # Both users should have profiles
    with db_connection.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM profiles WHERE id IN (%s, %s)", (user1, user2))
        assert cur.fetchone()['cnt'] == 2
