import os
import sys
from pathlib import Path

# Optionally source a secrets env file (sops-nix or systemd env)
SECRETS_PATH = os.environ.get(
    "RTUTILS_ENV_FILE", "/run/secrets/request-tracker-utils.env"
)
if os.path.exists(SECRETS_PATH):
    with open(SECRETS_PATH) as f:
        for line in f:
            if line.strip() and not line.strip().startswith("#"):
                k, _, v = line.strip().partition("=")
                os.environ.setdefault(k, v)

# Ensure WORKING_DIR is set for logging/db
if "WORKING_DIR" not in os.environ:
    os.environ["WORKING_DIR"] = "/var/lib/request-tracker-utils"

from django.core.management import execute_from_command_line


def main():
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
