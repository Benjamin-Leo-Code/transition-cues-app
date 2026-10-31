# Changelog

## 1.0.3

- Move the lock instructions into a splash screen between Show the plan and the locked journey.
- Add a Continue button, Back to choices, and a Don’t show this again checkbox remembered in the current browser on this device.

## 1.0.2

- Automatically apply a centred 4:3 crop to new place, transport and bring-along photos, with a matching upload preview. People use a square crop for circular portraits.
- Keep the original photo for later adjustments; existing library photos remain unchanged.
- Default the crop editor to 4:3 and offer Square or Original proportions. Remove the Portrait option.

## 1.0.1

- Replace PIN password fields with an on-screen number pad for setup, unlocking and PIN changes, avoiding Safari's password-creation suggestions.
- Show masked digits, with clear/backspace controls, confirmation and physical-keyboard support. Keep PINs in memory without hidden form fields.
- Keep existing PINs, server validation, failed-attempt limits and locked journeys unchanged.
- Add touch-keypad tests in Chromium and Safari's WebKit engine.

## 1.0.0

Initial release from this repository, with fresh Git history.

- Install and update through the Home Assistant custom add-on repository.
- Select a place and transport for a PIN-locked journey display.
- Optionally choose up to four bring-along items and the people joining you, shown as circular portraits.
- Upload, name, crop and remove photos from a phone-friendly library.
- Crop new and existing photos with dragging, zoom, position sliders and shape choices; keep resized originals for re-cropping.
- Preserve locked journey snapshots across refreshes and library edits.
- Store photos, settings and the PIN hash in private `/data/transition-cues-data`, with cold backups and a watchdog.
- Include server, browser and container checks for amd64 and aarch64.
