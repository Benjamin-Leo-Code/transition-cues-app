# Set up Transition Cues

## Requirements and installation

Use Home Assistant OS with its Supervisor/add-on store on amd64 (typical x86-64 hardware) or aarch64 (64-bit ARM hardware). Home Assistant Container alone does not provide an add-on store. This app is distributed only as a custom-repository Home Assistant add-on.

Install from the public `Benjamin-Leo-Code/transition-cues-app` repository:

1. In Home Assistant, open **Settings → Add-ons → Add-on Store → ⋮ → Repositories**. Newer versions use **Settings → Apps → Install app**.
2. Add `https://github.com/Benjamin-Leo-Code/transition-cues-app`.
3. Find **Transition Cues**, select **Install**, and wait for the build to finish.
4. Start it and optionally enable **Start on boot** and **Watchdog**.
5. Select **Open Web UI**. On the tablet and phone use `http://HOME-ASSISTANT-IP:8099`.

No folders or files need creating. No Home Assistant or GitHub access token is required. Internet access is needed to fetch the repository and base image when installing/updating; normal picture display and uploads stay on your home network.

The default exposed port is 8099. If it is already used, change the host port in the add-on's Network settings and use that port in tablet/phone addresses. Open Web UI follows the configured port. If hostname discovery fails, use the Home Assistant machine's LAN IP address.

## Moving from another repository

This is a fresh repository with an initial version of **1.0.0**, containing the current app features. It is not an in-place update or downgrade of an add-on installed from another repository. Home Assistant gives installations from different repository URLs separate identities and private data folders.

Before replacing an existing installation, create a Home Assistant backup including the old add-on. Keep it installed until any photos/settings you want have been migrated and checked; uninstalling removes its private data. Backing up the old add-on does not automatically import its data into this new one. There is no built-in export/import or automatic cross-repository migration at present.

If you are starting with an empty library, stop the old add-on, install and start the new one, and set a new parent PIN. Both default to host port 8099, so stop the old one before starting the new one or configure a different host port. You can keep the stopped old installation while verifying the new one.

## First launch and pictures

Set a shared parent PIN of 4–8 digits on first launch using the on-screen number pad. Tap **Next**, enter the same digits to confirm, then save. There is no default PIN. Use this PIN on your phone when opening the library or settings.

The PIN controls use buttons and masked dots instead of password fields, so Safari has no editable PIN field to offer a generated password for or open its keyboard against. Use **Clear** to start over or **⌫** to delete the last digit. A physical keyboard also works: type numbers, use Backspace to delete a digit, Delete to clear, and Enter on the selected PIN field to continue. PINs can start with zero and may contain up to eight digits.

To change the PIN in Settings, tap each PIN field (Current PIN, New PIN and Confirm new PIN), then use the same number pad. **Next PIN field** moves to the next entry. Changing this entry interface does not change your existing PIN.

In **Picture library**, select **A place**, **A way to travel**, **An item to bring along**, or **A person**, enter a name, choose a photo and add it. Use the Places, Transport, Items and People tabs to browse and remove pictures. JPEG, PNG and WebP are supported; convert HEIC files first. Photos are resized to at most 1600 pixels before upload. The four-item limit applies to a journey; the item library may contain more than four pictures.

## Crop photos

New place, transport and bring-along photos automatically receive a centred 4:3 crop, shown in the upload preview. Tap **Crop photo** to adjust it, or use **Crop photo** on an existing library picture. Drag the preview, adjust Zoom and the horizontal/vertical sliders, and choose Landscape (4:3), Square or Original proportions. Existing library photos stay unchanged until you save a crop. People use a square crop with a circular preview so you can centre the face. The circular appearance is used in the picker, library and locked display; the underlying image is a normal square JPEG.

**Use crop** applies the crop. For new photos, finish with **Add to library**; for existing photos, Use crop saves directly to the library. **Cancel** leaves the picture unchanged. **Reset** recentres the editor and resets its zoom. Photos and retained originals are resized to at most 1600 pixels. Reopening the editor starts from the saved original, allowing you to reframe a previous crop. For an older picture with no saved original, its current image becomes the original on the first crop.

Crops keep the existing picture's name and category. Images on an already-locked journey are fixed, so they do not change when a parent crops or removes a photo on another device. The updated image is used for the next journey. Retained originals and older versions use some additional disk space. All editing stays in your browser and on your Home Assistant machine; no external image service is used.

## Plan a journey

