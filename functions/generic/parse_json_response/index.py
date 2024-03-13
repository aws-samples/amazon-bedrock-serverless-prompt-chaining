import json
from jsonschema import validate


# Parse the JSON response string into an object and validate it against the JSON schema.
# Return the validated object.
def handler(event, context):
    response_string = event["response_string"]
    response_object = json.loads(response_string)

    json_schema = event["json_schema"]
    validate(instance=response_object, schema=json_schema)

    return response_object
