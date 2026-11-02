# ReadySteady — Home Assistant add-on

Transition Cues

A calm picture display for showing **where we are going**, **how we are getting there**, up to **four items to bring along**, and optional **people coming along**.

**Install and update through a custom Home Assistant add-on repository. This is the only supported deployment method.** Requires Home Assistant OS with the Supervisor and an add-on/app store, on an amd64 or aarch64 machine. Newer Home Assistant versions call add-ons “apps”.

## Install

In Home Assistant:

1. Open **Settings → Add-ons → Add-on Store** (or **Settings → Apps → Install app**).
2. Open the three-dot menu → **Repositories**.
3. Add `https://github.com/Benjamin-Leo-Code/transition-cues-app`.
4. Find **ReadySteady**, open it and select **Install**. Home Assistant builds the add-on from this repository; the first installation can take a few minutes and requires internet access.
5. Start it. Enable **Start on boot** and **Watchdog** as desired.
6. Select **Open Web UI**, or open `http://HOME-ASSISTANT-IP:8099` on your tablet and phone.
7. Add your familiar photos through the **Picture library** icon. No PIN setup is needed.

[Add this repository to Home Assistant](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBenjamin-Leo-Code%2Ftransition-cues-app)

No GitHub token is needed for this public repository. You do not need to copy files onto the server, create folders or install Python.

## Use

Choose one to three locations in visit order, then transport. The **Number of stops** segmented control defaults to one. The first row shows up to three most-used pictures; other choices appear below in rows of four on phones. Usage is saved when a plan is shown and is shared across devices; ties keep the library order. After choosing a place, a grouped summary of selected pictures replaces the logo and settings cog. Tap a thumbnail to edit an earlier choice, or **Reset** below the row to clear all choices and start again. On the final page, optionally select people first and up to four bring-along items beneath them. Scroll through the choices and tap **Show the plan** at the bottom when ready. A floating scroll cue appears when there is more below; tap it or swipe to continue. The locked display shows each location as **To**, **Then**, **Then**, alongside transport, followed by selected people as circular portraits and bring-along items in side-by-side groups. The journey works in portrait and landscape. People and items are optional; tap any selected picture again to deselect it. Tap five times within three seconds to finish. Reloading restores the locked journey in that browser.

Open the app on your phone or tablet and tap **Add item** at the end of the relevant Places, Transport, People or Items list. Choose a photo, enter its name and tap **Add to library**. The category is set by the list you opened it from. Use **Crop photo** to adjust the square frame before uploading. The new picture appears in that list without changing your current plan selections.

The gear icon opens **Manage photos**. Its segmented control switches between Place, Transport, Items and People using their glyphs. Browse, crop, rename, transfer, reorder or remove pictures here. The app is standalone.

After **Show the plan**, a splash screen explains how to unlock the display. Choose **Continue to the plan** to lock it, or **Back to choices** to keep editing. Tick **Don’t show this again** before continuing to skip the splash on future journeys in this browser on this device. The preference survives reloads and add-on updates; clearing browser site data resets it. Other devices keep their own preference.

## Home Screen and Dock icons

Use **Share → Add to Home Screen** in Safari on iPhone/iPad, or **File → Add to Dock** on Mac. Other browsers can use the supplied web app manifest and icons; full PWA installation generally needs HTTPS. See [installation and icon refresh instructions](transition_cues/DOCS.md#add-to-your-home-screen-or-dock). The same logo is included for Home Assistant’s app listing.

## Moving from another installation

This repository starts at **v1.0.0** with the full current feature set and fresh Git history. Home Assistant treats an add-on from a different repository as a separate installation. Back up the old add-on and keep its data before removing anything; data is not copied automatically. Stop an old installation using port 8099 before starting this one, or choose a different host port. See the setup guide for details.

## Updates and storage

Home Assistant offers an **Update** when the repository advertises a newer add-on version. Updates are installed through Home Assistant; automatic updates are optional. Every GitHub commit is not a release. The add-on is built on your machine during installation and updates; no separate image registry is required.

Photos, library entries and settings live in **`/data/transition-cues-data` inside the add-on**, separate from the application files. They survive normal updates and restarts. Include ReadySteady in Home Assistant backups. The add-on briefly stops during backups for consistency. No data is stored in `www`, `/share`, GitHub or the browser's photo storage.

The browser stores only the current locked journey snapshot locally. Uploaded photos remain on the Home Assistant machine.

[Full setup, updates, backups and troubleshooting](transition_cues/DOCS.md) · [Changelog](transition_cues/CHANGELOG.md) · [Maintainer guide](DEVELOPMENT.md)

## Screenshots

[Pre-lock splash screen](docs/screenshots/splash.png)

Screenshots use coloured test placeholders, not family photographs:

- [Tablet selection screen](docs/screenshots/picker.png)
- [Frequently used choices on a phone](docs/screenshots/frequent-choices.png)
- [Three-location journey](docs/screenshots/multiple-locations.png)
- [Transport selection with thumbnail summary](docs/screenshots/transport.png)
- [Combined People and Items page](docs/screenshots/companions.png)
- [Bottom-of-page plan button on a phone](docs/screenshots/plan-bottom.png)
- [Add item](docs/screenshots/add-item.png)
- [Manage photos](docs/screenshots/manage-photos.png)
- [Portrait journey display](docs/screenshots/portrait.png)
- [Locked display with people and bring-along items](docs/screenshots/locked.png)
- [Phone picture library](docs/screenshots/phone.png)
- [Photo crop editor](docs/screenshots/crop.png)

## Tablet and network

Use a current browser and the tablet's kiosk mode, screen pinning or Guided Access to prevent leaving the browser. The app requests fullscreen when supported; the in-app lock does not control operating-system navigation.

Use the app on your trusted home network. There is no PIN or account login; devices that can reach the app can view and edit it. Do not forward its port to the internet. The tablet and phone use a direct LAN address; Home Assistant ingress/sidebar embedding is not configured.

The add-on packaging has automated application checks and builds for both supported architectures. Installation, updating and backup/restore still need validation on a real Home Assistant host before relying on it daily.
