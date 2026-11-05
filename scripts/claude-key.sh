#!/usr/bin/env bash
# Stores the Claude API key the lab's API uses. Pasted here, never shown or stored in code:
# it goes straight into AWS Secrets Manager.
#
#   scripts/claude-key.sh [--staging]
#
# Live (lab.ukdoshi.com) by default; --staging for staging.lab.ukdoshi.com, which has its own key.
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-ukdoshi}" AWS_REGION="${AWS_REGION:-us-east-1}"

if [[ "${1:-}" == --staging ]]; then
  SECRET=ukdoshi-lab-staging/claude-api-key SITE=staging.lab.ukdoshi.com
else
  SECRET=ukdoshi-lab/claude-api-key SITE=lab.ukdoshi.com
fi

# Check the AWS login first, so a key isn't pasted only to fail.
aws sts get-caller-identity >/dev/null || { echo "Log in first: aws sso login --profile $AWS_PROFILE" >&2; exit 1; }

read -r -s -p "Claude API key for $SITE: " key; echo
[[ "$key" == sk-ant-* ]] || { echo "That doesn't look like a Claude API key (they start with sk-ant-)." >&2; exit 1; }

aws secretsmanager put-secret-value --secret-id "$SECRET" --secret-string "$key" >/dev/null
echo "Done. $SITE's API picks up the new key on its next start, or straight away if the old one was rejected."
