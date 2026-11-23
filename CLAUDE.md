# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Personal fork of [Mihon](https://github.com/mihonapp/mihon) (Android manga reader, Kotlin + Jetpack Compose), hosted at
https://github.com/JRRocks/Mihon-edited-. Upstream's fork rules (CONTRIBUTING.md) apply before any public release:
change app name, icon, `applicationId` (`app/build.gradle.kts`), disable/replace the update checker
(`AppUpdateChecker.kt`) and replace `app/src/standard/google-services.json`.

## Commands

Same checks as CI (`.github/workflows/build.yml`):

```bash
./gradlew spotlessCheck               # lint/format check (spotlessApply to fix)
./gradlew testDebugUnitTest           # unit tests
./gradlew verifySqlDelightMigration   # DB migration check
./gradlew assembleDebug               # debug APK (app id suffix .dev)
./gradlew assembleRelease             # release APK (needs keystore.properties or falls back to debug signing)
```

Single test: `./gradlew :<module>:testDebugUnitTest --tests "fully.qualified.TestClass"`.

Build flags (`gradle/build-logic/.../BuildConfig.kt`): `-Pdist=<local|ci|github|...>` controls telemetry
(Firebase/Crashlytics) and the in-app updater; local builds have both off. Build types: `debug`, `release`,
`foss`, `nightly`, `benchmark`. ABI splits produce per-ABI + universal APKs.

## Architecture

Multi-module Gradle build (`settings.gradle.kts`), convention plugins in `gradle/build-logic`, version catalogs
in `gradle/libs.versions.toml` + `gradle/mihon.versions.toml`.

- `app` — UI and app wiring. Legacy code lives under `eu.kanade.tachiyomi` (namespace), newer code under `mihon.*`.
- `domain` — models, interactors, repository interfaces.
- `data` — repository implementations; SQLDelight schema/queries in `data/src/main/sqldelight`
  (schema changes need a migration, checked by `verifySqlDelightMigration`).
- `source-api` / `source-local` — extension source API and the local-files source.
- `presentation-core` / `presentation-widget` — shared Compose components and home-screen widget.
- `core/*`, `core-metadata`, `i18n` (strings, translated via Weblate), `icons/*`, `telemetry`, `baseline-profile`.
- DI uses Metro (`core:metro`, `libs.plugins.metro`); GraphQL via Apollo.
- `tools/colorization-server` — PC server for the app's AI colorization (Python run by uv, `start-server.bat`).
  Default engine `guided` (`guided.py`, after ColorComic's architecture): manga-colorization-v2 + trapped-ball
  segmentation + CLIP region labels + per-region flat colors, on the GPU via ONNX Runtime DirectML. `--director`
  adds a text-only LLM (Qwen3 4B on llama.cpp Vulkan) picking one palette per series from the title the app sends
  in `X-Series-Title`. Other engines: `--engine flux` (FLUX.2 klein, NVIDIA), `--engine mc2` (CPU). DirectML
  crashes if the mc-v2 session is created before the CLIP ones. Models are cached outside the repo, in
  `%USERPROFILE%\.cache\mihon-colorization`.
- `tools/colorization-server/color_sheet.py` (`color-sheet.bat`) — builds a series' color sheet (task 2 of
  `docs/PLAN.md`): AniList/MangaBaka/MangaDex identity, MAIN characters, Japanese volume covers, characters found by
  deepghs head detection + CCIP, parts by See-through, colors measured in OKLab, Danbooru/Fandom control words, D14
  doubt rules; package `colorsheet/`, pure-part tests with `uv run --script tests/run_tests.py`. Trial pages live in
  `essais/` (JSON, SVG swatches and image URLs only, never images).

## Project memory

Read at the start of a session, update at the end (written in French, for the owner):
`docs/PLAN.md` (progress), `docs/JOURNAL.md` (last three entries), `docs/DECISIONS.md` (before any design choice),
`docs/specs/` (how a feature is meant to work), `docs/idees-futur.md` (only on request).

## Public repository

The repository is public: no e-mail address, private path, user name, token or test log in files, commits or
images. Commits use the GitHub `noreply` identity. Copyrighted material (manga pages, covers, character art) never
enters the repository; colorization tests keep only measured colors, source URLs and crop boxes.
Instructions that are specific to the owner's PC (backup mirror) live in `CLAUDE.local.md`, which is not committed.
