import json
from jsonschema import validate
import os

json_schema = json.loads(os.environ["SCHEMA"])


# Parse a JSON escaped string into an object and validate it against the JSON schema.
# Return the validated object.
def handler(event, context):
    json_string = event["node"]["inputs"][0]["value"]
    response_object = json.loads(json_string)

    validate(instance=response_object, schema=json_schema)

    return response_object
