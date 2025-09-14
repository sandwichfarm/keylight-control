# Release Procedures

This document outlines the release process for Key Light Controller.

## Release Types

- **Major Release (X.0.0)**: Breaking changes, major features
- **Minor Release (0.X.0)**: New features, backwards compatible
- **Patch Release (0.0.X)**: Bug fixes, minor improvements

## Automated Release Process

Releases are automatically created when a new tag is pushed to the repository.

### Quick Release

```bash
# 1. Update version in keylight_controller.py
# 2. Commit changes
git add -A
git commit -m "Release v1.2.3"

# 3. Create and push tag
git tag -a v1.2.3 -m "Release version 1.2.3"
git push origin main
git push origin v1.2.3
```

The GitHub Action will automatically:
1. Build the binary
2. Run tests
3. Create a GitHub release
4. Upload the binary to the release

## Manual Release Process

### Prerequisites

- Python 3.8+ installed
- Git repository with push access
- GitHub personal access token (for creating releases)

### Step 1: Prepare the Release

1. **Update Version Number**
   ```bash
   # Edit keylight_controller.py
   # Update __version__ = "X.Y.Z"
   ```

2. **Update CHANGELOG.md**
   ```bash
   # Document all changes since last release
   # Follow Keep a Changelog format
   ```

3. **Run Tests**
   ```bash
   # Ensure application runs correctly
   python3 keylight_controller.py
   
   # Test binary build
   ./build.sh
   ./dist/keylight-controller
   ```

### Step 2: Build the Binary

```bash
# Clean build
rm -rf build dist build_env

# Run build script
./build.sh

# Verify binary
./dist/keylight-controller --version
ldd dist/keylight-controller  # Should show "not a dynamic executable"
```

### Step 3: Create Git Tag

```bash
# Commit all changes
git add -A
git commit -m "Release v1.2.3"

# Create annotated tag
git tag -a v1.2.3 -m "Release version 1.2.3

- Feature: Added XYZ
- Fix: Resolved ABC
- Improvement: Enhanced DEF"

# Push to repository
git push origin main
git push origin v1.2.3
```

### Step 4: Create GitHub Release

#### Via GitHub CLI
```bash
# Install GitHub CLI if needed
# https://cli.github.com/

# Create release with binary
gh release create v1.2.3 \
  --title "Key Light Controller v1.2.3" \
  --notes "See CHANGELOG.md for details" \
  dist/keylight-controller
```

#### Via Web Interface
1. Go to https://github.com/yourusername/keylight-control-python/releases
2. Click "Draft a new release"
3. Choose the tag `v1.2.3`
4. Set release title: "Key Light Controller v1.2.3"
5. Add release notes from CHANGELOG.md
6. Upload `dist/keylight-controller` binary
7. Publish release

## Release Checklist

Before releasing, ensure:

- [ ] Version number updated in `keylight_controller.py`
- [ ] CHANGELOG.md updated with all changes
- [ ] Application tested on:
  - [ ] Wayland
  - [ ] X11
  - [ ] Different screen resolutions
- [ ] Binary builds successfully
- [ ] Binary runs without Python installed
- [ ] Single instance enforcement works
- [ ] Device discovery works
- [ ] All sliders and controls function properly
- [ ] System tray integration works
- [ ] Keyboard shortcuts work
- [ ] README.md is up to date
- [ ] No debug code or print statements

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Add functionality (backwards compatible)
- **PATCH**: Bug fixes (backwards compatible)

Examples:
- `1.0.0` → `2.0.0`: Changed configuration format
- `1.0.0` → `1.1.0`: Added new feature
- `1.0.0` → `1.0.1`: Fixed bug

## Post-Release

After releasing:

1. **Announce Release**
   - Update project website/wiki if applicable
   - Post to relevant forums/communities

2. **Monitor Issues**
   - Watch for bug reports
   - Respond to user feedback

3. **Plan Next Release**
   - Create milestone for next version
   - Triage incoming issues

## Rollback Procedure

If a release has critical issues:

1. **Delete the problematic release**
   ```bash
   gh release delete v1.2.3 --yes
   ```

2. **Delete the tag**
   ```bash
   git tag -d v1.2.3
   git push origin :refs/tags/v1.2.3
   ```

3. **Fix the issue**
   - Create hotfix branch
   - Fix the problem
   - Test thoroughly

4. **Re-release**
   - Use same version or increment patch
   - Follow normal release process

## Troubleshooting

### Binary Too Large
- Check for unnecessary imports
- Exclude test files from build
- Use UPX compression (already enabled)

### Binary Won't Run
- Verify Python version compatibility
- Check all dependencies are included
- Test on clean system without Python

### GitHub Action Fails
- Check workflow syntax
- Verify secrets are set correctly
- Review action logs for errors

## Security Considerations

- Never include API keys or secrets in binary
- Sign releases with GPG when possible
- Use GitHub's automated security scanning
- Keep dependencies updated

## Support

For release-related issues:
- Check GitHub Actions logs
- Review PyInstaller warnings
- Test on multiple Linux distributions