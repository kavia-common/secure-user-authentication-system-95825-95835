#!/bin/bash
cd /home/kavia/workspace/code-generation/secure-user-authentication-system-95825-95835/backend_auth_api
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

