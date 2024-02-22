#!/bin/bash

set -e

# TripPlanner, MoviePitch, etc
DEMO_NAME=$1

AWS_ACCOUNT_ID=`aws sts get-caller-identity --query Account --output text`

EXECUTION_NAME=local-test-`uuidgen`

echo "Starting execution $EXECUTION_NAME for state machine PromptChainDemo-$DEMO_NAME"
aws stepfunctions start-execution \
    --region us-west-2 \
    --name $EXECUTION_NAME \
    --state-machine-arn arn:aws:states:us-west-2:$AWS_ACCOUNT_ID:stateMachine:PromptChainDemo-$DEMO_NAME \
    --input file://test-inputs/$DEMO_NAME.json

echo -e "\nWatch the execution at:"
echo "https://us-west-2.console.aws.amazon.com/states/home?region=us-west-2#/v2/executions/details/arn:aws:states:us-west-2:$AWS_ACCOUNT_ID:execution:PromptChainDemo-$DEMO_NAME:$EXECUTION_NAME"

echo -ne "\nWaiting for execution to complete..."
while true; do
    STATUS=`aws stepfunctions describe-execution --region us-west-2 --query status --output text --execution-arn arn:aws:states:us-west-2:$AWS_ACCOUNT_ID:execution:PromptChainDemo-$DEMO_NAME:$EXECUTION_NAME`
    if [ "$STATUS" = "SUCCEEDED" ] || [ "$STATUS" = "FAILED" ] || [ "$STATUS" = "TIMED_OUT" ] || [ "$STATUS" = "ABORTED" ]; then
        echo -e "\n\nExecution completed. Status is $STATUS"
        if [ "$STATUS" = "SUCCEEDED" ]; then
          echo "Output:"
          aws stepfunctions describe-execution \
            --execution-arn arn:aws:states:us-west-2:$AWS_ACCOUNT_ID:execution:PromptChainDemo-$DEMO_NAME:$EXECUTION_NAME \
            --query output \
            --output text | jq
          exit 0
        fi
        exit 1
    fi
    sleep 2
    echo -n '.'
done