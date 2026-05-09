[![MacPaw Research](https://pbs.twimg.com/profile_banners/3993798502/1720615716/1500x500)](https://research.macpaw.com)

<p align="center">
  <img src="https://img.shields.io/pypi/v/macapptree" alt="PyPI version">
  <img src="https://img.shields.io/pypi/pyversions/macapptree" alt="Python versions">
  <img src="https://img.shields.io/badge/platform-macOS-lightgrey" alt="Platform">
  <img src="https://img.shields.io/github/license/MacPaw/macapptree" alt="License">
  <a href="https://arxiv.org/abs/2510.16051"><img src="https://img.shields.io/badge/arXiv-2510.16051-b31b1b.svg" alt="arXiv"></a>
</p>

# macapptree

`macapptree` is a Python package that extracts the **accessibility tree** of macOS applications as structured JSON. It can also capture screenshots of application windows with labeled bounding boxes colored by element type — useful for accessibility testing, UI automation, agent training data, and visual debugging.

You can capture a single app, a specific set of apps, or everything currently visible on screen — including the Dock and Menu Bar.

---

## Features

- **Accessibility tree extraction** — retrieve the full AX hierarchy of one or many macOS apps as JSON
- **Single-app or multi-app capture** — target apps by bundle ID or auto-discover all visible apps
- **Window screenshots** — cropped screenshots of individual application windows
- **Segmented visual output** — annotated screenshots with color-coded bounding boxes per element type
- **Menu Bar & Dock support** — include system UI in the captured tree
- **Full-screen annotated output** — overlay all element bounding boxes onto a full-screen capture

---

## Prerequisites

### macOS Accessibility Permissions

`macapptree` uses the macOS Accessibility API (`AXUIElement`). The process running it **must be granted Accessibility access**:

1. Open **System Settings → Privacy & Security → Accessibility**
2. Add your terminal application (e.g. Terminal, iTerm2) or the Python interpreter
3. Toggle it **on**

Without this permission, the library will return empty trees silently.

### Python 3.8+, macOS only

---

## Installation

```bash
pip install macapptree
```

---

## Python API

```python
from macapptree import get_tree, get_tree_screenshot, get_app_bundle

# Resolve bundle ID from app name
bundle = get_app_bundle("TextEdit")  # → "com.apple.TextEdit"

# Accessibility tree only
tree = get_tree(bundle)

# Accessibility tree + screenshots
tree, window_img, segmented_img = get_tree_screenshot(bundle)

# tree          – dict, the full accessibility hierarchy
# window_img    – PIL.Image, cropped screenshot of the app window
# segmented_img – PIL.Image, same screenshot with bounding boxes drawn
```

---

## CLI

### Capture specific apps

```bash
python -m macapptree.main \
  -a com.apple.Safari com.google.Chrome \
  --oa output/dump.json \
  --os output/screenshots \
  --include-menubar \
  --include-dock
```

### Capture all visible apps

```bash
python -m macapptree.main \
  --all-apps \
  --oa output/dump.json \
  --os output/screenshots \
  --include-menubar \
  --include-dock
```

### CLI options

| Flag | Description |
|------|-------------|
| `-a` / `--apps` | One or more app bundle IDs (space-separated) |
| `--all-apps` | Auto-discover all currently visible apps |
| `--oa` | Output path for the accessibility JSON file (**required**) |
| `--os` | Directory for cropped and segmented screenshots |
| `--max-depth` | Maximum depth of the accessibility tree |
| `--include-menubar` | Also capture the top Menu Bar |
| `--include-dock` | Also capture the Dock |

---

## Output

### JSON structure

Each element in the tree has the following shape:

```json
{
    "id": "9d72c04ce9df11c8ab938ead88723de1",
    "name": "Untitled",
    "role": "AXWindow",
    "description": null,
    "role_description": "standard window",
    "value": null,
    "absolute_position": "214.00;119.00",
    "position": "0.00;0.00",
    "size": "586;476",
    "enabled": false,
    "bbox": [0, 0, 586, 476],
    "visible_bbox": [0, 0, 586, 476],
    "children": [...]
}
```

### Screenshot output

| File | Description |
|------|-------------|
| `<AppName>_<window>_cropped.png` | Cropped screenshot of the window |
| `<AppName>_<window>_segmented.png` | Annotated screenshot with bounding boxes |
| `full_screen.png` | Full-screen capture |
| `full_screen_annotated.png` | Full-screen capture with all element overlays |

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## Citation

If you use `macapptree` in your research, please cite:

```bibtex
@article{garkot2025guirilla,
  title={GUIrilla: A Scalable Framework for Automated Desktop UI Exploration},
  author={Garkot, Sofiya and Shamrai, Maksym and Synytsia, Ivan and Hirna, Mariya},
  journal={arXiv preprint arXiv:2510.16051},
  year={2025},
  url={https://arxiv.org/abs/2510.16051}
}
```

---

## MacPaw Research

Built by the [MacPaw Research](https://research.macpaw.com) team.
