# Building for Native Platforms

This guide walks through building the Lightcurve Explorer with Briefcase for
every supported target. One codebase, six platforms.

---

## Prerequisites

```bash
# Python 3.11+ recommended
pip install briefcase

# Verify
briefcase --version
# Briefcase 0.3.25+
```

Briefcase downloads most platform tools automatically on first use.
The exceptions that need manual setup are noted per platform below.

---

## Development mode — fastest path

Before building for any platform, run in development mode. No build step,
no packaging. Your code changes are reflected immediately.

```bash
cd option-b-beeware

# First run: installs requirements into an isolated venv
briefcase dev

# Subsequent runs (skip requirement install)
briefcase dev --no-run    # just install deps, don't launch
briefcase dev             # launches the app
```

`briefcase dev` runs on your current OS and uses your current Python. This is
the mode for iterating on UI and logic. When it works here, it will work in the
packaged app.

---

## macOS

### What you get
- A `.app` bundle (double-click to run, drag to `/Applications`)
- A `.dmg` disk image (distributable installer)
- Universal binary — runs natively on both Intel and Apple Silicon

### Requirements
- macOS 12+
- Xcode command line tools: `xcode-select --install`
- For App Store or Notarization: paid Apple Developer account ($99/year)

### Commands

```bash
# Create the macOS app scaffold (downloads template + support files ~first time)
briefcase create macOS

# Build the .app
briefcase build macOS

# Run the built .app directly
briefcase run macOS

# Package as a distributable .dmg
briefcase package macOS --adhoc-sign

# The .dmg appears at:
# macOS/Lightcurve Explorer-0.1.0.dmg
```

### For Mac App Store distribution

```bash
# Requires Apple Developer account — set up signing identity in Xcode first
briefcase package macOS
# Then open macOS/Lightcurve\ Explorer.xcarchive in Xcode → Organizer → Distribute
```

---

## Windows

### What you get
- A `.msi` installer (Windows Installer format)
- Installs to `%LOCALAPPDATA%\Programs\Lightcurve Explorer`
- Ships Python runtime — no Python needed on target machine

### Requirements
- Windows 10+
- WiX toolset is bundled — Briefcase installs it automatically

### Commands

```bash
# Create the Windows app scaffold
briefcase create windows

# Build the app
briefcase build windows

# Run the built app
briefcase run windows

# Package as .msi installer
briefcase package windows --adhoc-sign

# The installer appears at:
# windows\Lightcurve Explorer-0.1.0.msi
```

### Notes
- `--adhoc-sign` skips code signing. For distribution, obtain a code signing
  certificate and use `briefcase package windows` without the flag.
- MSI includes a license acceptance dialog if a `LICENSE` file is present.

---

## Linux

### What you get
- An **AppImage** by default — a single executable that runs on any glibc-compatible distro
- Also: `.deb` (Ubuntu/Debian), `.rpm` (Fedora/RHEL), Flatpak, Snap

### Requirements
- 64-bit Linux
- AppImage: no extra tools needed
- .deb: `dpkg-deb` (pre-installed on Ubuntu/Debian)
- .rpm: `rpmbuild` (`sudo dnf install rpm-build`)

```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get install \
    libgirepository1.0-dev libcairo2-dev libpango1.0-dev \
    libwebkit2gtk-4.0-37 gir1.2-webkit2-4.0

# Create scaffold
briefcase create linux

# Build
briefcase build linux

# Run
briefcase run linux

# Package as AppImage (default)
briefcase package linux --adhoc-sign

# Package as .deb
briefcase package linux -p deb --adhoc-sign

# Package as .rpm
briefcase package linux -p rpm --adhoc-sign
```

The AppImage appears at `linux/Lightcurve_Explorer-0.1.0-x86_64.AppImage`.
Make it executable and run: `chmod +x *.AppImage && ./*.AppImage`

---

## iOS

### What you get
- An Xcode project with a full iOS/iPadOS app
- Runs in the iOS Simulator (free)
- Distributes via TestFlight or the App Store (requires Apple Developer account)

### Requirements
- **macOS only** — cannot build iOS apps on Windows or Linux
- Xcode 15+ installed from the Mac App Store
- Apple Developer account for device testing and App Store distribution
- For numpy/scikit-learn: Anaconda is adding iOS binary wheels (2025)

### Commands

