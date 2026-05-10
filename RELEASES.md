# wfbInstaller Release Guide

This guide explains how to create and distribute standalone executables for wfbInstaller.

## For End Users (Quick Start)

### Download and Install

1. Go to [GitHub Releases](https://github.com/joshuahxh/wfbInstaller/releases)
2. Download the executable for your platform:
   - **Windows**: `wfbinstaller-windows.exe`
   - **macOS**: `wfbinstaller-macos`
   - **Linux**: `wfbinstaller-linux`
3. Run it directly - no installation needed!

### Running the Executable

**Windows:**
```cmd
wfbinstaller.exe mystyle.zip
```

**macOS/Linux:**
```bash
./wfbinstaller mystyle.zip
```

Or make it executable once, then use from anywhere:
```bash
chmod +x wfbinstaller
./wfbinstaller mystyle.zip
```

---

## For Developers/Maintainers (Release Process)

### Step 1: Prepare the Release

1. Update version numbers:
   - `setup.py`: Update version
   - `main.py`: Add version string (optional)

2. Update CHANGELOG.md with new features/fixes

3. Commit and push changes:
   ```bash
   git add -A
   git commit -m "Release v1.0.0"
   git push origin main
   ```

### Step 2: Build Executables

You need to build on each platform to ensure compatibility. Here are your options:

#### Option A: Build Locally on Each OS

**On Windows (PowerShell):**
```powershell
cd wfbInstaller
pip install -r requirements-build.txt
pyinstaller --onefile --name wfbinstaller-windows wfbinstaller.spec
cd dist
Rename-Item wfbinstaller-windows.exe wfbinstaller-windows.exe
```

**On macOS:**
```bash
cd wfbInstaller
pip install -r requirements-build.txt
pyinstaller --onefile --name wfbinstaller-macos wfbinstaller.spec
cd dist
mv wfbinstaller-macos wfbinstaller-macos
chmod +x wfbinstaller-macos
```

**On Linux:**
```bash
cd wfbInstaller
pip install -r requirements-build.txt
pyinstaller --onefile --name wfbinstaller-linux wfbinstaller.spec
cd dist
chmod +x wfbinstaller-linux
```

#### Option B: Use GitHub Actions (Automated)

Create `.github/workflows/build-release.yml`:

```yaml
name: Build Releases

on:
  push:
    tags:
      - 'v*'

jobs:
  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          pip install -r requirements-build.txt
          pyinstaller --onefile --name wfbinstaller-windows wfbinstaller.spec
      - uses: actions/upload-artifact@v4
        with:
          name: wfbinstaller-windows
          path: dist/wfbinstaller-windows.exe

  build-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          brew install libmtp
          pip install -r requirements-build.txt
          pyinstaller --onefile --name wfbinstaller-macos wfbinstaller.spec
          chmod +x dist/wfbinstaller-macos
      - uses: actions/upload-artifact@v4
        with:
          name: wfbinstaller-macos
          path: dist/wfbinstaller-macos

  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: |
          sudo apt-get install libmtp9 libusb-1.0-0
          pip install -r requirements-build.txt
          pyinstaller --onefile --name wfbinstaller-linux wfbinstaller.spec
          chmod +x dist/wfbinstaller-linux
      - uses: actions/upload-artifact@v4
        with:
          name: wfbinstaller-linux
          path: dist/wfbinstaller-linux

  create-release:
    needs: [build-windows, build-macos, build-linux]
    runs-on: ubuntu-latest
    if: startsWith(github.ref, 'refs/tags/')
    steps:
      - uses: actions/download-artifact@v4
      - uses: softprops/action-gh-release@v2
        with:
          files: |
            wfbinstaller-windows/wfbinstaller-windows.exe
            wfbinstaller-macos/wfbinstaller-macos
            wfbinstaller-linux/wfbinstaller-linux
```

Then simply create a git tag:
```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions automatically builds and creates the release!

### Step 3: Create GitHub Release

**Using CLI:**
```bash
gh release create v1.0.0 \
  ./dist/wfbinstaller-windows.exe \
  ./dist/wfbinstaller-macos \
  ./dist/wfbinstaller-linux \
  --title "wfbInstaller v1.0.0" \
  --notes "Release notes here"
```

**Using Web UI:**
1. Go to [Releases](https://github.com/joshuahxh/wfbInstaller/releases)
2. Click "Create a new release"
3. Tag: `v1.0.0`
4. Title: `wfbInstaller v1.0.0`
5. Upload files (drag & drop):
   - `wfbinstaller-windows.exe`
   - `wfbinstaller-macos`
   - `wfbinstaller-linux`
6. Add release notes
7. Publish release

### Step 4: Create Archive Packages (Optional)

For easier distribution, create compressed archives:

**Windows (PowerShell):**
```powershell
cd dist
7z a wfbinstaller-windows-v1.0.0.zip wfbinstaller-windows.exe
```

**macOS/Linux (Bash):**
```bash
cd dist
tar -czf wfbinstaller-macos-v1.0.0.tar.gz wfbinstaller-macos
tar -czf wfbinstaller-linux-v1.0.0.tar.gz wfbinstaller-linux
```

Then attach these archives to the GitHub release instead of raw binaries.

### Step 5: Update Documentation

Update the README and any installation guides to point to the new release:

```markdown
## Download

- [Windows](https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-windows.exe)
- [macOS](https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-macos)
- [Linux](https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-linux)
```

---

## Executable Details

### What's Included in Each Executable

The standalone executables contain:
- Python runtime
- All dependencies (requests, libmtp bindings)
- Your application code
- Everything needed to run independently

### File Sizes

- Windows: ~35-50 MB
- macOS: ~35-50 MB
- Linux: ~35-50 MB

### Verification

Users can verify the executables:

**Windows:**
```cmd
wfbinstaller-windows.exe --help
```

**macOS/Linux:**
```bash
./wfbinstaller-macos --help
./wfbinstaller-linux --help
```

---

## Distribution Channels

### GitHub Releases (Recommended)
Best for:
- Direct downloads
- Automatic update detection possible
- Version history
- Release notes

### Website
Add download links to your project website:
```html
<a href="https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-windows.exe">
  Download for Windows
</a>
```

### Package Managers

**Linux - Create AUR package** (Arch Linux):
```bash
# Build with makepkg
makepkg -si
```

**macOS - Homebrew Tap**:
```bash
brew tap joshuahxh/wfbinstaller
brew install wfbinstaller
```

**Windows - Chocolatey**:
```powershell
choco install wfbinstaller
```

### Direct Download Link
```
https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-windows.exe
https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-macos
https://github.com/joshuahxh/wfbInstaller/releases/download/v1.0.0/wfbinstaller-linux
```

---

## Signing & Security

### Code Signing (macOS)
Sign the executable for distribution:
```bash
codesign --deep --force --verify --verbose \
  --sign "Developer ID Application: Your Name (XXXXXXXXXX)" \
  dist/wfbinstaller-macos
```

### Code Signing (Windows)
Use a code signing certificate from a CA like Sectigo or DigiCert.

### Checksums
Generate checksums for verification:

**macOS/Linux:**
```bash
sha256sum wfbinstaller-macos > wfbinstaller-macos.sha256
sha256sum wfbinstaller-linux > wfbinstaller-linux.sha256
```

**Windows (PowerShell):**
```powershell
certutil -hashfile wfbinstaller-windows.exe SHA256
```

Include in release notes:
```
SHA256 Checksums:
wfbinstaller-windows.exe: abc123...
wfbinstaller-macos: def456...
wfbinstaller-linux: ghi789...
```

---

## Troubleshooting

### Executable won't run on macOS
```bash
# Grant execute permission
chmod +x wfbinstaller-macos

# Remove quarantine attribute (if blocked by Gatekeeper)
xattr -d com.apple.quarantine wfbinstaller-macos
```

### Windows Defender/Antivirus warns about .exe
This is normal for PyInstaller binaries. Options:
1. Add to whitelist
2. Sign with code certificate
3. Use Windows App Packaging for distribution

### Linux: "Permission denied"
```bash
chmod +x wfbinstaller-linux
./wfbinstaller-linux
```

---

## Release Checklist

- [ ] Update version numbers
- [ ] Update CHANGELOG.md
- [ ] Test on all three platforms
- [ ] Build executables
- [ ] Create GitHub release
- [ ] Upload executables
- [ ] Add release notes
- [ ] Update README with new download links
- [ ] Announce release (Twitter, email, etc.)

---

## Next Release

For the next release, simply repeat Steps 1-5 with a new version number!
