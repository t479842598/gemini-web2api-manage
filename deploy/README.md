# Release deployment

The official server target is the Linux x86_64 PyInstaller binary.

1. Download the release tarball from GitHub Releases.
2. Verify the `.sha256` file.
3. Extract the binary under `/opt/gemini-web2api-manage`.
4. Create `/var/lib/gemini-web2api` for persistent config, Cookie, statistics, uploads, and logs.
5. Install `gemini-web2api.service` and start it with systemd.

The source checkout and Docker files remain available for development and compatibility, but are not the official v3.1.0 deployment path.
