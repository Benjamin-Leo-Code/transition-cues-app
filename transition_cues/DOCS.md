# Set up ReadySteady

## Requirements and installation

Use Home Assistant OS with its Supervisor/add-on store on amd64 (typical x86-64 hardware) or aarch64 (64-bit ARM hardware). Home Assistant Container alone does not provide an add-on store. This app is distributed only as a custom-repository Home Assistant add-on.

Install from the public `Benjamin-Leo-Code/transition-cues-app` repository:

1. In Home Assistant, open **Settings → Add-ons → Add-on Store → ⋮ → Repositories**. Newer versions use **Settings → Apps → Install app**.
2. Add `https://github.com/Benjamin-Leo-Code/transition-cues-app`.
3. Find **ReadySteady**, select **Install**, and wait for the build to finish.
4. Start it and optionally enable **Start on boot** and **Watchdog**.
5. Select **Open Web UI**. On the tablet and phone use `http://HOME-ASSISTANT-IP:8099`.

No folders or files need creating. No Home Assistant or GitHub access token is required. Internet access is needed to fetch the repository and base image when installing/updating; normal picture display and uploads stay on your home network.

The default exposed port is 8099. If it is already used, change the host port in the add-on's Network settings and use that port in tablet/phone addresses. Open Web UI follows the configured port. If hostname discovery fails, use the Home Assistant machine's LAN IP address.

ReadySteady uses **Transition Cues** as its subtitle. Updating from the former Transition Cues name keeps the same Home Assistant installation, photos, settings and browser journey storage. The repository URL, slug and existing data paths stay the same; no reinstall or data migration is needed.

## Add to your Home Screen or Dock

