#!/usr/bin/env bash
set -euo pipefail

project=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destination=${1:-"$project/build/web"}
godot_bin=${GODOT_BIN:-godot}

mkdir -p -- "$destination"
destination=$(cd -- "$destination" && pwd)
if [[ "$destination" == "$project/build/"* ]]; then
    touch -- "$project/build/.gdignore"
fi

"$godot_bin" --headless --path "$project" --import
"$godot_bin" --headless --path "$project" --export-release Web "$destination/index.html"
cp -- "$project/demo/start_web.py" "$destination/"