Choose one place and one transport picture. Optionally select zero to four items; tap a selected item to deselect it. Select any people coming along, or leave People empty. People has no four-person cap. Tap **Show the plan**.

The place and transport appear first, then circular photos and names of selected people, followed by bring-along items. With larger groups or a small screen, the locked display can scroll to keep every person and item accessible. Five taps within four seconds reveal the parent PIN prompt. Cancelling or entering the wrong PIN keeps the journey locked. Refreshing restores it, including the selected items and people, in the same browser and at the same server address. Different hostnames/ports have separate browser storage.

Use tablet kiosk mode or Guided Access to prevent browser/OS navigation and disable sleep as needed. Fullscreen and keeping the screen awake depend on the browser. Keep the app in its own browser tab; ingress/sidebar embedding is not provided.

## Return link

In Settings, enter the full main-screen address under **Back to main screen**. The return link appears in the navigation on parent screens after unlocking; there is no footer. When ready, add a link from the main tablet app to `http://HOME-ASSISTANT-IP:8099`. The return link does not modify the linked application.

## Updates

Home Assistant checks the custom repository for a newer version in `transition_cues/config.yaml`. When a release is available, open the add-on page and select **Update**. To refresh manually, use **Check for updates** in the store menu. Automatic updates can be enabled on the add-on page if desired.

Home Assistant downloads the repository and builds the new application on your machine. Allow a few minutes and internet access. No GitHub Container Registry package or credentials are needed for the public repository. Updating briefly interrupts access; uploaded pictures and settings remain in `/data`.

A GitHub push only produces an offered update when it includes a changed add-on version. Read the changelog and keep a backup before updating. Reload the browser after the updated service starts. If the update build fails, inspect the add-on/Supervisor logs and retain the existing installation and data; do not uninstall it as an update troubleshooting step.

## Persistent storage and backups

Inside the add-on:

```text
/app/transition-cues-web/           application files replaced by updates
/data/transition-cues-data/
  library.json                     names, image references, return URL, PIN hash
  images/                          uploaded pictures
```

Home Assistant manages the private `/data` mount. No `/share`, media or Home Assistant configuration folder is mounted. `/data` is a container path, not a directory to create in the File Editor or under `www`.

Include **Transition Cues** in a Home Assistant backup to capture its private data. Backups use `cold` mode: Home Assistant stops the add-on briefly, backs it up and starts it again. Restore the add-on from a backup to recover the photos and settings. Updates and restarts preserve data; uninstalling the add-on removes its private data, so keep a backup before removal. Local browser journey snapshots are separate and are not part of Home Assistant backups.

Removed pictures are hidden from the library but their files are retained, so a locked display on another device can still load them. This uses some additional space; no automatic image cleanup is performed. Keep enough free disk space for your library and backups.

The previous experimental shared-folder setup is no longer supported. Automatic import from an older `/share` installation is not provided.

## PIN and access

Change the PIN in Settings using the current PIN. Other devices need the new PIN after a change. Parent sessions expire after 12 hours or a restart; a locked journey always requires PIN entry to finish. Five failed attempts in a minute temporarily block further PIN attempts from that IP address.

If the PIN is forgotten, preserve a backup and seek administrator recovery rather than uninstalling. A maintenance-only `reset_pin.py` utility is included in the add-on image for an administrator with host/container access. Stop the running service and back up its data before using it against the library; it prompts for a new PIN without displaying it. This is not an extra deployment method or a standard Home Assistant Terminal command.

All devices that can reach the LAN port can view the picture library/images; editing requires the PIN. Keep it on your trusted LAN. For access away from home, use your trusted VPN. Home Assistant login does not automatically protect this direct LAN port.

## Troubleshooting

- **Repository cannot be added:** check the URL, repository access and Home Assistant internet connection. No GitHub token is needed for this repository.
- **No update appears:** check for updates in the store; confirm the release increased the add-on version. A source-code edit alone does not trigger an update.
- **Installation/update fails:** inspect build and Supervisor logs, check disk space and internet access, and confirm the machine architecture is supported.
- **Page cannot be reached:** confirm the add-on is running, the configured port is available and both devices can reach your Home Assistant host.
- **Uploads cannot be saved:** check add-on logs and free disk space. Do not create a replacement data folder in `www`.
- **Old page after an update:** reload the browser. Avoid clearing browser site storage while relying on a locked journey, as that clears its saved snapshot.

The add-on needs testing on a real Home Assistant installation, including update and backup/restore, before daily use.
