import AppKit
import shutil

from PIL import Image, ImageDraw
from time import sleep


_screen_scaling_factor = 1

# get the screen scaling factor
def store_screen_scaling_factor():
    for screen in AppKit.NSScreen.screens():
        global _screen_scaling_factor
        _screen_scaling_factor = screen.backingScaleFactor()
        print(f"Screen scaling factor: {_screen_scaling_factor}")


# convert point from screen coordinates to window coordinates
def convert_point_to_window(point, window_element):
    for screen in AppKit.NSScreen.screens():
        if AppKit.NSPointInRect(point, screen.frame()):
            return AppKit.NSMakePoint(
                point.x + window_element.x,
                point.y - 1 + window_element.y,
            )
    return AppKit.NSMakePoint(0.0, 0.0)


# check if the windows are equal
def windows_are_equal(window1, window2):
    if (
        window1.name == window2.name
        and window1.role == window2.role
        and window1.position == window2.position
        and window1.size == window2.size
    ):
        return True
    return False


# get color for the role
def color_for_role(role):
    color = "red"
    if role == "AXButton":
        color = "blue"
    elif role == "AXTextField":
        color = "green"
    elif role == "AXStaticText":
        color = "yellow"
    elif role == "AXImage":
        color = "purple"
    elif role == "AXGroup":
        color = "orange"
    elif role == "AXScrollBar":
        color = "brown"
    elif role == "AXRow":
        color = "pink"
    elif role == "AXColumn":
        color = "cyan"
    elif role == "AXCell":
        color = "magenta"
    elif role == "AXTable":
        color = "lightblue"
    elif role == "AXOutline":
        color = "lightgreen"
    elif role == "AXLayoutArea":
        color = "lightyellow"
    elif role == "AXLayoutItem":
        color = "lavender"
    elif role == "AXHandle":
        color = "peachpuff"
    elif role == "AXSplitter":
        color = "lightsalmon"
    elif role == "AXIncrementor":
        color = "lightpink"
    elif role == "AXBusyIndicator":
        color = "lightcyan"
    elif role == "AXProgressIndicator":
        color = "plum"
    elif role == "AXToolbar":
        color = "darkred"
    elif role == "AXPopover":
        color = "darkblue"
    elif role == "AXMenu":
        color = "darkgreen"
    elif role == "AXMenuItem":
        color = "olive"
    elif role == "AXMenuBar":
        color = "rebeccapurple"
    elif role == "AXMenuBarItem":
        color = "darkorange"
    elif role == "AXMenuButton":
        color = "saddlebrown"
    elif role == "AXMenuItemCheckbox":
        color = "palevioletred"
    elif role == "AXMenuItemRadio":
        color = "darkcyan"
    elif role == "AXMenuItemPopover":
        color = "darkmagenta"
    elif role == "AXMenuItemSplitter":
        color = "black"
    elif role == "AXMenuItemTable":
        color = "white"
    elif role == "AXMenuItemTextField":
        color = "lightgray"
    elif role == "AXMenuItemStaticText":
        color = "darkgray"
    elif role == "AXMenuItemImage":
        color = "salmon"
    elif role == "AXMenuItemGroup":
        color = "lightblue"
    elif role == "AXMenuItemScrollBar":
        color = "lightgreen"
    elif role == "AXMenuItemRow":
        color = "lightyellow"
    elif role == "AXMenuItemColumn":
        color = "lavender"
    elif role == "AXMenuItemCell":
        color = "peachpuff"
    elif role == "AXMenuItemOutline":
        color = "burlywood"
    elif role == "AXMenuItemLayoutArea":
        color = "lightpink"
    elif role == "AXMenuItemLayoutItem":
        color = "lightcyan"
    elif role == "AXMenuItemHandle":
        color = "plum"
    elif role == "AXMenuItemSplitter":
        color = "darkred"
    elif role == "AXMenuItemIncrementor":
        color = "darkblue"
    elif role == "AXMenuItemBusyIndicator":
        color = "darkgreen"
    elif role == "AXMenuItemProgressIndicator":
        color = "darkyellow"
    elif role == "AXMenuItemToolbar":
        color = "rebeccapurple"
    elif role == "AXMenuItemPopover":
        color = "darkorange"
    return color


# segment the window components
def segment_window_components(window, image_path: str):
    print(f"Segmenting window {window.name}")
    if not image_path:
        print(f"Image for window {window.name} not found")
        return

    segment_image_path = image_path.replace(".png", "_segmented.png")
    shutil.copy2(image_path, segment_image_path)
    sleep(0.5)

    # segment the image
    segment_image(segment_image_path, window)
    sleep(0.5)

    return segment_image_path


# paint all children to a different color on the screenshot
def segment_image(image_path, window_element, image_drawer=None, img=None):
    if image_path is None:
        return

    # open the image and create a drawer
    draw = image_drawer

    if draw is None:
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

    # iterate over all children
    for child in getattr(window_element, "children", []):
        if getattr(child, "children", None):
            segment_image(image_path, child, image_drawer=draw, img=img)

        if not child.visible:
            continue

        bbox = child.visible_bbox
        if not bbox:
            continue

        size = getattr(child, "size", None)
        if size is None or size.width == 0 or size.height == 0:
            continue

        height_offset = 0 if size.height < 2 else 2

        # convert to device pixels 
        x1, y1, x2, y2 = bbox
        rx1 = int(x1 * _screen_scaling_factor)
        ry1 = int(y1 * _screen_scaling_factor)
        rx2 = int(x2 * _screen_scaling_factor) - 1
        ry2 = int(y2 * _screen_scaling_factor) - height_offset + 1

        if rx2 < rx1:
            rx2 = rx1
        if ry2 < ry1:
            ry2 = ry1

        color = color_for_role(getattr(child, "role", ""))

        try:
            draw.rectangle([(rx1, ry1), (rx2, ry2)], outline=color, width=2)
        except Exception as e:
            print(f"Error drawing rectangle: {e}")

    if image_drawer is None:
        print(f"Saving segmented image to {image_path}")
        img.save(image_path)
