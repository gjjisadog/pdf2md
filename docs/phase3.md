# Phase 3 Scope

Phase 3 moves the Android reader from a skeleton to a buildable local reading MVP.

## Completed In Phase 3

- Added Gradle wrapper for `apps/reader-android`.
- Adjusted Android build to a Java 11/17 compatible Gradle/AGP setup:
  - Gradle 7.6.4
  - Android Gradle Plugin 7.4.2
  - Kotlin Android plugin 1.8.22
  - compile/target SDK 33
- Verified `./gradlew assembleDebug` with a temporary Android SDK/JDK toolchain.
- Implemented native Android local reading flow:
  - Import `.bookmd` through `Intent.ACTION_OPEN_DOCUMENT`.
  - Show imported books on shelf.
  - Open table of contents.
  - Open reader for chapter Markdown in WebView.
  - Search `search_index.json` and jump to a target block.
  - Preserve reading settings boundary.
  - Query `source_map.json` by block and show source page, bbox, type, and OCR text.
- Renderer supports chapter loading, block jumping, in-chapter search highlighting, image callbacks, and source-map callbacks.

## Verification

```bash
python -m pytest
python -m converter build --source-pdf samples/ocr_output_sample/original.pdf --ocr-output samples/ocr_output_sample --output samples/bookmd_sample/sample.bookmd --translate false
python -m converter validate samples/bookmd_sample/sample.bookmd
cd apps/reader-android
ANDROID_HOME=/path/to/android-sdk ANDROID_SDK_ROOT=/path/to/android-sdk ./gradlew assembleDebug
```

This repository was verified locally with:

```text
BUILD SUCCESSFUL
app/build/outputs/apk/debug/app-debug.apk
```

No Android device was attached during this phase, so `adb install` was not executed.
