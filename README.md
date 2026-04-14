# Copilot Image Generation MCP

An MCP server that connects [GitHub Copilot CLI](https://docs.github.com/copilot/concepts/agents/about-copilot-cli) to **Microsoft Copilot's image generation** backend.

Generate images from text prompts and iteratively refine them — all from the terminal. Images are saved locally and organized by session.

## Requirements

- Python 3.10+
- [GitHub Copilot CLI](https://docs.github.com/copilot/concepts/agents/about-copilot-cli)
- [Microsoft 365 Copilot license](https://learn.microsoft.com/en-us/microsoft-365/copilot/) with image generation enabled
- A Chromium-based browser (Edge, Chrome, or Chromium) for first-time sign-in

## Quick Start

1. **Install**

   ```bash
   pip install git+https://github.com/msartem/copilot_image_gen_mcp.git
   ```

   Or install from source:

   ```bash
   git clone https://github.com/msartem/copilot_image_gen_mcp.git
   cd copilot_image_gen_mcp
   pip install .
   ```

2. **Add to your MCP config** (`~/.copilot/mcp-config.json`)

   ```json
   {
     "mcpServers": {
       "copilot-image-gen": {
         "type": "stdio",
         "command": "copilot-image-gen"
       }
     }
   }
   ```

3. **Launch Copilot CLI**

   ```bash
   copilot
   ```

3. **Sign in** (first time only)

   Copilot will automatically call `sign_in` when needed. An Edge
   browser window opens — sign in with your Microsoft 365 account. The
   auth code is captured automatically via Playwright (no manual copy-paste).

4. **Try it out**

   ```
   Generate an image of an elephant in Times Square
   Make the elephant golden
   Change the background to a sunset over mountains
   ```

After first sign-in, auth is silent via cached refresh tokens (~90 day
lifetime, auto-renewing). No browser window on subsequent uses.

## How It Works

1. You ask Copilot CLI to generate or modify an image
2. Copilot routes it to the `generate_image` or `refine_image` tool
3. The MCP server opens a WebSocket to Microsoft Copilot's backend
4. The backend generates the image (DALL-E) and returns it as base64 PNG
5. The image is saved to `~/.copilot-images/` and the file path is returned

Multi-turn refinement works automatically — the server maintains a conversation
so each `refine_image` call builds on the previous image.

```
You → Copilot CLI → image gen MCP → M365 Copilot (Sydney) → DALL-E → PNG saved locally
```

## Tools

| Tool | Description |
|------|-------------|
| `generate_image(prompt, orientation)` | Generate a new image from text. Blocks ~15-30s, returns file path. |
| `refine_image(prompt)` | Modify the last generated image. Same conversation context. |
| `sign_in()` | Sign in to Microsoft 365 (opens browser, one-time). |
| `new_session()` | Start a fresh conversation (discard previous image context). |

### Orientation Options

- `landscape` (default)
- `portrait`
- `square`

## Image Storage

Images are saved to `~/.copilot-images/` organized by session. Each session
groups an initial image with its refinements:

```
~/.copilot-images/
├── 20250115_143022_elephant_in_times_square/
│   ├── session.json                              ← metadata (prompts, timestamps)
│   ├── 001_elephant_in_times_square.png           ← initial image
│   ├── 002_make_the_elephant_golden.png           ← first refinement
│   └── 003_change_the_background_to_a_sunset.png  ← second refinement
└── 20250116_091200_sunset_over_mountains/
    ├── session.json
    └── 001_sunset_over_mountains.png
```

Session directories are created lazily on first image save — no side effects
until you actually generate something.

## Authentication

Authentication uses [Playwright](https://playwright.dev/python/) to
automate browser sign-in via Microsoft Edge. This works identically on
macOS and Windows — no platform-specific code.

### First sign-in

1. Copilot calls `sign_in` (or you trigger it manually)
2. An Edge window opens to the Microsoft sign-in page
3. Sign in with your M365 account (SSO may auto-complete this)
4. The auth code is captured automatically — the browser closes
5. Tokens are cached locally

### Subsequent runs

Cached refresh tokens are used — no browser window, no interaction needed.

### Browser selection

Playwright uses Microsoft Edge by default. To use a different Chromium-based browser:

```bash
export COPILOT_BROWSER=chrome    # or: msedge (default), chromium
```

> **Note**: `chromium` requires `playwright install chromium`. Edge and Chrome
> use your installed browser directly — no extra install needed.

### Manual auth

```bash
python auth.py          # Interactive sign-in
python auth.py logout   # Clear cached tokens
```

### Token storage

| Platform | Cache location |
|----------|---------------|
| macOS / Linux | `~/.copilot-image-gen-mcp/token_cache.json` |
| Windows | `%LOCALAPPDATA%\copilot-image-gen-mcp\token_cache.json` |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COPILOT_IMAGES_DIR` | `~/.copilot-images` | Image output directory |
| `COPILOT_BROWSER` | `msedge` | Browser for sign-in: `msedge`, `chrome`, `chromium` |
| `COPILOT_TENANT` | `common` | Azure AD tenant ID |
| `COPILOT_TIMEOUT` | `90` | Image generation timeout in seconds |
| `COPILOT_VARIANTS` | (built-in) | Feature flag overrides (advanced) |

## Technical Details

See [TECHNICAL.md](TECHNICAL.md) for details on the SignalR WebSocket protocol, authentication flow, image delivery format, and multi-turn refinement architecture.

## Disclaimer

This is an independent community project — **not affiliated with or supported by Microsoft**.

It works by communicating with the same undocumented web APIs that power the
[M365 Copilot web/desktop app](https://m365.cloud.microsoft/chat) image generation.
These APIs may change or break without notice. Use at your own risk.
