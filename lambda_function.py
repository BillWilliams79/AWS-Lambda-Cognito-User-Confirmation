import os
import pymysql

from classifier import varDump, pretty_print_sql

# retrieve db credential environment variables
endpoint = os.environ['endpoint']
username = os.environ['username']
password = os.environ['db_password']
db = os.environ['db_name']

# setup database access
print('Cognito Post User Confirmation Lambda Cold Start')

connection = pymysql.connect(host = endpoint,
                             user = username,
                             password = password,
                             database = db,)

varDump(connection, 'Lambda Init: connection details')


def lambda_handler(event, context):

    # the purpose of this lambda is to create a user profile in the database
    # and (for now) instantiate initial user data. Later possibly refactor to send
    # a message to a separate lambda to service the user data create request.
    # this is suitable for now.

    print('Lambda Invoked: Cognito Post User Confirmation Lambda')
    sql_table = "profiles"


    # STEP 1 => process Cognito event to retrieve user information
    name = event.get('request', {}).get('userAttributes', {}).get('name')
    email = event.get('request', {}).get('userAttributes', {}).get('email')

    # userName is absolutely required for use in the database, cannot proceed without
    userName = event.get('userName')

    if userName == None:
        error_message = f"Username data unavaible from Cognito for user: {name}, {email}"
        print(error_message)
        return error_message

    sub = event.get('request', {}).get('userAttributes', {}).get('sub')
    region = event.get('region')
    userPoolId = event.get('userPoolId')

    # STEP 2 => create user profile
    try:
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
            # profile must be created, otherwise user is invalid in the App
            error_message = f"User Profile Create failed for user {name} : {email}. Zero affected rows returned."
            print(error_message)
            return error_message

    except pymysql.Error as e:
        # profile must be created, otherwise user is invalid in the App
        error_message = f"User Profile Create failed for user {name} : {email}: {e.args[0]} {e.args[1]}"
        print(error_message)
        return(error_message)

    # STEP 3a => Create initial Domain record for the user.
    try:
        sql_table = 'domains'
        domain_name = 'Personal'
        closed = 0

        sql_statement = f"""
                    INSERT INTO {sql_table} (domain_name, creator_fk, closed)
                    VALUES ('{domain_name}', '{userName}', '{closed}');
        """
        pretty_print_sql(sql_statement, 'CREATE NEW DOMAIN')

        cursor = connection.cursor()
        affected_put_rows = cursor.execute(sql_statement)

        if affected_put_rows > 0:
            connection.commit()
        else:
            # print message and exit successs back to Cognito. User created, but default data wasn't which is OK
            error_message = f"Warning: Domain Create failed for user {name} : {email}. Zero affected rows returned."
            print(error_message)
            return event;

    except pymysql.Error as e:
        # print message and exit successs back to Cognito. User created, but default data wasn't which is OK
        error_message = f"Warning: Domain Create failed for user {name} : {email}: {e.args[0]} {e.args[1]}"
        print(error_message)
        return event; 


    # STEP 3b => retrieve ID of the initial domain for use in STEP 4
    try:
        # mySql syntax to retrieve ID of prior insert in this session
        sql_statement= f"""SELECT LAST_INSERT_ID()"""
        affected_rows = cursor.execute(sql_statement)

        if affected_rows > 0:
            domain_fk = cursor.fetchone()
        else:
            # Without new domain Id, creation of user data cannot continue
            print(f"Warning: failed to read last_insert_id for created domain.")
            return event

    except pymysql.Error as e:
        # Without new domain Id, creation of user data cannot continue
        print(f"Warning: failed to read last_insert_id for created domain.")
        return event


    # STEP 4 => Create initial Area for the user
    try:
        sql_table = 'areas'
        area_name = 'Home'
        closed = 0

        sql_statement = f"""
                    INSERT INTO {sql_table} (area_name, domain_fk, creator_fk, closed)
                    VALUES ('{area_name}', '{domain_fk[0]}', '{userName}', '{closed}');
        """
        pretty_print_sql(sql_statement, 'CREATE NEW AREA')

        cursor = connection.cursor()
        affected_put_rows = cursor.execute(sql_statement)

        if affected_put_rows > 0:
            connection.commit()
        else:
            # print message and exit successs back to Cognito. User created, but default data wasn't which is OK
            error_message = f"Warning: Area Create failed for user {name} : {email}. Zero affected rows returned."
            print(error_message)
            return event;

    except pymysql.Error as e:
        # print message and exit successs back to Cognito. User created, but default data wasn't which is OK
        error_message = f"Warning: Area Create failed for user {name} : {email}: {e.args[0]} {e.args[1]}"
        print(error_message)
        return event; 

    # STEP 4b => retrieve ID of the initial area for use in STEP 5
    try:
        # mySql syntax to retrieve ID of prior insert in this session
        sql_statement= f"""SELECT LAST_INSERT_ID()"""
        affected_rows = cursor.execute(sql_statement)

        if affected_rows > 0:
            area_fk = cursor.fetchone()
        else:
            # Without new area Id, creation of user data cannot continue
            print(f"Warning: failed to read last_insert_id for created area.")
            return event

    except pymysql.Error as e:
        # Without new area Id, creation of user data cannot continue
        print(f"Warning: failed to read last_insert_id for created area.")
        return event


    # STEP 5 => Create initial Task for the user
    try:
        sql_table = 'tasks'
        priority = 1
        done = 0
        description = 'Tasks are organized in two levels: Domains and Areas. On the Plan page, Domains correspond to the tabs, areas to the cards. All tasks are stored in an Area and sorted by priority. When completed, tasks show up in the calendar view.'

        sql_statement = f"""
                    INSERT INTO {sql_table} (priority, done, description, area_fk, creator_fk)
                    VALUES ('{priority}', '{done}', '{description}', '{area_fk[0]}', '{userName}');
        """
        pretty_print_sql(sql_statement, 'CREATE NEW AREA')

        cursor = connection.cursor()
        affected_put_rows = cursor.execute(sql_statement)

        if affected_put_rows > 0:
            connection.commit()
        else:
            # print message and exit successs back to Cognito. User created, but default data wasn't which is OK
            error_message = f"Warning: Task create failed for user {name} : {email}. Zero affected rows returned."
            print(error_message)
            return event;

    except pymysql.Error as e:
        # print message and exit successs back to Cognito. User created, but default data wasn't which is OK
        error_message = f"Warning: Task create failed for user {name} : {email}: {e.args[0]} {e.args[1]}"
        print(error_message)
        return event; 

    # for now, errors print to CloudWatch and return OK.
    # later we can queue this up and have more sophisticated error handler there (or here)
    return event
