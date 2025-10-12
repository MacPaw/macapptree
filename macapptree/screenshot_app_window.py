from typing import Iterable, List, Dict, AnyStr, Union, Tuple
from macapptree.uielement import UIElement
import subprocess
import time
import Quartz
import os
import AppKit
from unidecode import unidecode
from PIL import Image
from macapptree.exceptions import WindowNotFoundException

import time as _time

def reveal_dock_temporarily(orientation: str, dwell: float = 0.7):
    try:
        screen = AppKit.NSScreen.mainScreen().frame()
        sw, sh = int(screen.size.width), int(screen.size.height)

        if orientation and orientation.lower() == "left":
            x, y = 2, sh // 2
        elif orientation and orientation.lower() == "right":
            x, y = sw - 2, sh // 2
        else: 
            x, y = sw // 2, sh - 2

        evt = Quartz.CGEventCreateMouseEvent(
            None, Quartz.kCGEventMouseMoved, (x, y), Quartz.kCGMouseButtonLeft
        )
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, evt)
        _time.sleep(dwell)
    except Exception:
        pass

import subprocess, AppKit

def _read_defaults(domain: str, key: str, fallback=None):
    try:
        out = subprocess.check_output(
            ["defaults", "read", domain, key],
            stderr=subprocess.STDOUT,
            text=True
        ).strip()
        return out
    except Exception:
        return fallback

def get_dock_prefs():
    orient = _read_defaults("com.apple.dock", "orientation", "bottom")
    tilesize = int(float(_read_defaults("com.apple.dock", "tilesize", "64")))
    magnification = (_read_defaults("com.apple.dock", "magnification", "0") in ("1", "true", "YES"))
    largesize = int(float(_read_defaults("com.apple.dock", "largesize", str(tilesize))))
    autohide = (_read_defaults("com.apple.dock", "autohide", "0") in ("1", "true", "YES"))
    return {
        "orientation": orient,
        "tilesize": tilesize,
        "magnification": magnification,
        "largesize": largesize,
        "autohide": autohide,
    }

def dock_rect_from_prefs() -> tuple[int,int,int,int]:
    prefs = get_dock_prefs()
    screen = AppKit.NSScreen.mainScreen().frame()
    sw, sh = int(screen.size.width), int(screen.size.height)

    base = prefs["largesize"] if prefs["magnification"] else prefs["tilesize"]
    thickness_pt = int(base + 24) 

    o = (prefs["orientation"] or "bottom").lower()
    if o == "left":
        return (0, 0, thickness_pt, sh)
    if o == "right":
        return (sw - thickness_pt, 0, thickness_pt, sh)
    return (0, sh - thickness_pt, sw, thickness_pt) 


def get_dock_window_bounds():
    """
    Return (x_tl, y_tl, w, h) for the actual Dock window.
    """
    windows = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll,
        Quartz.kCGNullWindowID
    )
    # main screen for heuristics
    screen = AppKit.NSScreen.mainScreen().frame()
    screen_w, screen_h = int(screen.size.width), int(screen.size.height)

    # gather all windows that belong to Dock
    dock_wins = []
    for w in windows:
        owner = w.get("kCGWindowOwnerName", "") or ""
        if owner != "Dock":
            continue
        b = w.get("kCGWindowBounds", {})
        if not b:
            continue
        x, y, W, H = int(b.get("X", 0)), int(b.get("Y", 0)), int(b.get("Width", 0)), int(b.get("Height", 0))
        layer = int(w.get("kCGWindowLayer", 0))
        alpha = float(w.get("kCGWindowAlpha", 1.0))
        if alpha == 0 or W == 0 or H == 0:
            continue
        dock_wins.append((x, y, W, H, layer))

    if not dock_wins:
        return None

    candidates = []
    for x, y, W, H, layer in dock_wins:
        area = W * H
        bottom_like = (y >= screen_h - H - 4) and (W >= 0.4 * screen_w) and (H <= screen_h * 0.33)
        side_like   = (H >= 0.4 * screen_h) and (W <= screen_w * 0.33)
        if bottom_like or side_like:
            candidates.append((area, x, y, W, H))

    if not candidates:
        x, y, W, H, _ = max(dock_wins, key=lambda t: t[2] * t[3])
        return (x, y, W, H)

    _, x, y, W, H = max(candidates, key=lambda t: t[0])
    return (x, y, W, H)


class ScreencaptureEx(Exception):
    pass


WindowInfo = Dict[AnyStr, Union[AnyStr, int]]

USER_OPTS_STR = "exclude_desktop on_screen_only"
FILE_EXT = "png"
COMMAND = 'screencapture -C -o "{filename}"'
SUCCESS = 0
STATUS_BAR_WINDOW_IDENTIFIER = "Item-0"


# get window info
def get_window_info() -> List[WindowInfo]:
    return Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListOptionAll
        | Quartz.kCGWindowListOptionIncludingWindow
        | Quartz.kCGWindowListExcludeDesktopElements
        | Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
    )


