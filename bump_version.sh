#!/bin/bash
# Version bump script for Key Light Controller

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Current version
CURRENT_VERSION=$(grep "__version__" keylight_controller.py | cut -d'"' -f2)

echo "Current version: $CURRENT_VERSION"

# Parse arguments
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <major|minor|patch|X.Y.Z>"
    echo "  major: Increment major version (X.0.0)"
    echo "  minor: Increment minor version (0.X.0)"
    echo "  patch: Increment patch version (0.0.X)"
    echo "  X.Y.Z: Set specific version"
    exit 1
fi

# Calculate new version
IFS='.' read -ra VERSION_PARTS <<< "$CURRENT_VERSION"
MAJOR="${VERSION_PARTS[0]}"
MINOR="${VERSION_PARTS[1]}"
PATCH="${VERSION_PARTS[2]}"

case "$1" in
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    minor)
        NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
        ;;
    patch)
        NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
        ;;
    *)
        # Validate version format
        if [[ $1 =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            NEW_VERSION="$1"
        else
            echo -e "${RED}Error: Invalid version format. Use X.Y.Z${NC}"
            exit 1
        fi
        ;;
esac

echo -e "${YELLOW}Bumping version from $CURRENT_VERSION to $NEW_VERSION${NC}"

# Update version in keylight_controller.py
sed -i "s/__version__ = \".*\"/__version__ = \"$NEW_VERSION\"/" keylight_controller.py

# Update CHANGELOG.md
DATE=$(date +%Y-%m-%d)
sed -i "/## \[Unreleased\]/a\\
\\
## [$NEW_VERSION] - $DATE\\
\\
### Added\\
- \\
\\
### Changed\\
- \\
\\
### Fixed\\
- " CHANGELOG.md

echo -e "${GREEN}✅ Version bumped to $NEW_VERSION${NC}"
echo ""
echo "Next steps:"
echo "1. Update CHANGELOG.md with your changes"
echo "2. Commit: git add -A && git commit -m \"Release v$NEW_VERSION\""
echo "3. Tag: git tag -a v$NEW_VERSION -m \"Release version $NEW_VERSION\""
echo "4. Push: git push origin main && git push origin v$NEW_VERSION"
echo ""
echo "GitHub Actions will automatically create the release!"