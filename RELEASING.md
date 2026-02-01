# Release Process

This document describes how to release a new version of Guest Dashboard Guard.

## Steps to Release a New Version

### 1. Update Version Number

Edit [custom_components/guest_dashboard_guard/manifest.json](custom_components/guest_dashboard_guard/manifest.json) and increment the version:

```json
{
  "version": "1.0.1"
}
```

### 2. Commit and Push Changes

```bash
git add custom_components/guest_dashboard_guard/manifest.json
git commit -m "Bump version to 1.0.1"
git push
```

### 3. Create a Git Tag

```bash
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1
```

### 4. Create a GitHub Release

1. Go to https://github.com/scottswaaley/hass-guest-page/releases
2. Click **"Draft a new release"**
3. Click **"Choose a tag"** and select `v1.0.1`
4. Set **Release title**: `v1.0.1`
5. Add **release notes** describing what changed:
   ```markdown
   ## What's Changed
   - Fixed LovelaceData attribute error
   - Improved dashboard detection

   ## Installation
   Update via HACS or download manually from this release.
   ```
6. Click **"Publish release"**

### 5. HACS Will Automatically Detect the New Release

Once published, HACS users will be notified of the update within 24 hours.

## Version Numbering

Follow [Semantic Versioning](https://semver.org/):

- **Major** (1.0.0 → 2.0.0): Breaking changes
- **Minor** (1.0.0 → 1.1.0): New features, backward compatible
- **Patch** (1.0.0 → 1.0.1): Bug fixes, backward compatible

## Quick Release Commands

For a patch release (bug fix):

```bash
# Update version in manifest.json to 1.0.1, then:
git add custom_components/guest_dashboard_guard/manifest.json
git commit -m "Bump version to 1.0.1"
git push
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1
# Then create GitHub release manually
```
