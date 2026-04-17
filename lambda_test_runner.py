from lambda_cognito_test import lambda_cognito_test
from lambda_function import lambda_handler, connection

# Synthetic user IDs used by the tests below. Stable so pre-test cleanup is reliable.
TEST_USER_IDS = (
    '67166f09-e83f-4724-a90d-00e21bc36a9c',  # success_test
    '99999999-ffff-4fff-bfff-999999999999',  # column_drift_regression
)

def cleanup_test_rows():
    """Delete any rows left from a prior run. FK cascade removes domains/areas/tasks."""
    placeholders = ','.join(["'%s'" % uid for uid in TEST_USER_IDS])
    cur = connection.cursor()
    cur.execute(f"DELETE FROM profiles WHERE id IN ({placeholders})")
    connection.commit()
    print(f"Pre-test cleanup: removed {cur.rowcount} profile rows")


# Success path - good data is passed and user info should be instantiated in the database
success_test = {
        'event' : {
                    'version': '1',
                    'region': 'us-west-1',
                    'userPoolId': 'us-west-1_jqN0WLASK',
                    'userName': '67166f09-e83f-4724-a90d-00e21bc36a9c',
                    'callerContext': {'awsSdkVersion': 'aws-sdk-unknown-unknown',
                                      'clientId': '4qv8m44mllqllljbenbeou4uis'},
                    'triggerSource': 'PostConfirmation_ConfirmSignUp',
                    'request': {'userAttributes': {'sub': '67166f09-e83f-4724-a90d-00e21bc36a9c',
                                                   'email_verified': 'true',
                                                   'cognito:user_status': 'CONFIRMED',
                                                   'cognito:email_alias': 'testrunner@email.com',
                                                   'name': 'Test Runner name',
                                                   'email': 'testrunner@email.com'}},
                    'response': {},
        },
        'context': {},
        'test_name': 'Postive test case, creates Test Runner account in MySQL',
}

password_change = {
    'event' : {
                'version': '1',
                'region': 'us-west-1',
                'userPoolId': 'us-west-1_jqN0WLASK',
                'userName': '00010203-000d-4470-8be4-1792d8261f69',
                'callerContext': {
                                      'awsSdkVersion': 'aws-sdk-unknown-unknown',
                                      'clientId': '4qv8m44mllqllljbenbeou4uis'
                                 },
                'triggerSource': 'PostConfirmation_ConfirmForgotPassword',
                'request': {'userAttributes': {
                                                   'sub': '00010203-000d-4470-8be4-1792d8261f69',
                                                   'email_verified': 'true',
                                                   'cognito:user_status': 'CONFIRMED',
                                                   'cognito:email_alias': 'barney@rubble.com',
                                                   'name': 'Barney R', 'email': 'barney@rubble.com'
                                              }
                },
                'response': {}
             },
     'context': {},
     'test_name': 'Negative test case - confirmation lambda called during password change',
}

# Regression test for req #2171 — guards against reintroducing any of the dropped
# profile columns (subject, userName, region, userPoolId) into the INSERT. If the
# column list drifts, the handler returns an error string instead of the event.
column_drift_regression = {
    'event' : {
                'version': '1',
                'region': 'us-west-1',
                'userPoolId': 'us-west-1_jqN0WLASK',
                'userName': '99999999-ffff-4fff-bfff-999999999999',
                'callerContext': {'awsSdkVersion': 'aws-sdk-unknown-unknown',
                                  'clientId': '4qv8m44mllqllljbenbeou4uis'},
                'triggerSource': 'PostConfirmation_ConfirmSignUp',
                'request': {'userAttributes': {'sub': '99999999-ffff-4fff-bfff-999999999999',
                                               'email_verified': 'true',
                                               'cognito:user_status': 'CONFIRMED',
                                               'name': 'Column Drift Regression',
                                               'email': 'drift@regression.test'}},
                'response': {},
    },
    'context': {},
    'test_name': 'Regression req #2171 - profile INSERT column list matches current schema',
}


if __name__ == '__main__':
    cleanup_test_rows()

    # success_test
    result = lambda_handler(success_test['event'], success_test['context'])
    ok = isinstance(result, dict) and result is success_test['event']
    print(f"[{'PASS' if ok else 'FAIL'}] {success_test['test_name']}")
    if not ok:
        print(f"  expected event dict, got: {result!r}")

    # column_drift_regression
    result = lambda_handler(column_drift_regression['event'], column_drift_regression['context'])
    ok = isinstance(result, dict) and result is column_drift_regression['event']
    print(f"[{'PASS' if ok else 'FAIL'}] {column_drift_regression['test_name']}")
    if not ok:
        print(f"  expected event dict, got: {result!r}")

    cleanup_test_rows()
