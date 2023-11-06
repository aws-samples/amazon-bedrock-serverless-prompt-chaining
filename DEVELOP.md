## Development guide

### Setup

Install both nodejs and python on your computer.

Install CDK:
```
npm install -g aws-cdk
```

Set up a virtual env:
```
python3 -m venv .venv

source .venv/bin/activate

pip install -r requirements.txt

pip install boto3
```
After this initial setup, you only need to run `source .venv/bin/activate` to use the virtual env for further development.

### Deploy the demo application

Fork this repo to your own GitHub account.
Edit the file `cdk_stacks.py`. Search for `parent_domain` and fill in your own DNS domain, such as `my-domain.com`.
The demo application will be hosted at `https://bedrock-serverless-prompt-chaining.my-domain.com`.
Push this change to your fork repository.

Set up a Weasyprint Lambda layer in your account. One of the examples in the demo application uses this library to generate PDF files.
```
git clone https://github.com/kotify/cloud-print-utils.git

cd cloud-print-utils

make build/weasyprint-layer-python3.8.zip

aws lambda publish-layer-version \
    --region us-west-2 \
    --layer-name weasyprint \
    --zip-file fileb://build/weasyprint-layer-python3.8.zip \
    --compatible-runtimes "python3.8" \
    --license-info "MIT" \
    --description "fonts and libs required by weasyprint"

aws ssm put-parameter --region us-west-2 \
    --name WeasyprintLambdaLayer \
    --type String \
    --value <value of LayerVersionArn from above command's output>
```

Deploy all the demo stacks:
```
cdk deploy --app 'python3 cdk_stacks.py' --all
```

The demo application will be hosted at `https://bedrock-serverless-prompt-chaining.my-domain.com`,
behind Cognito-based user authentication.
To add users that can log into the demo application, select the `bedrock-serverless-prompt-chaining-demo` user pool on the
[Cognito console](https://us-west-2.console.aws.amazon.com/cognito/v2/idp/user-pools?region=us-west-2)
and click "Create user".

As part of deploying the demo application, an SNS topic `bedrock-serverless-prompt-chaining-notifications`
will be created and will receive notifications about demo failures.
An email address or a [chat bot](https://docs.aws.amazon.com/chatbot/latest/adminguide/setting-up.html)
can be subscribed to the topic to receive notifications when the demo's alarms fire.

### Deploy the demo pipeline

The demo pipeline will automatically keep your deployed demo application in sync with the latest changes in your fork repository.

Edit the file `pipeline/pipeline_stack.py`.
Search for `owner` and fill in the GitHub account that owns your fork repository.
Push this change to your fork.

Deploy the pipeline:
```
cdk deploy --app 'python3 pipeline_stack.py'
```

Activate the CodeStar Connections connection created by the pipeline stack.
Go to the [CodeStar Connections console](https://console.aws.amazon.com/codesuite/settings/connections?region=us-west-2),
select the `bedrock-prompt-chain-repo` connection, and click "Update pending connection".
Then follow the prompts to connect your GitHub account and repos to AWS.
When finished, the `bedrock-prompt-chain-repo` connection should have the "Available" status.

Go to the [pipeline's page in the CodePipeline console](https://us-west-2.console.aws.amazon.com/codesuite/codepipeline/pipelines/bedrock-serverless-prompt-chaining-demo/view?region=us-west-2),
and click "Release change" to restart the pipeline.

As part of deploying the demo application, an SNS topic `bedrock-serverless-prompt-chaining-notifications`
will be created and will receive notifications about pipeline failures.
An email address or a [chat bot](https://docs.aws.amazon.com/chatbot/latest/adminguide/setting-up.html)
can be subscribed to the topic to receive notifications when pipeline executions fail.

### Test changes locally

Ensure the CDK code compiles:
```
cdk synth
```

Run the webapp locally:
```
docker compose up --build
```

Run the Lambda functions locally:
```
# Trip planner
python -c 'from agents.trip_planner.hotels_agent import index; print(index.handler({"location": "Paris, France"}, ""))'

python -c 'from agents.trip_planner.restaurants_agent import index; print(index.handler({"location": "Paris, France"}, ""))'

python -c 'from agents.trip_planner.activities_agent import index; print(index.handler({"location": "Paris, France"}, ""))'

# Story writer
python -c 'from agents.story_writer.characters_agent import index; print(index.handler({"story_description": "cowboys in space"}, ""))'

# Movie pitch
python -c 'from agents.movie_pitch.pitch_generator_agent import index; print(index.handler({"movie_description": "cowboys", "temperature": 0.5}, ""))'

python -c 'from agents.movie_pitch.pitch_chooser_agent import index; print(index.handler([{"movie_description": "cowboys", "movie_pitch": "Cowboys in space."}, {"movie_description": "cowboys", "movie_pitch": "Alien cowboys."}, {"movie_description": "cowboys", "movie_pitch": "Time-traveling cowboys."}], ""))'
```
