import hashlib
import hmac
import json
import os
import time

import boto3

SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
WORKER_FUNCTION_NAME = os.environ["WORKER_FUNCTION_NAME"]

_lambda = boto3.client("lambda")


def _verify_signature(headers, body):
    timestamp = headers.get("x-slack-request-timestamp", "0")
    if abs(time.time() - int(timestamp)) > 300:
        return False
    sig_base = "v0:{}:{}".format(timestamp, body).encode()
    expected = "v0=" + hmac.new(
        SLACK_SIGNING_SECRET.encode(), sig_base, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, headers.get("x-slack-signature", ""))


def lambda_handler(event, context):
    headers  = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    body_str = event.get("body", "")

    if headers.get("x-slack-retry-num"):
        return {"statusCode": 200, "body": "OK"}

    if not _verify_signature(headers, body_str):
        return {"statusCode": 403, "body": "Forbidden"}

    body = json.loads(body_str)

    if body.get("type") == "url_verification":
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"challenge": body["challenge"]}),
        }

    ev   = body.get("event", {})
    etype = ev.get("type", "")

    # Handle app_mention — ignore bot messages
    if etype == "app_mention" and not ev.get("bot_id"):
        _lambda.invoke(
            FunctionName=WORKER_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(ev).encode(),
        )

    # Handle reactions on messages (👍/👎 for preference tuning)
    elif etype == "reaction_added" and ev.get("reaction") in ("thumbsup", "thumbsdown", "+1", "-1"):
        _lambda.invoke(
            FunctionName=WORKER_FUNCTION_NAME,
            InvocationType="Event",
            Payload=json.dumps(ev).encode(),
        )

    return {"statusCode": 200, "body": "OK"}
