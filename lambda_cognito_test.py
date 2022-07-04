import json
from lambda_function import lambda_handler
from classifier import varDump

#
# Generic Lambda Rest API test execututor. Uses a dictionary to pass parameters. 
#
def lambda_cognito_test(config):
    
    print(f"\n**** Execute Lambda-Cognito Test: { config['test_name'] } ****\n")

    event = config['event']
    context = config['context']

    return_value = lambda_handler(event, context)
