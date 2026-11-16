# Security Policy

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Email **info@h190k.com** with:

- what you found and its impact,
- steps to reproduce,
- the app version and your OS.

You should get a reply within a few days. Once a fix ships, you'll be credited in the release notes unless you'd rather not be.

## Things to know about RCON

- **RCON is not encrypted.** The password and every command travel in plain text. Only expose the RCON port on trusted networks, or tunnel it (SSH, WireGuard, Tailscale…). Never open it to the internet.
- **Use a long, random `rcon.password`.** Anyone with it has full operator control of your server.
- **Saved passwords** are stored in your user profile. On Windows they are encrypted with your Windows account (DPAPI), so other accounts and other machines can't read them. On macOS and Linux they are stored as plain text in a file only your user can read (`chmod 600`). Untick *Remember password* on shared machines.
