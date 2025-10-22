import os
import time
import AppKit
import Quartz
import ApplicationServices

import macapptree.apps as apps
from macapptree.uielement import UIElement
from macapptree.extractor import extract_window
from macapptree.window_tools import store_screen_scaling_factor, segment_window_components
from macapptree.screenshot_app_window import capture_full_screen
from macapptree.window_tools import propagate_screen_rect

DOCK_THICKNESS_PT = 96 

def _dock_tl_rect_fixed(orientation: str = "bottom") -> tuple[int, int, int, int]:
    screen = AppKit.NSScreen.mainScreen().frame()
    sw, sh = int(screen.size.width), int(screen.size.height)
    t = int(DOCK_THICKNESS_PT)
    o = (orientation or "bottom").lower()
    if o == "left":
        return (0, 0, t, sh)
    if o == "right":
        return (sw - t, 0, t, sh)
    return (0, sh - t, sw, t)

def _propagate_screen_rect_local(ui_element, screen_rect_tl):
    ui_element.window_screen_rect = screen_rect_tl
    for child in getattr(ui_element, "children", []):
        _propagate_screen_rect_local(child, screen_rect_tl)

# if the dock is set to autohide, we can move the mouse to reveal it temporarily
def _reveal_dock_temporarily(orientation: str = "bottom", dwell: float = 0.8):
    try:
        screen = AppKit.NSScreen.mainScreen().frame()
        sw, sh = int(screen.size.width), int(screen.size.height)

        if orientation.lower() == "left":
            x, y = 2, sh // 2
        elif orientation.lower() == "right":
            x, y = sw - 2, sh // 2
        else:
            # bottom
            x, y = sw // 2, sh - 2

        evt = Quartz.CGEventCreateMouseEvent(None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, evt)
        time.sleep(dwell)
    except Exception:
        pass

class DockCapture:
    def __init__(self, orientation: str = "bottom", reveal: bool = True, dwell: float = 0.8):
        self.orientation = orientation
        self.reveal = reveal
        self.dwell = dwell

    def capture(self, max_depth=None, output_screenshot_dir=None):
        store_screen_scaling_factor()

        if self.reveal:
            _reveal_dock_temporarily(self.orientation, dwell=self.dwell)

        dock_ax = apps.dock_ax_application()

        x_tl, y_tl, w, h = _dock_tl_rect_fixed(self.orientation)

        dock_root = UIElement(
            dock_ax,
            offset_x=x_tl,
            offset_y=y_tl,
            max_depth=max_depth,
            parents_visible_bbox=[0, 0, w, h],
        )
        dock_root.app_name = "Dock"
        dock_root.window_screen_rect = [x_tl, y_tl, x_tl + w, y_tl + h]

        extract_window(
            dock_root, "com.apple.dock", None,
            perform_hit_test=False, print_nodes=False, max_depth=max_depth
        )
        propagate_screen_rect(dock_root, dock_root.window_screen_rect)

        screenshot_info = None
        if output_screenshot_dir:
            os.makedirs(output_screenshot_dir, exist_ok=True)

            full_path = os.path.join(output_screenshot_dir, "dock_full.png")
            capture_full_screen(full_path)

            crop_path = full_path.replace(".png", "_cropped.png")
            from macapptree.screenshot_app_window import crop_screenshot
            _ = crop_screenshot(full_path, (x_tl, y_tl, w, h), crop_path)

            segmented_path = segment_window_components(dock_root, crop_path) or crop_path
            screenshot_info = {
                "app": "com.apple.dock",
                "window_name": "Dock",
                "cropped_screenshot_path": crop_path,
                "segmented_screenshot_path": segmented_path,
            }

        return dock_root, screenshot_info
