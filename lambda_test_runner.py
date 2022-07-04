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
                                                   'cognito:email_alias': 'darwintestuser@proton.me',
                                                   'name': 'Darwin Guy',
                                                   'email': 'darwintestuser@proton.me'}},
                    'response': {},
        },
        'context': {},
        'test_name': 'Postive test case user Darwin Guy',
}

lambda_cognito_test(success_test)