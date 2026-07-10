# iPadOS Reader Xcode Repair Notes

This note records the local Xcode/simulator blocker that previously prevented the iPadOS BookMD reader runtime gate, plus the repair path if it reappears.

## Historical Blocker

`xcodebuild -version` works on this machine:

```text
Xcode 26.5
Build version 17F42
```

But `xcodebuild -list -project apps/reader-ios/BookMDReader.xcodeproj` fails before it can inspect the project. The failure is in Xcode's simulator/private framework loading, not in the BookMD reader project:

```text
A required plugin failed to load.
IDESimulatorFoundation
Symbol not found: _$s12DVTDownloads21DownloadableAssetTypeO22developerDocumentationyA2CmFWC
Expected in: /Library/Developer/PrivateFrameworks/DVTDownloads.framework
```

This meant the installed Xcode app and `/Library/Developer/PrivateFrameworks/DVTDownloads.framework` content appeared inconsistent for the active Xcode build.

The blocker was cleared on this machine after simulator platform content was installed and `xcrun simctl` completed its first setup. The installed runtime now includes:

```text
iOS 26.5 (23F77) - com.apple.CoreSimulator.SimRuntime.iOS-26-5
iPad mini (A17 Pro)
```

## Non-Destructive Checks

Run these before changing the Xcode installation:

```bash
xcode-select -p
xcodebuild -version
tmp=$(mktemp -d); printf 'print("swift-ok")\n' > "$tmp/min.swift"; swiftc "$tmp/min.swift" -o "$tmp/min" && "$tmp/min"
xcodebuild -list -project apps/reader-ios/BookMDReader.xcodeproj
xcrun simctl list devices available
```

If `xcodebuild -list` reports the `IDESimulatorFoundation` / `DVTDownloads.framework` symbol error again, the iOS reader cannot be built or tested locally until Xcode simulator support is repaired.

If `xcrun simctl list devices available` hangs or `verify_ios_release.py` reports that `xcrun simctl timed out`, the simulator installation is still unhealthy even if `xcodebuild -version` works. Repair or reinstall the active Xcode installation before running iPad mini simulator acceptance.

## Repair Attempts

Try first-launch setup:

```bash
sudo xcodebuild -license accept
xcodebuild -runFirstLaunch
```

If the same framework symbol error remains, install missing simulator platform content or repair the active Xcode installation, then confirm `xcode-select -p` points to the repaired Xcode:

```bash
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
xcodebuild -version
xcodebuild -downloadPlatform iOS
```

If multiple Xcode apps are installed, ensure the selected app and `/Library/Developer` support files belong to the same Xcode version.

## Resume Automated Verification

After Xcode is healthy, run the release gate without the blocked override:

```bash
cd apps/reader-ios
python3 scripts/verify_ios_release.py
```

The release gate regenerates the project, runs static verification, checks Xcode health, auto-selects an available iPad mini simulator, and runs:

```bash
BOOKMD_REAL_SAMPLE=/Users/wangxuwen/Documents/pdf2md/tmp/real_book_full_clean_toc.bookmd \
  xcodebuild test -project BookMDReader.xcodeproj -scheme BookMDReader -destination 'platform=iOS Simulator,name=iPad mini (A17 Pro)'
```

If the local simulator name differs, pass an explicit destination:

```bash
python3 scripts/verify_ios_release.py --destination 'platform=iOS Simulator,name=<installed iPad mini name>'
```

## Manual Runtime Acceptance

The automated gate now covers the core iPad mini flow. Before using it as a daily reader, still perform the physical/manual checks from `docs/ios_reader_acceptance.md`:

- Import `tmp/real_book_full_clean_toc.bookmd` from Files.
- Confirm shelf, 18-chapter TOC, chapter open, search jump, source-map sheet, PDF page review, and progress restore.
- Rotate portrait and landscape to verify single-column and split-view layouts.
- Search and open several late-book results to confirm the 461-page sample remains responsive.
