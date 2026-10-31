# Changelog

## 1.0.14

- Top-align selection card photos and names so multiline names expand downward without shifting adjacent photos.
- Check mixed-length names in all four picker categories at phone and tablet widths in Chromium and Safari’s engine.

## 1.0.13

- Add saved left/right ordering controls to every library category, reflected in the journey picker.
- Make Show the plan smaller and reveal it after a place is selected; transport is still required to start.
- Enable numbered sections in sequence, with No items to bring to skip the optional Items step before choosing People.

## 1.0.12

- Reorder the upload form: choose a photo first, enter its name second, then choose its category.

## 1.0.11

- Replace library crop/remove text with accessible icon buttons; show deletion in red.
- Add rename and change-category icons and dialogs. Moving a picture preserves its identity, photo and original.
- Keep names, photos and categories in already displayed journeys unchanged.

## 1.0.10

- Use Add a picture and its short-photo guidance as the library page heading, removing duplicate text from the upload box.
- Move Optional beneath the Items to bring along and People headings, keeping selection counts separate.

## 1.0.9

- Add Apple home-screen metadata, a web app manifest, and high-resolution regular and maskable icons using the Transition Cues logo.
- Add Home Assistant app icon and logo artwork.
- Document Home Screen/Dock installation, HTTPS requirements on other browsers, and refreshing existing shortcuts.

## 1.0.8

- Remove Places and Transport totals from the journey picker.
- Move Back to plan to the left, in the logo position on Library and Settings pages.
- Replace the upload category dropdown with labelled Place, Transport, Items and People icons.

## 1.0.7

- Show the journey in landscape, with a Turn your device prompt in portrait. Put People and bring-along items side by side.
- Remove PIN setup, prompts and editing restrictions. Five taps within three seconds return to the plan choices.
- Align destination and transport photos and To:/By: labels; long names expand downward.
- Preserve existing photos and settings while removing obsolete saved PIN hashes.

## 1.0.6

- Simplify the logo and page headings; use accessible icon links for Library and Settings at the top right, with Back to plan on parent pages.
- Show journey photos edge to edge with soft shadows and no borders.
- Size rounded-square bring-along photos to match the circular People portraits.

## 1.0.5

- Use square crops and square photo frames throughout; keep People circular.
- Fill the square by default, allow zooming out and fitting the whole photo, and offer a background colour only when there are gaps or any source transparency.
- Preserve transparency in new originals and bake the chosen background into saved square images.

## 1.0.4

- Move To and By beside the destination and transport names beneath their photos, using separate italic labels vertically centred against each name.

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
