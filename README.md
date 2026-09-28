# Remotify ChatGPT

A small mobile-first web remote for talking to the OpenAI Responses API from your phone while the service runs on your Windows PC.

## MVP features

- mobile chat UI
- durable multi-turn conversations using the OpenAI Conversations API
- local SQLite copy of conversation titles and messages for fast history loading
- streaming ChatGPT replies
- phone microphone recording and OpenAI speech-to-text transcription
- simple token protection
- designed to sit behind Tailscale Serve so the phone gets HTTPS without exposing the app publicly

## Why this version does not automate the ChatGPT desktop app

UI automation is fragile. This branch talks to the OpenAI API directly, so sending messages, streaming replies, and loading the conversations created by Remotify are much more reliable.

This does **not** import or read your existing ChatGPT consumer-app history or ChatGPT Memory. Remotify starts its own API conversations.

## 1. Download and start on Windows

Requirements: Python 3.10+.

Double-click:

```text
start.bat
```

On the first run it creates `.env` and stops. Edit `.env`:

```env
OPENAI_API_KEY=sk-...
REMOTIFY_TOKEN=use-a-long-random-token
OPENAI_MODEL=gpt-5.6
OPENAI_TRANSCRIPTION_MODEL=gpt-transcribe
HOST=127.0.0.1
PORT=8765
```

Run `start.bat` again.

Desktop test:

```text
http://127.0.0.1:8765
```

Enter your `REMOTIFY_TOKEN` in the web page when asked.

## 2. Recommended phone access: Tailscale Serve

Install Tailscale on the Windows PC and phone, sign into the same tailnet, then leave Remotify bound to `127.0.0.1` and run on the PC:

```powershell
tailscale serve --bg 8765
```

Tailscale prints/provisions a private `https://...ts.net` address. Open that HTTPS address on the phone.

HTTPS matters because iOS/Android browsers normally require a secure context before JavaScript can access the microphone.

To inspect the current Serve configuration:

```powershell
tailscale serve status
```

To remove it later:

```powershell
tailscale serve reset
```

Do not use Tailscale Funnel for this app unless you deliberately want a public internet endpoint.

## API flow

```text
Phone browser
  -> Remotify on PC
      -> OpenAI Conversations API
      -> OpenAI Responses API (streaming text)
      -> OpenAI Transcriptions API (recorded microphone audio)
  <- local SQLite history + streamed reply
```

## Voice input

Tap the microphone button once to start recording and again to stop. The browser uploads the completed recording to the PC, which sends it to `gpt-transcribe`. The transcript is placed into the text box so you can edit it before sending.

## Data

Local history is stored in:

```text
data/remotify.db
```

The corresponding OpenAI conversation ID is also saved locally.

## Security notes

- keep `.env` out of GitHub
- use a long random `REMOTIFY_TOKEN`
- keep `HOST=127.0.0.1` when using Tailscale Serve
- do not directly expose port `8765` to the public internet
- the OpenAI API key stays on the PC; it is never sent to the phone browser

## Current limitations

- this is API chat, not the ChatGPT consumer app
- it cannot read existing ChatGPT.com history or ChatGPT Memory
- no image/file upload yet
- no model picker in the UI yet; change `OPENAI_MODEL` in `.env`
- no message editing/branching yet
