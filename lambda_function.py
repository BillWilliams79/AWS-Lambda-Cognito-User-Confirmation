import json
import pymysql
from rds_config_secrets import *

from classifier import varDump, pretty_print_sql

# setup database access
print('Cognito Post User Confirmation Lambda Cold Start')

connection = pymysql.connect(host = endpoint,
                             user = username,
                             password = password,
                             database = db,)

varDump(connection, 'Lambda Init: connection details')


def lambda_handler(event, context):

    print('Lambda Invoked: Cognito Post User Confirmation Lambda')
    sql_table = "profiles"

    name = event.get('request', {}).get('userAttributes', {}).get('name')
    email = event.get('request', {}).get('userAttributes', {}).get('email')

    # userName is absolutely required for use in the database
    userName = event.get('userName')
    if userName == None:
        errorMsg = f"User Profile Create failed for user {name}, {email}: {e.args[0]} {e.args[1]}"
        print(errorMsg)
        return

    sub = event.get('request', {}).get('userAttributes', {}).get('sub')
    region = event.get('region')
    userPoolId = event.get('userPoolId')
    
    try:
        # insert a profile record, hard code OK: mostly invariant business logic
        sql_statement = f"""
                    INSERT INTO {sql_table} (id, name, email, subject, userName, region, userPoolId)
                    VALUES ('{userName}', '{name}', '{email}', '{sub}', '{userName}', '{region}', '{userPoolId}');
        """
        pretty_print_sql(sql_statement, 'PUT NEW USER')

        cursor = connection.cursor()
        affected_put_rows = cursor.execute(sql_statement)

        if affected_put_rows > 0:
            connection.commit()
        else:
            errorMsg = f"User Profile Create failed for user {name} : {email}. Zero affected rows returned."
            print(errorMsg)

    except pymysql.Error as e:

        errorMsg = f"User Profile Create failed for user {name} : {email}: {e.args[0]} {e.args[1]}"
        print(errorMsg)

    # for now, errors print to CloudWatch and return OK.
    # later we can queue this up and have more sophisticated error handler there (or here)
    return event
