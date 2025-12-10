#!/usr/bin/env bash
set -euo pipefail

echo "=== Unit FragmentPath ==="
systemctl show -p FragmentPath --value request-tracker-utils || true

echo "=== Resolved FragmentPath ==="
vp=$(systemctl show -p FragmentPath --value request-tracker-utils || true)
if [ -n "$vp" ]; then readlink -f "$vp" || true; fi

echo "=== ExecStart ==="
systemctl show -p ExecStart --value request-tracker-utils || true

echo "=== Environment ==="
systemctl show -p Environment --value request-tracker-utils || true

echo "=== ExecStartPre ==="
systemctl show -p ExecStartPre --value request-tracker-utils || true
pre=$(systemctl show -p ExecStartPre --value request-tracker-utils || true)

# extract first token as path (strip quotes)
pre_path=$(echo "$pre" | awk '{print $1}' | sed "s/'//g")
echo "pre-start path: $pre_path"

if [ -n "$pre_path" ] && [ -f "$pre_path" ]; then
  echo "=== Pre-start script head ==="
  sed -n '1,240p' "$pre_path" || true
else
  echo "pre-start script not found at $pre_path"
fi

echo "=== Journal last 200 lines ==="
journalctl -u request-tracker-utils -n 200 --no-pager || true

echo "=== Locate package store for request-tracker-utils ==="
ls -d /nix/store/*request-tracker-utils* 2>/dev/null || true
pkg=$(ls -d /nix/store/*request-tracker-utils* 2>/dev/null | head -n1 || true)
echo "pkg: $pkg"

if [ -n "$pkg" ]; then
  echo "=== pkg bin ==="
  ls -la "$pkg/bin" || true
  echo "=== site-packages listing ==="
  ls -la "$pkg/lib"/*/site-packages 2>/dev/null || true
  echo "=== Check for asgiref inside package site-packages ==="
  if ls -d "$pkg"/lib/*/site-packages/asgiref* 2>/dev/null; then
    echo "asgiref exists in package site-packages"
  else
    echo "asgiref NOT in package site-packages"
  fi

  if [ -x "$pkg/bin/rtutils-python" ]; then
    echo "=== Running rtutils-python import test ==="
    "$pkg/bin/rtutils-python" - <<'PYCODE'
import sys
try:
    import asgiref
    print('asgiref:', asgiref.__file__)
except Exception as e:
    print('asgiref import failed:', e)
try:
    import django
    print('django:', django.__file__)
except Exception as e:
    print('django import failed:', e)
print('sys.path:')
for p in sys.path[:20]:
    print('  ', p)
PYCODE
  else
    echo "rtutils-python wrapper not found or not executable: $pkg/bin/rtutils-python"
  fi
fi

if [ -n "$pre_path" ] && [ -f "$pre_path" ]; then
  echo "=== Tracing pre-start script ==="
  bash -x "$pre_path" || true
fi

echo "=== Done ==="
