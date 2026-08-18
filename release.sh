#!/usr/bin/env bash
set -euo pipefail

# Release script: bumps version in pyproject.toml, commits, tags, pushes,
# and creates a GitHub release which triggers PyPI publishing.
#
# Usage: ./release.sh <version>
# Example: ./release.sh 0.2.0

if [ $# -ne 1 ]; then
    echo "Usage: ./release.sh <version>"
    echo "Example: ./release.sh 0.2.0"
    exit 1
fi

NEW_VERSION="$1"
TAG="v${NEW_VERSION}"

# Validate version format (semver-like)
if ! echo "$NEW_VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo "Error: version must be in format X.Y.Z (e.g., 0.2.0)"
    exit 1
fi

# Ensure working directory is clean
if [ -n "$(git status --porcelain)" ]; then
    echo "Error: working directory is not clean. Commit or stash changes first."
    exit 1
fi

# Ensure we're on main
BRANCH=$(git branch --show-current)
if [ "$BRANCH" != "main" ]; then
    echo "Error: must be on 'main' branch (currently on '$BRANCH')"
    exit 1
fi

# Check tag doesn't already exist
if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "Error: tag $TAG already exists"
    exit 1
fi

# Read current version
CURRENT=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)
echo "Bumping version: $CURRENT → $NEW_VERSION"

# Update pyproject.toml (single source of truth)
sed -i '' "s/^version = \".*\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Commit, tag, push
git add pyproject.toml
git commit -m "Release $TAG"
git tag "$TAG"
git push origin main
git push origin "$TAG"

# Create GitHub release (triggers publish workflow)
gh release create "$TAG" --title "$TAG" --generate-notes

echo ""
echo "✅ Released $TAG"
echo "   PyPI publish workflow triggered — check: gh run list"
