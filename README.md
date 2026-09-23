# MonkSynth Themes

Community themes for [MonkSynth](https://github.com/JonET/monksynth). The plugin's theme gallery (right-click → Browse Themes...) lists everything in this repo and installs themes with one click.

## Using a theme without the gallery

Download a folder from [`themes/`](themes/) and copy it into MonkSynth's themes folder, then pick it from the right-click menu:

- macOS: `~/Library/Application Support/MonkSynth/themes/`
- Windows: `%APPDATA%\MonkSynth\themes\`
- Linux: `~/.config/MonkSynth/themes/`

## Submitting a theme

1. Build your theme in the themes folder above so you can try it in the plugin as you go.
2. Fork this repo and add your folder as `themes/<your-theme>/`. The folder name is the theme's id: lowercase letters, digits and dashes.
3. Open a pull request. A check validates the folder. You don't need to touch `index.json` or make a thumbnail or preview image; they're generated after merge.

Only submit art you made or have the right to share.

### What goes in a theme folder

| File | Required | Notes |
|---|---|---|
| `theme.json` | yes | Credits shown in the gallery and in "About Theme..." |
| `background.png` | yes | 360x510 |
| `monk-strip.png` | yes | 5x6 grid of 311x311 frames in 314 px columns, ordered down each column |
| `knob-left.png`, `knob-right.png` | no | Vertical filmstrips, 60 frames |
| `fader-down-large.png`, `fader-down-sm.png`, `fader-right-sm.png` | no | Fader handles |
| `info.png` | no | Info overlay, 253x275 |
| `credits.txt` | no | Longer credits, if you want them |

Missing optional images fall back to blank placeholders. Each file can be up to 8 MB and a whole theme up to 24 MB.

`theme.json` fields are plain one-line strings without double quotes. Only `name` is required:

```json
{
  "name": "My Theme",
  "author": "you",
  "version": "1.0",
  "description": "One or two sentences about the theme.",
  "url": "https://example.com/where-to-find-you"
}
```

Bump `version` when you update a theme; the gallery offers the update to people who have it installed.

## How the gallery reads this repo

`index.json` lists every theme with its metadata, thumbnail, preview and files (size and SHA-256). The plugin fetches it and the files from `raw.githubusercontent.com` on the `main` branch, and only downloads the file names listed above. `scripts/build_index.py` validates the themes and regenerates the index and thumbnails; CI runs it on every pull request (validate only) and on every push to `main` (rebuild and commit).

## Credits and takedowns

Each theme belongs to its author, credited in its `theme.json`. The "Classic Delay Lama" theme is artwork from the original Delay Lama plugin by AudioNerdz (2002), included as a tribute. If you hold rights to anything here and want it removed, open an issue or email the maintainer and it will be taken down.
