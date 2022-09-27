from lambda_cognito_test import lambda_cognito_test

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

lambda_cognito_test(success_test)
#lambda_cognito_test(password_change)

