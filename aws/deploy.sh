#!/bin/bash
set -e
cd "$(dirname "$0")"
sam build && sam deploy \
  --profile daybreak \
  --stack-name alfred-bot-2 \
  --resolve-s3 \
  --region us-east-1 \
  --parameter-overrides \
    "SlackBotToken=${SLACK_BOT_TOKEN}" \
    "SlackSigningSecret=${SLACK_SIGNING_SECRET}" \
    "AnthropicApiKey=${ANTHROPIC_API_KEY}" \
    "AlfredAgentId=${ALFRED_AGENT_ID}" \
    "EnvId=${ENV_ID}"
