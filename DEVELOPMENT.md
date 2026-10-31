# Maintaining the Home Assistant add-on

The only supported deployment is installation from this custom repository through Home Assistant. Direct test servers and Docker builds below are development checks, not alternative installation instructions.

## Layout

`repository.yaml` describes the custom store repository. `transition_cues/` is the complete add-on build context: config, Dockerfile, server, web files and store documentation. `tests/` and `.github/workflows/checks.yml` live outside the build context. Screenshots in `docs/screenshots/` contain test placeholders only.

The add-on intentionally has no `image` setting. Home Assistant builds its Dockerfile from this repository on installation/update. No container registry package or private-repository credentials are required for this public source-built distribution. Do not add another add-on config at the root; keep the folder and slug stable, because a different repository/slug identifies a different installation and data directory.

## Checks

With Python 3.12, Node and PyYAML available, from the repository root:

```sh
python3 -m unittest discover -s tests -v
node --check transition_cues/transition-cues-web/app.js
```

For optional browser checks, install Playwright and its Chromium dependency, then run `python3 tests/browser_smoke.py` and `python3 tests/browser_people_crop.py`. The latter checks square frames, fill/fit output pixels, background colours, source transparency, People portraits and immutable locked journey snapshots; add `--browser webkit` to check the same flows with the Safari engine. Run `python3 tests/browser_keypad.py` for button-based PIN entry, and add `--browser webkit` with Playwright WebKit installed to check the Safari engine. Run `python3 tests/browser_splash.py` (or add `--browser webkit`) to check the pre-lock splash and saved browser preference. Real iOS password-manager UI still needs verification on an Apple device. Set `CHROMIUM_PATH` to use a system Chromium. It creates an isolated temporary library, not `/data` or a shared Home Assistant folder.

CI runs the tests and builds the add-on for `linux/amd64` and `linux/arm64` (Home Assistant's `aarch64`). Each job also runs an isolated container check that verifies /data storage and preservation across container replacement. Nothing is pushed to a registry or deployed. A local equivalent is `docker build -t transition-cues-check ./transition_cues` followed by `python3 tests/container_smoke.py --image transition-cues-check`. The smoke check creates and removes only its own temporary containers and volume.

## Release process

1. Make the source and documentation changes, update `transition_cues/CHANGELOG.md` and increase the quoted version in `transition_cues/config.yaml` (for example, `1.0.0` to `1.0.1`).
2. Run tests and build checks. Prefer a pull request and merge after CI passes.
3. Merge/push the versioned change to `main`. Home Assistant uses the default branch when the repository is added without a branch suffix.
4. Home Assistant detects the new version at its next repository refresh, or the user selects Check for updates. The user installs it with Update, or enables automatic updates.
5. Verify a real Home Assistant installation can update without losing photos/PIN/settings; verify backup and restore too.

Do not promise an update for an unversioned source push. No GitHub release/tag is required for this source-built distribution. Do not change the same version's code after release: publish a new version. Build failures, networking or disk space can prevent an install/update even when application tests pass.

## Storage contract

The process listens on container port 8099 and stores its library in `/data/transition-cues-data`. Supervisor always provides the persistent `/data` volume. The add-on does not require shared folders, Home Assistant API permissions, tokens, privileged mode or ingress. Keep the app's data out of the source and image.

Backups are cold to capture consistent JSON/image files. Tests pass an explicit temporary data directory to the server factory. `/data/options.json` belongs to Supervisor and must never be used for the app's picture library. Migration from the previous experimental `/share` path is not implemented; handle any existing data explicitly before changing installations.

## Verification boundary

Automated checks cover server behavior, repository metadata and both image architectures in CI. A normal container build/browser test does not emulate Supervisor; confirm store installation, Update, Watchdog and backup/restore on real Home Assistant OS before marking those flows verified.

## Repository hygiene

This repository starts from a reviewed source snapshot with independent Git history. Do not import commit history from another repository when bringing in changes. Keep uploaded pictures, runtime data and credentials outside Git; review example content and screenshots for personal information before publication.
