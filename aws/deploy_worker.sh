#!/bin/bash
# Deploy alfred-worker Lambda with full package included.
# Run from the repo root: ./aws/deploy_worker.sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKER_DIR="$SCRIPT_DIR/alfred_worker"
ZIP="$WORKER_DIR/alfred_worker.zip"

echo "Building deployment zip..."
cd "$WORKER_DIR/package"
zip -r ../alfred_worker.zip . -q
cd "$WORKER_DIR"
zip alfred_worker.zip handler.py research_digest_state.py -q

SIZE=$(du -sh "$ZIP" | cut -f1)
echo "Zip size: $SIZE"

echo "Deploying to Lambda..."
aws lambda update-function-code \
  --function-name alfred-worker \
  --zip-file "fileb://$ZIP" \
  --profile daybreak \
  --region us-east-1 \
  --query '[FunctionName, CodeSize]' \
  --output text

rm "$ZIP"
echo "Done."
