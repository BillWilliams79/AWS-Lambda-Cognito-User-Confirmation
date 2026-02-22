"""
Test the full Cognito post-confirmation signup provisioning flow.

Verifies that lambda_handler creates: profile → domain → area → task
when triggered by PostConfirmation_ConfirmSignUp.

All tests use darwin_dev via patched table names.
"""
import json

import pytest

from conftest import build_cognito_event


def test_signup_creates_profile(invoke_cognito, test_user_name, db_connection):
    """PostConfirmation_ConfirmSignUp creates a profile record."""
    event = build_cognito_event(
        user_name=test_user_name,
        name='Provisioning Test User',
        email='provision@test.com',
    )
    result = invoke_cognito(event)

    # Should return the event (success)
    assert isinstance(result, dict)
    assert result.get('triggerSource') == 'PostConfirmation_ConfirmSignUp'

    # Verify profile was created in darwin_dev
    with db_connection.cursor() as cur:
        cur.execute("SELECT * FROM profiles WHERE id = %s", (test_user_name,))
        profile = cur.fetchone()

    assert profile is not None
    assert profile['name'] == 'Provisioning Test User'
    assert profile['email'] == 'provision@test.com'
    assert profile['userName'] == test_user_name


def test_signup_creates_domain(invoke_cognito, test_user_name, db_connection):
    """PostConfirmation creates a 'Personal' domain for the user."""
    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM domains WHERE creator_fk = %s",
            (test_user_name,),
        )
        domains = cur.fetchall()

    assert len(domains) >= 1
    personal = [d for d in domains if d['domain_name'] == 'Personal']
    assert len(personal) == 1
    assert personal[0]['closed'] == 0


def test_signup_creates_area(invoke_cognito, test_user_name, db_connection):
    """PostConfirmation creates a 'Home' area under the Personal domain."""
    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM areas WHERE creator_fk = %s",
            (test_user_name,),
        )
        areas = cur.fetchall()

    assert len(areas) >= 1
    home = [a for a in areas if a['area_name'] == 'Home']
    assert len(home) == 1
    assert home[0]['closed'] == 0


def test_signup_creates_task(invoke_cognito, test_user_name, db_connection):
    """PostConfirmation creates an instructional task in the Home area."""
    with db_connection.cursor() as cur:
        cur.execute(
            "SELECT * FROM tasks WHERE creator_fk = %s",
            (test_user_name,),
        )
        tasks = cur.fetchall()

    assert len(tasks) >= 1
    # The instructional task mentions "Domains" and "Areas"
    instructional = [t for t in tasks if 'Domains' in (t['description'] or '')]
    assert len(instructional) == 1
    assert instructional[0]['priority'] == 1
    assert instructional[0]['done'] == 0


def test_signup_full_hierarchy_linked(invoke_cognito, test_user_name, db_connection):
    """Verify the full provisioned hierarchy is properly linked via FKs."""
    with db_connection.cursor() as cur:
        # Join task → area → domain → profile
        cur.execute(
            "SELECT t.description, a.area_name, d.domain_name, p.name "
            "FROM tasks t "
            "JOIN areas a ON t.area_fk = a.id "
            "JOIN domains d ON a.domain_fk = d.id "
            "JOIN profiles p ON d.creator_fk = p.id "
            "WHERE p.id = %s",
            (test_user_name,),
        )
        rows = cur.fetchall()

    assert len(rows) >= 1
    row = rows[0]
    assert row['area_name'] == 'Home'
    assert row['domain_name'] == 'Personal'
    assert row['name'] == 'Provisioning Test User'
