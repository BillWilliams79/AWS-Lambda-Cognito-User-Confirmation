import json
import pymysql
from rds_config_secrets import *

from classifier import varDump, pretty_print_sql

# setup database access
print('Lambda Cognito: attempting database connection...')
connection = pymysql.connect(host = endpoint,
                             user = username,
                             password = password,
                             database = db,)

cursor = connection.cursor()

try:
    # default session value "read repeatable" breaks ability to see
    # updates from back end...READ COMITTED enable select to return all 
    # committed data from all sources
    sql_statement = "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED"
    no_data = cursor.execute(sql_statement)

except pymysql.Error as e:
    errorMsg = f"Set session isolation read committed failed: {e.args[0]} {e.args[1]}"
    print(errorMsg)

try:
    # Required to allow large data returns for reads using group_concat_max_len
    cursor.execute("SET SESSION group_concat_max_len = 65536")
except pymysql.Error as e:
    errorMsg = f"Set session group_concat_max_len 64k failed: {e.args[0]} {e.args[1]}"
    print(errorMsg)

varDump(connection, 'Lambda Init: connection details')


def lambda_handler(event, context):

    print('Lambda Invoked: Cognito Post User Confirmation Lambda')
    table = "profiles"

    name = event['request']['userAttributes']['name']
    email = event['request']['userAttributes']['email']
    sub = event['request']['userAttributes']['sub']
    userName = event['userName']
    region = event['region']
    userPoolId = event['userPoolId']

    try:
        # insert a profile record, hard code OK: mostly invariant business logic
        sql_statement = f"""
                    INSERT INTO {table} (name, email, subject, userName, region, userPoolId)
                    VALUES ('{name}', '{email}', '{sub}', '{userName}', '{region}', '{userPoolId}');
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

        errorMsg = f"User Profile Create failedfor user {name} : {email}: {e.args[0]} {e.args[1]}"
        print(errorMsg)

    # for now, errors print to CloudWatch and return OK.
    # later we can queue this up and have more sophisticated error handler there (or here)
    return event
