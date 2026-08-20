#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${VERSION:-3.1.0}"
VERSION="${VERSION#v}"
TARGET="linux-x86_64"
PYTHON="${PYTHON:-python3}"

cd "$ROOT"
"$PYTHON" -m pip install -r requirements.txt "pyinstaller>=6.10,<7"
"$PYTHON" -m PyInstaller --clean --noconfirm deploy/gemini_web2api_manage.spec

mkdir -p "$ROOT/release"
ARTIFACT="$ROOT/release/gemini-web2api-manage-${TARGET}-v${VERSION}"
rm -rf "$ARTIFACT" "$ARTIFACT.tar.gz"
mkdir -p "$ARTIFACT"
cp "dist/gemini-web2api-manage" "$ARTIFACT/"
cp config.example.json "$ARTIFACT/"
cp deploy/gemini-web2api.service "$ARTIFACT/"
cp README.md CHANGELOG.md LICENSE "$ARTIFACT/"
cp -R docs "$ARTIFACT/"
chmod +x "$ARTIFACT/gemini-web2api-manage"

tar -C "$ROOT/release" -czf "$ARTIFACT.tar.gz" "$(basename "$ARTIFACT")"
(
  cd "$ROOT/release"
  sha256sum "$(basename "$ARTIFACT.tar.gz")"
) | tee "$ARTIFACT.sha256"
printf 'Built %s\n' "$ARTIFACT.tar.gz"
