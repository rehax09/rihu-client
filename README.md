# Rihu Client Launcher

A personal Minecraft: Java Edition launcher written in Python, made for learning. Version 0.1.0, early development.

## What it does
- Signs in with the official Microsoft login in your web browser (authorization code flow with PKCE, redirecting to http://localhost). The launcher never sees or stores a Microsoft password.
- Downloads Minecraft from Mojang's official servers and launches it for the signed-in account that owns the game. It does not bypass ownership checks or licensing, and it does not distribute any game files.
- Separate profiles, RAM and Java settings, themes, and a mods folder manager.

## Security
- Only a refresh token is kept, inside Windows Credential Manager on the user's own PC.
- Access tokens are given only to the game process and are never written to logs.

## Status
Early development. Some features are not fully tested yet. A Legacy Fabric visual HUD mod (information only, no cheats) is planned for Minecraft 1.8.9.

## Run it
Install Python 3.10 or newer, then double-click `run_launcher.bat`.
