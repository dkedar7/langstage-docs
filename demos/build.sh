#!/usr/bin/env bash
# Build every automatable demo into docs/assets/demos/.
#   demos/build.sh                 # all of them
#   demos/build.sh web jupyter     # a subset: cli agui hermes web jupyter
# Needs: the LangStage packages (demos/requirements.txt), Playwright's Chromium,
# ffmpeg, and VHS + ttyd for the terminal tapes. CI (.github/workflows/demos.yml)
# installs all of these on ubuntu-latest.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/assets/demos

targets=("$@")
[ ${#targets[@]} -eq 0 ] && targets=(cli agui hermes web jupyter)

for t in "${targets[@]}"; do
  echo "::group::demo: $t"
  case "$t" in
    cli|agui|hermes) vhs "demos/tapes/$t.tape" ;;
    web|jupyter)     python "demos/scripts/record_$t.py" ;;
    *) echo "unknown demo: $t" >&2; exit 64 ;;
  esac
  echo "::endgroup::"
done

python demos/scripts/versions.py write
ls -la docs/assets/demos