# generate window ids
def gen_ids_from_info(
        windows: Iterable[WindowInfo],
) -> List[Tuple[int, str, str]]: 
    result = [] 
    for win_dict in windows:
        owner = win_dict.get("kCGWindowOwnerName", "")
        num = win_dict.get("kCGWindowNumber", "")
        name = win_dict.get("kCGWindowName", "")
        bounds = win_dict.get('kCGWindowBounds', "")

        x = bounds['X']
        y = bounds['Y']
        width = bounds['Width']
        height = bounds['Height']

        result.append((num, owner, name, (x, y, width, height)))
    return result


def gen_window_ids(
        parent: str,
) -> List[Tuple[int, str]]: 
    windows = get_window_info()
    parent = parent.lower()
    result = [] 

    for num, owner, window_name, (x, y, width, height) in gen_ids_from_info(windows):
        if parent == owner.lower():
            if window_name == STATUS_BAR_WINDOW_IDENTIFIER:
                print(f"Skipping status bar window: {num}")
            else:
                window_name = window_name.replace(" ", "_")
                result.append((num, window_name, (x, y, width, height)))

    return result 


# take screenshot
def take_screenshot(window: int, filename: str, output_folder: str = None) -> str:
    if output_folder:
        filename = os.path.join(output_folder, filename)

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

    command = COMMAND.format(window=window, filename=filename, options="")
    rc, output = subprocess.getstatusoutput(command)
    if rc != SUCCESS:
        raise ScreencaptureEx(f"Error: screencapture output: {output}")

    return filename


# get filename
def get_filename(window_name, extension, add_cursor_move) -> str:
    if window_name != "":
        if add_cursor_move:
            return f"{window_name}:{time.time():.2f}_cursor.{extension}"
        else:
            return f"{window_name}:{time.time():.2f}.{extension}"
    if add_cursor_move:
        return f"{time.time():.2f}_cursor.{extension}"
    else:
        return f"{time.time():.2f}.{extension}"


def crop_screenshot(image_path, window_coords, output_path):
    backing_scale_factor = AppKit.NSScreen.mainScreen().backingScaleFactor()

    screenshot = Image.open(image_path)

    left, top, width, height = window_coords

    right = left + width
    bottom = top + height

    cropped_image = screenshot.crop((int(left * backing_scale_factor),
                                     int(top * backing_scale_factor),
                                     int(right * backing_scale_factor),
                                     int(bottom * backing_scale_factor)))

    cropped_image.save(output_path)
    scaled_coors = (int(left ),
                    int(top ),
                    int(right ),
                    int(bottom ))
    return scaled_coors


def find_window(
        app_name: str,
        window_name: str
        ):
    # generate all windows
    windows = gen_windows(app_name)
    if window_name is None:
        identifier, name, window_coords = windows[0]
        decoded_name = unidecode(name)
        return identifier, decoded_name, window_coords

    decoded_window_name = unidecode(window_name)

    # search for the window
    for identifier, name, window_coords in windows:
        decoded_name = unidecode(name)
        
        if decoded_name == decoded_window_name or decoded_window_name == app_name or window_name == "":  
            return identifier, decoded_name, window_coords
    
    for identifier, name, window_coords in windows:
        decoded_name = unidecode(name)
        
        if decoded_window_name.startswith(decoded_name): 
            return identifier, decoded_name, window_coords
    
    raise WindowNotFoundException(f"Window {window_name} not found.")


def screenshot_window_to_file(
        app_name: str,
        window_name: str,
        output_file: str
) -> str:
    identifier, _, window_coords = find_window(app_name, window_name)
    take_screenshot(identifier, output_file)
    _, extension = os.path.splitext(output_file)
    time.sleep(0.4)
    filename_cropped = output_file.replace(f".{extension}", f"_cropped.{extension}")
    scaled_coors = crop_screenshot(output_file, window_coords, filename_cropped)
    time.sleep(0.4)
    return filename_cropped, scaled_coors


# screenshot required window
def screenshot_windows(
        app_name: str,
        window_name: str,
        element_identifier: str,
        output_folder: str,
        extension: str = "",
        add_cursor_move: bool = False,
) -> str:
    
    try:
        identifier, name, window_coords = find_window(app_name, window_name)
        if name == "":
            name = element_identifier
        file_name = get_filename(name, extension, add_cursor_move)
        file_path = take_screenshot(identifier, file_name, output_folder)
        time.sleep(0.4)

        file_path_cropped = file_path.replace(f".{extension}", f"_cropped.{extension}")
        file_name_cropped = file_name.replace(f".{extension}", f"_cropped.{extension}")

        scaled_coors = crop_screenshot(file_path, window_coords, file_path_cropped)
        time.sleep(0.4)
        return (file_name_cropped, scaled_coors)
    except Exception as e:
        print(repr(e))
        return


# generate window ids
def gen_windows(application_name: str) -> List[int]:  
    windows = list(gen_window_ids(application_name)) 
    if not windows:  
        print(f"Window with parent {application_name} not found.")
    return windows 


