#!/usr/bin/env bash
set -euo pipefail

# local_prestart.sh
# Helper to simulate the systemd preStart for the request-tracker-utils service
# - Creates a working directory (default: ./.local-test-workdir)
# - Generates a safely quoted secret.env with DJANGO_SECRET_KEY if missing
# - Exports WORKING_DIR so Django logging writes into a writable location
# - Runs migrate and collectstatic using the packaged rtutils-manage if available
# - Captures logs into the working directory

usage() {
  cat <<'USAGE'
Usage: local_prestart.sh [--workdir DIR] [--manage PATH]

Options:
  --workdir DIR   Directory to use as WORKING_DIR (default: ./.local-test-workdir)
  --manage PATH   Path to manage helper to use (default: ./result/bin/rtutils-manage if present)
  -h, --help      Show this help
USAGE
}

WORKING_DIR="$PWD/.local-test-workdir"
MANAGE_BIN=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --workdir)
      WORKING_DIR="$2"; shift 2;;
    --manage)
      MANAGE_BIN="$2"; shift 2;;
    -h|--help)
      usage; exit 0;;
    --)
      shift; break;;
    *)
      echo "Unknown arg: $1" >&2; usage; exit 2;;
  esac
done

mkdir -p "$WORKING_DIR" "$WORKING_DIR/logs" "$WORKING_DIR/static" "$WORKING_DIR/media"

SECRET_ENV="$WORKING_DIR/secret.env"
if [ -f "$SECRET_ENV" ]; then
  echo "Using existing $SECRET_ENV"
else
  echo "Generating $SECRET_ENV"
  # Use Python to generate a secure key and shlex.quote it to make the env file safe to `.` (source)
  python - <<'PY' > "$SECRET_ENV"
import secrets, string, shlex, sys
alphabet = string.ascii_letters + string.digits + "!@#$%^&*(-_=+)"
key = ''.join(secrets.choice(alphabet) for _ in range(50))
sys.stdout.write('DJANGO_SECRET_KEY=' + shlex.quote(key) + '\n')
PY
  chmod 600 "$SECRET_ENV"
  echo "Wrote $SECRET_ENV"
fi

# Export WORKING_DIR so Django logging writes to a writable location
export WORKING_DIR

# Choose manage command
if [ -n "$MANAGE_BIN" ] && [ -x "$MANAGE_BIN" ]; then
  MANAGE_CMD="$MANAGE_BIN"
elif [ -x ./result/bin/rtutils-manage ]; then
  MANAGE_CMD="./result/bin/rtutils-manage"
elif command -v rtutils-manage >/dev/null 2>&1; then
  MANAGE_CMD="rtutils-manage"
elif command -v uv >/dev/null 2>&1; then
  MANAGE_CMD="uv run python manage.py"
elif command -v python >/dev/null 2>&1; then
  MANAGE_CMD="python manage.py"
else
  echo "No manage runner found (rtutils-manage, uv, or python)." >&2
  exit 3
fi

echo "Using manage command: $MANAGE_CMD"

# Run migrate and collectstatic capturing logs
MIGRATE_OUT="$WORKING_DIR/migrate.out"
COLLECT_OUT="$WORKING_DIR/collect.out"

echo "Running migrate... (logs -> $MIGRATE_OUT)"
bash -lc "set -a; . '$SECRET_ENV'; export WORKING_DIR='$WORKING_DIR'; $MANAGE_CMD migrate --noinput" > "$MIGRATE_OUT" 2>&1 || echo "migrate failed (exit $?) -- see $MIGRATE_OUT"

echo "Running collectstatic... (logs -> $COLLECT_OUT)"
bash -lc "set -a; . '$SECRET_ENV'; export WORKING_DIR='$WORKING_DIR'; $MANAGE_CMD collectstatic --noinput --clear" > "$COLLECT_OUT" 2>&1 || echo "collectstatic failed (exit $?) -- see $COLLECT_OUT"

echo "--- migrate.out (tail 200) ---"
tail -n 200 "$MIGRATE_OUT" || true

echo "--- collect.out (tail 200) ---"
tail -n 200 "$COLLECT_OUT" || true

echo "Workdir listing:"
ls -la "$WORKING_DIR" || true

echo "Done. Inspect $MIGRATE_OUT and $COLLECT_OUT for details."
