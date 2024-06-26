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

find . -name requirements.txt | xargs -I{} pip install -r {}
```
After this initial setup, you only need to run `source .venv/bin/activate` to use the virtual env for further development.

### Deploy the demo application

Fork this repo to your own GitHub account.
Edit the file `cdk_stacks.py`. Search for `parent_domain` and fill in your own DNS domain, such as `my-domain.com`.
The demo application will be hosted at `https://bedrock-serverless-prompt-chaining.my-domain.com`.
Push this change to your fork repository.

Create a [new GitHub personal access token](https://github.com/settings/tokens/new).
The token only needs the `public_repo` scope.
Copy the generated token, and create a Secrets Manager secret containing the token:
```
aws secretsmanager create-secret \
    --region us-west-2 \
    --name BedrockPromptChainGitHubToken \
    --description "For access to public repos for the Bedrock serverless prompt chain demos" \
    --secret-string "{\"token\": \"<your token>\"}"
```


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
cdk deploy --app 'python3 pipeline_app.py'
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

### Test local changes

Ensure the CDK code compiles:
```
cdk synth
```

Run the webapp locally:
```
docker compose up --build
```

Changes to Step Functions state machines and Lambda functions can be tested in the cloud using `cdk watch`,
after the demo application has been fully deployed to an AWS account (following the instructions above):
```
cdk watch --app 'python3 cdk_stacks.py' \
    PromptChaining-BlogPostDemo \
    PromptChaining-TripPlannerDemo \
    PromptChaining-StoryWriterDemo \
    PromptChaining-MoviePitchDemo \
    PromptChaining-MealPlannerDemo \
    PromptChaining-MostPopularRepoBedrockAgentsDemo \
    PromptChaining-MostPopularRepoLangchainDemo
```

Then in a separate terminal, run test executions in the cloud after making changes to your code.
Edit the files in the `test-inputs` directory to change the test execution inputs.
```
./run-test-execution.sh BlogPost

./run-test-execution.sh TripPlanner

./run-test-execution.sh StoryWriter

./run-test-execution.sh MoviePitch

./run-test-execution.sh MealPlanner

./run-test-execution.sh MostPopularRepoBedrockAgents

./run-test-execution.sh MostPopularRepoLangchain
```