# screenshot application
def screenshot_app(
        app_name: str,
        window_name: str,
        element_identifier: str,
        output_folder: str,
        extension: str,
        add_cursor_move: bool = False,
) -> str:
    return screenshot_windows(
        app_name, window_name, element_identifier, output_folder, extension, add_cursor_move
    )


# running application for the bundle id
def running_app(app_bundle):
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    for app in workspace.runningApplications():
        if app.bundleIdentifier() == app_bundle:
            return app
    return None


def screenshot_app_window(
        bundle_id, window_name, element_identifier: str, output_folder, add_cursor_move
) -> str:
    app = running_app(bundle_id)
    return screenshot_app(
        app.localizedName(), window_name, element_identifier, output_folder, FILE_EXT, add_cursor_move
    )


def screenshot_image_element(element: UIElement, output_folder: str):
    image = element.get_image()
    filename = f"{element.get_name()}-{time.time():.2f}.{FILE_EXT}"
    image.save(os.path.join(output_folder, filename), FILE_EXT)
    print(f"Screenshot saved to {filename}")



from typing import List, Dict, Tuple

# --- helper: map running apps for requested bundle ids ---
def _get_running_apps_for_bundles(bundle_ids: List[str]) -> Tuple[Dict[int,str], Dict[str, AppKit.NSRunningApplication]]:
    """
    Returns:
      pid_to_bundle: { pid: bundle_id } for running apps that match bundle_ids
      bundle_to_app: { bundle_id: NSRunningApplication }
    """
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    pid_to_bundle = {}
    bundle_to_app = {}
    for app in workspace.runningApplications():
        bid = app.bundleIdentifier()
        if bid in bundle_ids:
            pid_to_bundle[int(app.processIdentifier())] = bid
            bundle_to_app[bid] = app
    return pid_to_bundle, bundle_to_app


def get_visible_windows_for_bundles(bundle_ids: List[str]) -> List[Dict]:
    """
    Returns a list of windows that belong to any of the running applications
    specified by bundle_ids.

    Each returned item is a dict:
    {
      "window_number": int,
      "owner": str,            # owner name
      "name": str,             # window name (may be empty)
      "bounds": (x, y, w, h), # integers, screen coordinates
      "pid": int,
      "bundle": "com.example.app",
      "layer": int,
      "alpha": float,
      "raw": <original CGWindow dict>,
      "z_index": int           # index from CGWindowListCopyWindowInfo (used for ordering)
    }

    Ordering: front (top-most) -> back (bottom-most). Sorting heuristic:
      - higher window layer first
      - then by the position returned by CGWindowListCopyWindowInfo
    """
    pid_map, bundle_apps = _get_running_apps_for_bundles(bundle_ids)

    windows = get_window_info()
    results = []
    for idx, win in enumerate(windows):
        pid = win.get("kCGWindowOwnerPID")
        if pid is None:
            continue
        pid = int(pid)
        if pid not in pid_map:
            continue

        num = win.get("kCGWindowNumber")
        owner = win.get("kCGWindowOwnerName", "") or ""
        name = win.get("kCGWindowName", "") or ""
        bounds = win.get("kCGWindowBounds", {}) or {}
        x = int(bounds.get("X", 0))
        y = int(bounds.get("Y", 0))
        w = int(bounds.get("Width", 0))
        h = int(bounds.get("Height", 0))
        layer = int(win.get("kCGWindowLayer", 0))
        alpha = float(win.get("kCGWindowAlpha", 1.0))

        results.append({
            "window_number": num,
            "owner": owner,
            "name": name,
            "bounds": (x, y, w, h),
            "pid": pid,
            "bundle": pid_map[pid],
            "layer": layer,
            "alpha": alpha,
            "z_index": idx
        })


    results.sort(key=lambda w: (-w["layer"], w["z_index"]))
    return results

from typing import List, Tuple

Rect = Tuple[int, int, int, int]  # (x, y, w, h)

def rect_intersection(a: Rect, b: Rect) -> Rect | None:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh

    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)

    if ix1 < ix2 and iy1 < iy2:
        return (ix1, iy1, ix2 - ix1, iy2 - iy1)
    return None


def rect_subtract(a: Rect, bs: List[Rect]) -> List[Rect]:
    """
    Subtract rectangles bs from a.
    Returns a list of remaining non-overlapping rects (may be multiple).
    """
    remaining = [a]
    for b in bs:
        new_remaining = []
        for r in remaining:
            inter = rect_intersection(r, b)
            if not inter:
                new_remaining.append(r)
                continue
            rx, ry, rw, rh = r
            ix, iy, iw, ih = inter
            # top
            if iy > ry:
                new_remaining.append((rx, ry, rw, iy - ry))
            # bottom
            if iy + ih < ry + rh:
                new_remaining.append((rx, iy + ih, rw, (ry + rh) - (iy + ih)))
            # left
            if ix > rx:
                new_remaining.append((rx, iy, ix - rx, ih))
            # right
            if ix + iw < rx + rw:
                new_remaining.append((ix + iw, iy, (rx + rw) - (ix + iw), ih))
        remaining = new_remaining
    return remaining
