# macapptree

`macapptree` is a Python package that extracts the accessibility tree of a macOS application's screen in JSON format. It also provides an option to capture screenshots of the application, including labeled bounding boxes with different colors representing various element types. This tool is useful for accessibility testing, UI automation, and visual debugging.

---

## Features

- **Accessibility Tree Extraction**: Retrieve the accessibility hierarchy of a macOS application in JSON format.
- **Screenshot Capture**: Capture a cropped screenshot of the application window.
- **Labeled Visual Output**: Generate a segmented screenshot with bounding boxes highlighting UI elements, colored by their types.

---

## Installation

To install `macapptree`, use `pip`:

```bash
pip install macapptree
```
> Note: This package requires macOS and Python 3.10+.

---

## Usage

The library provides two primary functions:
* `get_tree`: Extracts the accessibility tree of a macOS app.
* `get_tree_screenshot`: Extracts the accessibility tree and generates screenshots.

### Example

```python
from macapptree import get_tree, get_tree_screenshot, get_app_bundle

# Get the app bundle identifier (for example: "com.apple.TextEdit")
bundle = get_app_bundle("TextEdit")

# Retrieve the accessibility tree, a cropped screenshot, and a segmented screenshot
tree, im, im_seg = get_tree_screenshot(bundle)

# `tree`: JSON-like structure of the accessibility elements
# `im`: Cropped screenshot of the application window
# `im_seg`: Labeled screenshot with bounding boxes indicating UI elements

```

### Output

* **tree**: A Python dictionary representing the accessibility hierarchy.
* **im**: A cropped `PIL.Image` object of the app window.
* **im_seg**: A `PIL.Image` object with bounding boxes drawn on top, colored based on the element type.

---


## Example Tree Output

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
    "bbox": [
        0,
        0,
        586,
        476
    ],
    "visible_bbox": [
        0,
        0,
        586,
        476
    ],
    "children": [
        {
            "id": "422f5e0df37aa872341d3b6a47faf320",
            "name": null,
            "role": "AXScrollArea",
            "description": null,
            "role_description": "scroll area",
            "value": null,
            "absolute_position": "214.00;175.00",
            "position": "0.00;56.00",
            "size": "586;420",
            "enabled": false,
            "bbox": [
                0,
                56,
                586,
                476
            ],
            "visible_bbox": [
                0,
                56,
                586,
                476
            ],
            "children": [
                ...
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
