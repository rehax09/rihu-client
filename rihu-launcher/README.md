# Rihu Client Launcher (version 0.1.0)

A Windows launcher that signs you in with your Microsoft account, downloads Minecraft Java Edition
from Mojang's official servers, and starts it. Default version: **1.8.9**.

## What works and what does not (read this first)

**Written, but NOT yet tested on a real PC** (it was only syntax-checked, and its file/settings/mods logic
was tested without the window): the window, Microsoft sign-in, the Minecraft download, and launching.
Expect to send me some error messages the first time. That is normal.

| Feature | Status |
|---|---|
| Home page, Play button, version + profile pickers, progress bar, readable errors | Written, untested |
| Microsoft sign-in (official browser flow, token kept in Windows Credential Manager) | Written, untested. **Needs step 3 below.** |
| Install any official release version, repair interrupted downloads | Written, untested |
| Profiles (separate folders for worlds/mods), RAM slider, Java file choice | Written, untested |
| Mods page (add, turn on/off, remove .jar files) | Written, untested |
| Themes (Purple, Dark, Minimal, Neon) and custom accent colour | Written, untested |
| **Legacy Fabric install and the Rihu Client mod** | **Not built yet.** Comes with the mod stage. Until then Minecraft runs as vanilla. |
| Per-profile RAM/Java, config presets, auto-updates | Not built yet |

## Step 1: Install Python (once)
1. Go to https://www.python.org/downloads/ and install Python 3.10 or newer.
2. On the first installer screen, **tick "Add python.exe to PATH"**, then install.

## Step 2: Start the launcher
Double-click **run_launcher.bat**. The first run installs the two libraries it needs, then opens the window.

## Step 3: Microsoft sign-in needs your own Azure app (one-time)
Microsoft only allows Minecraft sign-in for apps that are registered. This is the official route.
Menu names in the Azure website change now and then, so follow the idea if a label differs.

1. Sign in at https://portal.azure.com with a Microsoft account and open **App registrations** (search for it).
2. **New registration**. Name: `Rihu Client Launcher`. Account type: the option that includes
   **personal Microsoft accounts**. Under Redirect URI choose platform **Mobile and desktop applications**
   and enter `http://localhost:53682`.
3. Open the app's **Authentication** page and set **Allow public client flows** to **Yes**. Save.
4. Copy the **Application (client) ID** from the Overview page.
5. In the launcher open **Settings**, paste it into *Azure Application (client) ID*, press
   **Save sign-in settings**.
6. **New Azure apps must be approved by Mojang before they can use the Minecraft API.** Until that is approved,
   sign-in ends with a "not approved" message. The approval form is linked from this page:
   https://minecraft-launcher-lib.readthedocs.io/en/stable/tutorial/microsoft_login.html
   Approval can take days. There is no way around this and the launcher does not try to bypass it.

Your password is typed on Microsoft's own page in your browser. The launcher never sees it.

## Using it
1. Press **Play**. First time: your browser opens for sign-in, then Minecraft downloads, then it starts.
2. **Profiles**: make extra profiles with their own version and worlds.
3. **Settings**: RAM, Java file, theme, accent colour.

## Controls
The launcher is mouse-driven. In the game, Right Shift opens the Rihu GUI once the mod exists (not built yet).

## Making a Windows .exe (optional)
Double-click **build_exe.bat**. When finished, find `dist\RihuClientLauncher.exe`. (Untested.)

## Where files go
`%APPDATA%\RihuClient`: settings.json, minecraft\ (game files), instances\ (profiles), logs\ (launcher.log and game logs).
Your settings file is never silently replaced: a damaged one is renamed to settings.json.broken.

## Troubleshooting
See the **Help** page in the launcher, and send me the end of `logs\launcher.log` or the game log if something fails.
