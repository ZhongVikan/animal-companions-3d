#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec godot --headless --rendering-method gl_compatibility \
  --rendering-driver opengl3 --audio-driver Dummy --path "$ROOT" \
  -- --autostart --headless_test
