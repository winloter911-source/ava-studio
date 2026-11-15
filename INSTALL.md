# Install AVA Studio

These instructions are for the installation agent; members need only the repository link.

1. Read AGENTS.md, inspect the installer and check system compatibility. Install Python 3.11+ if missing, using an official source and the available permissions. Configure Codex CLI and request the user's own sign-in when required.
2. Download/clone this repository into a temporary or separate bootstrap folder. It contains the downloader, not the installed app.
3. Run `bash install.sh`. The destination defaults to `~/AVA Studio`; use `--directory` for another new folder. A currently empty folder still counts as existing and is not overwritten.
4. The downloader queries the latest published release, accepts exactly one asset named AVA-Studio.zip or AVA-Studio-2026-11-15.zip, verifies its pinned SHA-256 and internal file manifest, extracts the application, and runs Setup.command.
5. Follow INSTALL-AGENT.md inside the application for remaining dependencies, verification and opening the UI. A failed setup can be resumed from that installed folder; do not delete user data.
6. Do not generate paid content during setup. Add service keys through Settings, never the chat. Missing voice/profile configuration is not an invitation to reuse another person's credentials.

## Release maintenance (owner)

Before publishing, attach the complete ZIP and its .sha256 file to the release. This installer is pinned to the archive hash in install.py. When rebuilding the archive, update that hash in the repository and publish the matching asset. Do not point this installer at a newer archive without updating its pin. Never upload secrets or the configured working installation.

If the release is still a draft, public installation will stop with a clear error. Publish the intended release and make it the latest after the bootstrap files and assets are ready.

Diagnostic command: `python3 install.py --verify-only --package /path/to/AVA-Studio.zip`. This checks archive integrity without installation, dependency downloads or paid calls.
