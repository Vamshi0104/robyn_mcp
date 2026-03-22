#!/usr/bin/env bash
set -euo pipefail

pushd extensions/vscode >/dev/null
npm install
npm run build
npm run package
popd >/dev/null

pushd extensions/jetbrains >/dev/null
./gradlew buildPlugin
popd >/dev/null

echo "Editor artifacts built."
