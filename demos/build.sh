#!/usr/bin/env bash
# Build every automatable demo into docs/assets/demos/.
#   demos/build.sh                 # all of them
#   demos/build.sh web jupyter     # a subset: cli agui hermes web jupyter vscode
# Needs: the LangStage packages (demos/requirements.txt), Playwright's Chromium,
# ffmpeg, VHS + ttyd for the terminal tapes, and git + Node 22 for vscode. CI
# (.github/workflows/demos.yml) installs all of these on ubuntu-latest.
#
# vscode: the LangStage panel, recorded by the langstage-vscode repo's own recorder
# (`npm run record`: the real webview bundle in its Playwright harness, driven through
# the real host logic against the sidecar installed here from PyPI). It checks out
# dkedar7/langstage-vscode at its latest `extension-v*` release tag; override with
# VSCODE_REF=<tag|branch> (e.g. main), or point VSCODE_REPO_DIR at an existing clone.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs/assets/demos

targets=("$@")
[ ${#targets[@]} -eq 0 ] && targets=(cli agui hermes web jupyter vscode)

record_vscode() {
  local repo="${VSCODE_REPO_DIR:-}"
  if [ -z "$repo" ]; then
    local url=https://github.com/dkedar7/langstage-vscode
    local ref="${VSCODE_REF:-}"
    if [ -z "$ref" ]; then
      ref=$(git ls-remote --tags --refs "$url" 'extension-v*' | sed 's#.*refs/tags/##' | sort -V | tail -n1)
      ref="${ref:-main}"
    fi
    repo="$(mktemp -d)/langstage-vscode"
    git clone --quiet --depth 1 --branch "$ref" "$url" "$repo"
    export LANGSTAGE_VSCODE_REF="$ref"
  fi
  echo "langstage-vscode extension at: ${LANGSTAGE_VSCODE_REF:-$repo}"
  (
    cd "$repo/extension"
    npm ci --no-audit --no-fund
    npm run compile
    npx playwright install chromium
    LANGSTAGE_PYTHON="${LANGSTAGE_PYTHON:-python}" npm run record
  )
  cp "$repo/docs/assets/panel-demo.gif" docs/assets/demos/vscode.gif
  cp "$repo/docs/assets/panel-demo.webm" docs/assets/demos/vscode.webm
}

for t in "${targets[@]}"; do
  echo "::group::demo: $t"
  case "$t" in
    cli|agui|hermes) vhs "demos/tapes/$t.tape" ;;
    web|jupyter)     python "demos/scripts/record_$t.py" ;;
    vscode)          record_vscode ;;
    *) echo "unknown demo: $t" >&2; exit 64 ;;
  esac
  echo "::endgroup::"
done

python demos/scripts/versions.py write
ls -la docs/assets/demos