The app includes Apple touch icons and a web app manifest with regular and maskable PNG icons, all using the supplied zoomed green mitten artwork on its ivory background. The app uses a warm neutral page background (#ded8ca). Content includes top safe-area spacing and a small extra inset to avoid native status-bar and scroll-edge effects in installed apps. Native iOS blur effects are controlled by the operating system.

- **iPhone/iPad:** open the app’s address in Safari, choose **Share → Add to Home Screen**, and enable **Open as Web App** if that option appears.
- **Mac:** open the address in Safari, then choose **File → Add to Dock** (macOS Sonoma or later). See [Apple’s instructions](https://support.apple.com/104996).
- **Other devices:** use your browser’s **Install app** or **Add to Home Screen** option. Availability varies. Chromium’s full PWA install experience requires HTTPS, except for localhost/loopback development; a plain `http://homeassistant.local:8099` address may only offer a shortcut. See [browser installation requirements](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable). This update does not configure HTTPS or a reverse proxy for you.

Reload the app after updating before adding it. An existing shortcut or Dock app may retain its old name or icon; rename the shortcut or add it again if necessary. Do not uninstall the Home Assistant add-on to refresh an icon. Photos and shared settings stay on the server. A newly created standalone app can have separate browser storage for the saved journey and splash preference. The Home Assistant server must remain reachable; this update adds install metadata and icons, not offline hosting.

The same mitten artwork appears in the site header. The custom repository also includes Home Assistant’s `icon.png` and `logo.png` assets for its app store/list and detail page, following [Home Assistant’s artwork format](https://contributors.home-assistant.io/apps/guides/presentation/). After updating, refresh the app store/repository and reload Home Assistant if cached artwork remains. Actual Home Screen/Dock artwork and Home Assistant’s interface need checking on your devices; automated checks validate the manifest and served image files.

## Moving from another repository

This is a fresh repository with an initial version of **1.0.0**, containing the current app features. It is not an in-place update or downgrade of an add-on installed from another repository. Home Assistant gives installations from different repository URLs separate identities and private data folders.

Before replacing an existing installation, create a Home Assistant backup including the old add-on. Keep it installed until any photos/settings you want have been migrated and checked; uninstalling removes its private data. Backing up the old add-on does not automatically import its data into this new one. There is no built-in export/import or automatic cross-repository migration at present.

If you are starting with an empty library, stop the old add-on, install and start the new one, and add your familiar photos. Both default to host port 8099, so stop the old one before starting the new one or configure a different host port. You can keep the stopped old installation while verifying the new one.

## First launch and pictures

The gear icon opens **Manage photos**. The segmented category control shows **Places** (location pin), **Transport** (train), **Items** (teddy bear), and **People** (person). It switches the saved pictures below and supports arrow keys and Home/End. Use the chevron at the top left to return to the plan. Existing picture-library URLs also open Manage photos.

No PIN or first-launch setup is required. Existing pictures remain available after updating. Obsolete PIN hashes and saved return addresses are removed automatically; the app runs standalone.

To add a picture, tap **Add item** at the end of the relevant category on the planner. The form opens over your current choices with a photo chooser, name field and **Add to library** button. The category is already chosen, so there is no category picker. Use **Crop photo** to adjust the photo before saving. **Cancel** or Escape closes the form without saving. A successful upload closes the form and adds the picture to that category, retaining the current plan selections. JPEG, PNG and WebP are supported; convert HEIC files first. Photos are resized to at most 1600 pixels before upload. There is no fixed limit on how many items you can select for a journey.

Each library picture has left/right arrows to reorder it within its category. The order is saved on the server and used by every device in the library and journey picker. Edge arrows are disabled; new uploads and transferred pictures join the end of their category. Existing displayed plans keep their current order.

Each library picture also has four icon buttons with accessible names and tooltips: **Crop**, **Rename** (pencil), **Change category** (transfer arrows), and **Remove** (red bin). Remove still asks for confirmation.

Rename opens the current name for editing; save a non-empty name of up to 60 characters. Change category opens Place, Transport, Items and People icons; choose a different category, then **Move picture**. The library switches to the destination category after moving. The item keeps its identity, photo and retained original. Pictures moved to People display as circles; use Crop if the framing needs adjusting. Cancel closes either dialog without changes. Names and pictures in plans already on screen remain unchanged, including after reload.

## Crop photos

All new photos automatically fill a centred square crop, shown in the upload preview. Photo frames are square in the picker, library and locked display. People keep their circular appearance, using a square saved image. Existing photos are shown within square frames; their saved files and locked snapshots are not rewritten automatically.

Tap **Crop photo** on an upload or library picture to adjust it. The frame is always square. Drag or use the position sliders to move the image. Zoom starts at 1 (fill); zoom in for a closer crop, or zoom out to add space around the image. **Fit whole photo** shows the entire photo inside the square. The **Background colour** picker appears only when there are gaps around the image or when the source contains any transparency, including partial transparency. The selected colour fills those gaps and transparent areas in the saved photo. Opaque images that fill the frame have no colour option.

New transparent originals retain their transparency for later edits. Images uploaded in older releases may already have had transparency flattened; upload the original again to recover it. Transparent originals may be resized further to fit the upload limit.

**Use crop** applies the crop. For new photos, finish with **Add to library**; for existing photos, Use crop saves directly to the library. **Cancel** leaves the picture unchanged. **Reset** recentres the editor and resets its zoom. Photos and retained originals are resized to at most 1600 pixels. Reopening the editor starts from the saved original, allowing you to reframe a previous crop. For an older picture with no saved original, its current image becomes the original on the first crop.

Crops keep the existing picture's name and category. Images on an already-locked journey are fixed, so they do not change when a parent crops or removes a photo on another device. The updated image is used for the next journey. Retained originals and older versions use some additional disk space. All editing stays in your browser and on your Home Assistant machine; no external image service is used.

## Plan a journey

The planner has four pages. **Where are we going?** allows multiple locations, and **How are we travelling?** allows multiple transport modes. Select pictures in the order you want them shown. Tapping a selected picture removes it; numbered marks update to reflect the order. There is no stop-count control. A floating circular **Next** arrow appears at the bottom right after at least one choice is selected on the current page. Tap it to advance; selection no longer advances automatically.

**Who is coming along?** is a separate People page. It is optional: choose people or tap **Next** immediately to skip. **What is coming with us?** is the fourth and final page and contains only Items. Items are also optional. There is no four-item cap or selection counter. A circular **Show the plan** button replaces Next on the Items page in the same corner and remains available while you scroll, even if no items are selected.

After the first location is selected, grouped thumbnails replace the logo and settings cog. Locations, Transport, People and Items each wrap within their own category beneath their glyph. Tap a thumbnail to edit that category while retaining other choices, or **Reset** to clear all choices and return to the beginning.

Each category starts with up to three frequently used choices; remaining pictures appear in rows of four on phones, followed by **Add item**. Counts are saved when you show a plan and shared across devices. Reloading a locked plan does not count it again; ties follow library order. A **Scroll for more** cue appears while choices extend below the screen. It disappears at the bottom and is hidden alongside floating actions while dialogs are open.

The locked display preserves the selected order: locations are labelled **To**, then **Then**; transport modes are labelled **By**, then **Then**. Every selected photo is shown. Older saved journeys with one place and transport still restore normally, and new multi-select journeys retain every selection after reload.

The journey appears in both portrait and landscape. On portrait phones, the People and Items groups stack to use the available width. Destination and transport photos stay aligned, with **To:** and **By:** beside their names. Long names expand downward. People and bring-along items appear in groups beside each other below the main photos; larger groups may wrap and the display can scroll.

Tap the display five times within three seconds to return directly to the plan choices. There is no PIN prompt. Fewer taps, or taps spread over longer than three seconds, keep the plan on screen. Refreshing restores the journey, including its selected photos, in the same browser and at the same server address. Different hostnames/ports have separate browser storage.

Use tablet kiosk mode or Guided Access to prevent browser/OS navigation and disable sleep as needed. Fullscreen and keeping the screen awake depend on the browser. Keep the app in its own browser tab; ingress/sidebar embedding is not provided.

After **Show the plan**, a splash screen explains how to unlock the display. The **A quick note** screen puts the tap-to-unlock instructions on their own line. Choose **Continue to the plan** to lock the display. Tick **Don’t show this again** before continuing to skip the splash on future journeys in this browser on this device. The preference survives reloads and add-on updates; clearing browser site data resets it. Other devices keep their own preference.

## Updates

Home Assistant checks the custom repository for a newer version in `transition_cues/config.yaml`. When a release is available, open the add-on page and select **Update**. To refresh manually, use **Check for updates** in the store menu. Automatic updates can be enabled on the add-on page if desired.

Home Assistant downloads the repository and builds the new application on your machine. Allow a few minutes and internet access. No GitHub Container Registry package or credentials are needed for the public repository. Updating briefly interrupts access; uploaded pictures and settings remain in `/data`.

A GitHub push only produces an offered update when it includes a changed add-on version. Read the changelog and keep a backup before updating. Reload the browser after the updated service starts. If the update build fails, inspect the add-on/Supervisor logs and retain the existing installation and data; do not uninstall it as an update troubleshooting step.

## Persistent storage and backups

Inside the add-on:

```text
/app/transition-cues-web/           application files replaced by updates
/data/transition-cues-data/
  library.json                     names, image references, return URL
  images/                          uploaded pictures
```

Home Assistant manages the private `/data` mount. No `/share`, media or Home Assistant configuration folder is mounted. `/data` is a container path, not a directory to create in the File Editor or under `www`.

Include **ReadySteady** in a Home Assistant backup to capture its private data. Backups use `cold` mode: Home Assistant stops the add-on briefly, backs it up and starts it again. Restore the add-on from a backup to recover the photos and settings. Updates and restarts preserve data; uninstalling the add-on removes its private data, so keep a backup before removal. Local browser journey snapshots are separate and are not part of Home Assistant backups.

Removed pictures are hidden from the library but their files are retained, so a locked display on another device can still load them. This uses some additional space; no automatic image cleanup is performed. Keep enough free disk space for your library and backups.

The previous experimental shared-folder setup is no longer supported. Automatic import from an older `/share` installation is not provided.

## Access

All devices that can reach the LAN port can view and edit the picture library and settings. There is no PIN or account login. Keep the app on your trusted home network; do not forward its port to the internet. For access away from home, use your trusted VPN. Home Assistant login does not automatically protect this direct LAN port.

## Troubleshooting

- **Repository cannot be added:** check the URL, repository access and Home Assistant internet connection. No GitHub token is needed for this repository.
- **No update appears:** check for updates in the store; confirm the release increased the add-on version. A source-code edit alone does not trigger an update.
- **Installation/update fails:** inspect build and Supervisor logs, check disk space and internet access, and confirm the machine architecture is supported.
- **Page cannot be reached:** confirm the add-on is running, the configured port is available and both devices can reach your Home Assistant host.
- **Uploads cannot be saved:** check add-on logs and free disk space. Do not create a replacement data folder in `www`.
- **Old page after an update:** reload the browser. Avoid clearing browser site storage while relying on a locked journey, as that clears its saved snapshot.

The add-on needs testing on a real Home Assistant installation, including update and backup/restore, before daily use.
