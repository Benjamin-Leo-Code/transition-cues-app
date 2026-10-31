# Transition Cues — Home Assistant add-on

A calm picture display for showing **where we are going**, **how we are getting there**, up to **four items to bring along**, and optional **people coming along**.

**Install and update through a custom Home Assistant add-on repository. This is the only supported deployment method.** Requires Home Assistant OS with the Supervisor and an add-on/app store, on an amd64 or aarch64 machine. Newer Home Assistant versions call add-ons “apps”.

## Install

In Home Assistant:

1. Open **Settings → Add-ons → Add-on Store** (or **Settings → Apps → Install app**).
2. Open the three-dot menu → **Repositories**.
3. Add `https://github.com/Benjamin-Leo-Code/transition-cues-app`.
4. Find **Transition Cues**, open it and select **Install**. Home Assistant builds the add-on from this repository; the first installation can take a few minutes and requires internet access.
5. Start it. Enable **Start on boot** and **Watchdog** as desired.
6. Select **Open Web UI**, or open `http://HOME-ASSISTANT-IP:8099` on your tablet and phone.
7. Set and confirm the parent PIN using the on-screen number pad, then add your familiar photos through **Picture library**.

[Add this repository to Home Assistant](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FBenjamin-Leo-Code%2Ftransition-cues-app)

No GitHub token is needed for this public repository. You do not need to copy files onto the server, create folders or install Python.

## Use

Choose a place and transport, optionally select up to four bring-along items and any people joining you, then tap **Show the plan**. The locked display shows the place and transport first, followed by selected people as circular portraits and the bring-along items. People and items are optional; tap any selected picture again to deselect it. Tap five times within four seconds and enter the parent PIN to finish. Reloading restores the locked journey in that browser.

On a phone, open the same server address and choose **Picture library** to upload, name, browse and remove pictures in all four categories. Use **Crop photo** before uploading or beside an existing library picture to frame the image. People have a circular preview; drag, zoom or use the position sliders to centre each face. Use Settings to change the PIN or add a **Back to main screen** link in the parent-screen navigation. The return link can point to a dashboard or another application.

## Moving from another installation

This repository starts at **v1.0.0** with the full current feature set and fresh Git history. Home Assistant treats an add-on from a different repository as a separate installation. Back up the old add-on and keep its data before removing anything; data is not copied automatically. Stop an old installation using port 8099 before starting this one, or choose a different host port. See the setup guide for details.

## Updates and storage

Home Assistant offers an **Update** when the repository advertises a newer add-on version. Updates are installed through Home Assistant; automatic updates are optional. Every GitHub commit is not a release. The add-on is built on your machine during installation and updates; no separate image registry is required.

Photos, library entries and the PIN hash live in **`/data/transition-cues-data` inside the add-on**, separate from the application files. They survive normal updates and restarts. Include Transition Cues in Home Assistant backups. The add-on briefly stops during backups for consistency. No data is stored in `www`, `/share`, GitHub or the browser's photo storage.

The browser stores only the current locked journey snapshot locally. Uploaded photos remain on the Home Assistant machine.

[Full setup, updates, backups and troubleshooting](transition_cues/DOCS.md) · [Changelog](transition_cues/CHANGELOG.md) · [Maintainer guide](DEVELOPMENT.md)

## Screenshots

Screenshots use coloured test placeholders, not family photographs:

- [Tablet selection screen](docs/screenshots/picker.png)
- [Locked display with people and bring-along items](docs/screenshots/locked.png)
- [Phone picture library](docs/screenshots/phone.png)
- [Photo crop editor](docs/screenshots/crop.png)
- [PIN number pad](docs/screenshots/keypad.png)

## Tablet and network

Use a current browser and the tablet's kiosk mode, screen pinning or Guided Access to prevent leaving the browser. The app requests fullscreen when supported; the in-app lock does not control operating-system navigation.

Use the app on your trusted home network. The parent PIN protects editing and leaving a locked journey; it is not an internet-facing account system. Do not forward its port to the internet. The tablet and phone use a direct LAN address; Home Assistant ingress/sidebar embedding is not configured.

The add-on packaging has automated application checks and builds for both supported architectures. Installation, updating and backup/restore still need validation on a real Home Assistant host before relying on it daily.
