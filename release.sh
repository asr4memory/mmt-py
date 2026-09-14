#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <version>"
  echo "Example: $0 2026.9.14"
  exit 1
fi

VERSION="$1"

# The app uses date-based versioning: YYYY.M.D, with an optional counter for a
# second release on the same day. Leading zeros are rejected because PEP 440
# removes them, which would make the version in pyproject.toml differ from the
# git tag.
if ! [[ "$VERSION" =~ ^[0-9]{4}\.([1-9]|1[0-2])\.([1-9]|[12][0-9]|3[01])(\.[1-9][0-9]*)?$ ]]; then
  echo "Error: version must be YYYY.M.D or YYYY.M.D.N without leading zeros, for example 2026.9.14 or 2026.9.14.2"
  exit 1
fi

# Check working tree is clean (CHANGELOG.md may have unstaged changes)
if ! git diff --quiet -- ':!CHANGELOG.md' || ! git diff --cached --quiet; then
  echo "Error: working tree is not clean, commit or stash changes first"
  exit 1
fi

echo "Bumping version to $VERSION..."

uv --directory app version "$VERSION"

git add app/pyproject.toml app/uv.lock CHANGELOG.md
git commit -m "Release $VERSION"
git tag "v$VERSION"

echo "Created commit and tag v$VERSION"
echo "Run 'git push && git push --tags' to publish"
