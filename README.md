# Remotify

Remotify is a tiny mobile-friendly remote controller for a desktop application window.

The first target is the Codex desktop app on Windows:

- capture the Codex window screenshot
- show it in a mobile Web UI
- send text to the Codex input box by clipboard paste + Enter
- click on the screenshot and map the click back to the real desktop window
- focus the target window
- protect the local control API with a simple token

This is intentionally a small MVP, because UI automation is already enough chaos without inviting a full circus.

## Status

MVP scaffold.

## Requirements

- Windows 10/11
- Python 3.10+
- A visible Codex desktop window
- Same LAN, Tailscale, ZeroTier, or another private tunnel for phone access

Do **not** expose this service directly to the public internet. It can control your mouse, keyboard, and clipboard. Treat it like a tiny remote-control goblin with house keys.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configure

Copy the example env file:

```bash
copy .env.example .env
```

Edit `.env`:

```env
REMOTIFY_TOKEN=change-me
TARGET_WINDOW_TITLE=Codex
HOST=127.0.0.1
PORT=8765
```

For phone access, prefer Tailscale and bind to `0.0.0.0` only on a private network:

```env
HOST=0.0.0.0
```

## Run

```bash
python -m app.main
```

Open on the desktop first:

```text
http://127.0.0.1:8765/?token=change-me
```

Then open from your phone using the computer's LAN/Tailscale IP:

```text
http://YOUR_PC_IP:8765/?token=change-me
```

## Usage

1. Keep the Codex desktop window visible.
2. Open Remotify from your phone.
3. Tap **Refresh** to capture the window.
4. Type a message and press **Send**.
5. Tap directly on the screenshot to click the real Codex window.

## API

### `GET /api/health`

Returns service status.

### `GET /api/screenshot?token=...`

Returns the current target window screenshot as PNG.

### `POST /api/send?token=...`

```json
{
  "text": "Continue the previous task.",
  "press_enter": true
}
```

### `POST /api/click?token=...`

Coordinates are relative to the image shown in the browser.

```json
{
  "x": 120,
  "y": 500,
  "display_width": 390,
  "display_height": 800
}
```

### `POST /api/focus?token=...`

Focuses the target window.

## Limitations

- Windows-focused MVP.
- Requires the target window to be visible and not minimized.
- Does not OCR or understand the Codex UI yet.
- Clipboard is temporarily overwritten when sending text.
- Some apps/windows may require running the terminal as administrator if they are elevated.

## Roadmap

- WebSocket auto-refresh
- OCR output extraction
- multiple target windows
- configurable hotkeys
- approve button helper
- session presets
- Tailscale setup guide
