#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 2.5.3"
  exit 1
fi

VERSION="$1"

# Check working tree is clean
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Error: working tree is not clean, commit or stash changes first"
  exit 1
fi

echo "Bumping version to $VERSION..."

uv --directory app version "$VERSION"
npm version "$VERSION" --no-git-tag-version --prefix app

git add app/pyproject.toml app/package.json app/package-lock.json CHANGELOG.md
git commit -m "Release $VERSION"
git tag "v$VERSION"

echo "Created commit and tag v$VERSION"
echo "Run 'git push && git push --tags' to publish"