```bash
# Create the Xcode project (downloads iOS support runtime ~200MB)
briefcase create iOS

# Run in the iOS Simulator (default: latest iPhone simulator)
briefcase run iOS

# Run on a specific simulator
briefcase run iOS -d "iPhone 15 Pro"
briefcase run iOS -d "iPad Air (5th generation)"

# Run on a physical device (requires device registered in Apple Developer account)
briefcase run iOS -d "Your iPhone Name"

# Build for release
briefcase build iOS

# Package for TestFlight / App Store
briefcase package iOS
# → Opens Xcode Organizer for upload
```

### numpy / scikit-learn on iOS

The Anaconda OSS engineering team is actively building iOS binary wheels for
numpy and scikit-learn (tracked in the BeeWare March 2025 status update).
Until available, the `app.py` in this project falls back to a pure-Python
synthesiser and a σ-threshold anomaly detector when numpy isn't importable —
so the app runs on iOS today, just without the full ML pipeline.

Check availability:
```bash
# Look for iOS wheels in the BeeWare mobile packages index
pip index versions --index-url https://releases.beeware.org/mobile numpy
```

---

## Android

### What you get
- An Android Studio / Gradle project
- `.apk` for direct installation on a device or emulator
- `.aab` (Android App Bundle) for Google Play Store submission

### Requirements
- Android Studio with an emulator configured, OR a physical Android device
- JDK 17 — Briefcase can install this automatically:
  `briefcase upgrade java`
- Google Play Developer account for distribution ($25 one-time fee)

### Commands

```bash
# Create the Gradle project (downloads Android support runtime ~200MB)
briefcase create android

# Run on the default emulator
briefcase run android

# Run on a specific emulator or connected device
briefcase run android -d "Pixel 8 API 35"
briefcase run android -d "samsung-sm-s921b"   # connected physical device

# Build
briefcase build android

# Package as .apk (direct install)
briefcase package android --packaging-format apk

# Package as .aab (Play Store)
briefcase package android
# → sign the .aab and upload via Google Play Console
```

### Signing for the Play Store

```bash
# Generate a signing key (once)
keytool -genkey -v \
    -keystore ~/.android/upload-key-lightcurve.jks \
    -alias lightcurve \
    -keyalg RSA -keysize 2048 \
    -validity 10000

# Sign the .aab
jarsigner -verbose \
    -sigalg SHA256withRSA -digestalg SHA-256 \
    -keystore ~/.android/upload-key-lightcurve.jks \
    "android/gradle/Lightcurve Explorer/app/build/outputs/bundle/release/app-release.aab" \
    lightcurve
```

---

## All platforms at a glance

| Platform | Build command | Package command | Output |
|---|---|---|---|
| macOS | `briefcase build macOS` | `briefcase package macOS --adhoc-sign` | `.dmg` |
| Windows | `briefcase build windows` | `briefcase package windows --adhoc-sign` | `.msi` |
| Linux | `briefcase build linux` | `briefcase package linux --adhoc-sign` | AppImage |
| Linux (.deb) | `briefcase build linux` | `briefcase package linux -p deb` | `.deb` |
| iOS | `briefcase build iOS` | `briefcase package iOS` | Xcode project |
| Android | `briefcase build android` | `briefcase package android` | `.aab` |

All of them start from the same `pyproject.toml` and `src/lightcurve/` directory.

---

## Updating the app after code changes

```bash
# Fastest: push source changes into an existing scaffold
briefcase update
briefcase run

# Or in one step
briefcase run --update

# After adding new dependencies to pyproject.toml requires[]:
briefcase update --update-requirements
briefcase run
```

---

## The Briefcase command lifecycle

```
briefcase new       → scaffold a new project (interactive)
briefcase dev       → run in development mode (no build)
briefcase create    → set up platform-specific scaffold
briefcase build     → compile the app for the target platform
briefcase run       → run the built app
briefcase update    → push code changes into an existing scaffold
briefcase package   → create a distributable installer/archive
briefcase upgrade   → update Briefcase-managed tools (Java, etc.)
```

Each of `create`, `build`, `run`, `update`, `package` accepts a platform
argument: `macOS`, `windows`, `linux`, `iOS`, `android`.
Without a platform argument, Briefcase targets the current OS.

---

## Further reading

- [BeeWare tutorial](https://tutorial.beeware.org)
- [Briefcase docs](https://briefcase.readthedocs.io)
- [Toga widget reference](https://toga.readthedocs.io)
- [Anaconda + BeeWare mobile Python](https://www.anaconda.com/blog/beeware-mobile-python)
- [BeeWare status updates](https://beeware.org/news/buzz/)
