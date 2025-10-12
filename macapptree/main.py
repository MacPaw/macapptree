import AppKit
import ApplicationServices
import argparse
import json
import os
import time
from PIL import ImageGrab, Image, ImageDraw, ImageFont

from macapptree.screenshot_app_window import (
    get_window_info,
    get_visible_windows_for_bundles,
    rect_subtract,
)
import macapptree.apps as apps
from macapptree.window_tools import store_screen_scaling_factor, segment_window_components
from macapptree.uielement import UIElement, element_attribute, element_value
from macapptree.extractor import extract_window
from macapptree.screenshot_app_window import screenshot_window_to_file
from macapptree.apps import dock_ax_application

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


def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter <= 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    return inter / float(area_a + area_b - inter + 1e-9)

def _build_global_visible_index(bundle_ids):
    windows = get_visible_windows_for_bundles(bundle_ids) 
    seen = []
    out = []
    for w in windows:
        x, y, W, H = w["bounds"]
        full = (x, y, W, H)
        remaining = rect_subtract(full, seen)
        if remaining:
            out.append({"pid": w["pid"], "bounds": full, "visible": remaining})
            seen.append(full)
        else:
            out.append({"pid": w["pid"], "bounds": full, "visible": []})
    return out

def _menu_bar_tl_rect() -> tuple[int,int,int,int]:
    """Return TOP-LEFT rect of the menu bar in points."""
    screen = AppKit.NSScreen.mainScreen().frame()
    sw, sh = int(screen.size.width), int(screen.size.height)
    thickness = int(AppKit.NSStatusBar.systemStatusBar().thickness())
    return (0, 0, sw, thickness)

def _menubar_ax_for_front_app():
    ws = AppKit.NSWorkspace.sharedWorkspace()
    front = ws.frontmostApplication()
    if not front:
        return None
    ax_app = apps.application_for_process_id(front.processIdentifier())
    try:
        return element_attribute(ax_app, ApplicationServices.kAXMenuBarAttribute)
    except Exception:
        return None

def _menubar_ax_for_system():
    ws = AppKit.NSWorkspace.sharedWorkspace()
    for ra in ws.runningApplications():
        if ra.bundleIdentifier() == "com.apple.SystemUIServer":
            return apps.application_for_process_id(ra.processIdentifier())
    return None

# menu bar (top)
def process_menu_bar(max_depth=None, output_screenshot_dir=None):
    store_screen_scaling_factor()

    x_tl, y_tl, w, h = _menu_bar_tl_rect()
    win_rect_tl = [x_tl, y_tl, x_tl + w, y_tl + h]

    roots, shot_info = [], None

    ax_mb_left = _menubar_ax_for_front_app()
    if ax_mb_left:
        mb_left = UIElement(
            ax_mb_left,
            max_depth=max_depth,
            parents_visible_bbox=[0, 0, w, h],
        )
        mb_left.app_name = "MenuBar (App)"
        mb_left.window_screen_rect = win_rect_tl
        extract_window(mb_left, "front.app.menubar", None,
                       perform_hit_test=False, print_nodes=False, max_depth=max_depth)
        _propagate_screen_rect(mb_left, win_rect_tl)
        roots.append(mb_left)

    ax_sys = _menubar_ax_for_system()
    if ax_sys:
        try:
            ax_mb_right = element_attribute(ax_sys, ApplicationServices.kAXMenuBarAttribute) or ax_sys
        except Exception:
            ax_mb_right = ax_sys
        mb_right = UIElement(
            ax_mb_right,
            max_depth=max_depth,
            parents_visible_bbox=[0, 0, w, h],
        )
        mb_right.app_name = "MenuBar (System)"
        mb_right.window_screen_rect = win_rect_tl
        extract_window(mb_right, "com.apple.SystemUIServer", None,
                       perform_hit_test=False, print_nodes=False, max_depth=max_depth)
        _propagate_screen_rect(mb_right, win_rect_tl)
        roots.append(mb_right)

    if output_screenshot_dir:
        os.makedirs(output_screenshot_dir, exist_ok=True)
        full_path = os.path.join(output_screenshot_dir, "menubar_full.png")
        capture_full_screen(full_path)

        crop_path = full_path.replace(".png", "_cropped.png")
        from macapptree.screenshot_app_window import crop_screenshot
        _ = crop_screenshot(full_path, (x_tl, y_tl, w, h), crop_path)

        if roots:
            segment_window_components(roots[0], crop_path)
        shot_info = {
            "app": "menubar",
            "window_name": "MenuBar",
            "cropped_screenshot_path": crop_path,
            "segmented_screenshot_path": crop_path.replace(".png", "_segmented.png"),
        }

    return roots, shot_info


# dock
def process_dock(max_depth=None, output_screenshot_dir=None):
    store_screen_scaling_factor()

    dock_ax = dock_ax_application()
    if dock_ax is None:
        print("Dock not found/running.")
        return None, None

    x_tl, y_tl, w, h = _dock_tl_rect_fixed("bottom")

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
    _propagate_screen_rect(dock_root, dock_root.window_screen_rect)

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


def _propagate_screen_rect(ui_element, screen_rect_tl):
    ui_element.window_screen_rect = screen_rect_tl
    for child in getattr(ui_element, "children", []):
        _propagate_screen_rect(child, screen_rect_tl)

def capture_full_screen(output_path: str):
    screen = AppKit.NSScreen.mainScreen()
    frame = screen.frame()
    left, top = int(frame.origin.x), int(frame.origin.y)
    width, height = int(frame.size.width), int(frame.size.height)
    img = ImageGrab.grab(bbox=(left, top, left + width, top + height))
    img.save(output_path)
    print(f"Full-screen screenshot saved to {output_path}")
    return output_path

def get_window_rect(window):
    pos = element_attribute(window, ApplicationServices.kAXPositionAttribute)
    size = element_attribute(window, ApplicationServices.kAXSizeAttribute)
    if pos is None or size is None:
        return None
    pos = element_value(pos, ApplicationServices.kAXValueCGPointType)
    size = element_value(size, ApplicationServices.kAXValueCGSizeType)
    if pos is None or size is None:
        return None
    x, y = pos.x, pos.y
    w, h = size.width, size.height
    return [x, y, x + w, y + h]


def draw_bounding_boxes_on_full_screen(full_screen_path, ui_elements, output_path=None):
    img = Image.open(full_screen_path)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

    screen_frame = AppKit.NSScreen.mainScreen().frame()
    sw_pt = int(screen_frame.size.width)
    sh_pt = int(screen_frame.size.height)
    iw_px, ih_px = img.size
    sx = iw_px / max(1, sw_pt)
    sy = ih_px / max(1, sh_pt)

    for e in ui_elements:
        if not getattr(e, "visible", False):
            continue

        win_rect = getattr(e, "window_screen_rect", None)   
        vb = getattr(e, "visible_bbox", None) 
        if not win_rect or not vb:
            continue

        wx1, wy1, _, _ = win_rect
        ex1, ey1, ex2, ey2 = vb

        sx1_pt = wx1 + ex1
        sy1_pt = wy1 + ey1
        sx2_pt = wx1 + ex2
        sy2_pt = wy1 + ey2

        X1 = int(round(sx1_pt * sx))
        Y1 = int(round(sy1_pt * sy))
        X2 = int(round(sx2_pt * sx))
        Y2 = int(round(sy2_pt * sy))

        if X2 < X1: X2 = X1
        if Y2 < Y1: Y2 = Y1

        try:
            draw.rectangle([X1, Y1, X2, Y2], outline="red", width=3)
            if font:
                label = e.name or ""
                if getattr(e, "app_name", None):
                    label += f" ({e.app_name})"
                draw.text((X1, max(0, Y1 - 12)), label, fill="red", font=font)
        except Exception as ex:
            print(f"draw fail for element: {ex}")

    output_path = output_path or full_screen_path.replace(".png", "_annotated.png")
    img.save(output_path)
    return output_path


def process_app(app_bundle, max_depth, output_screenshot_dir=None, global_vis_index=None):
    store_screen_scaling_factor()
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    app = apps.application_for_bundle(app_bundle, workspace)
    if app is None:
        print(f"App {app_bundle} not running.")
        return [], []

    application = apps.application_for_process_id(app.processIdentifier())
    windows = apps.windows_for_application(application)
    if not windows:
        print(f"No windows found for {app_bundle}")
        return [], []

    cg_entries = [e for e in (global_vis_index or []) if e["pid"] == int(app.processIdentifier())]

    all_ui_elements = []
    screenshot_info_list = []

    for ax_win in windows:
        rect = get_window_rect(ax_win)  
        if not rect:
            continue
        x_tl, y_tl, x2_tl, y2_tl = rect
        w_ax, h_ax = (x2_tl - x_tl), (y2_tl - y_tl)

        best = None
        best_iou = 0.0
        for cg in cg_entries:
            cx, cy, cW, cH = cg["bounds"]
            cand = (cx, cy, cx + cW, cy + cH)
            iou = _iou((x_tl, y_tl, x2_tl, y2_tl), cand)
            if iou > best_iou:
                best_iou, best = iou, cg
        if not best:
            continue

        vis_rects = best["visible"] 
        # skip not visible windows
        if not vis_rects:
            continue

        vx1 = min(r[0] for r in vis_rects)
        vy1 = min(r[1] for r in vis_rects)
        vx2 = max(r[0] + r[2] for r in vis_rects)
        vy2 = max(r[1] + r[3] for r in vis_rects)

        ix1, iy1 = max(x_tl, vx1), max(y_tl, vy1)
        ix2, iy2 = min(x2_tl, vx2), min(y2_tl, vy2)
        if ix2 <= ix1 or iy2 <= iy1:
            continue

        parents_visible_bbox = [
            int(ix1 - x_tl),
            int(iy1 - y_tl),
            int(ix2 - x_tl),
            int(iy2 - y_tl),
        ]

        win_screen_rect = [x_tl, y_tl, x_tl + w_ax, y_tl + h_ax]

        ui_window = UIElement(
            ax_win,
            max_depth=max_depth,
            parents_visible_bbox=parents_visible_bbox
        )
        ui_window.app_name = app.localizedName()
        ui_window.window_screen_rect = win_screen_rect

        extract_window(
            ui_window, app_bundle, None,
            perform_hit_test=False, print_nodes=False, max_depth=max_depth
        )
        _propagate_screen_rect(ui_window, win_screen_rect)
        all_ui_elements.append(ui_window)

        if output_screenshot_dir:
            os.makedirs(output_screenshot_dir, exist_ok=True)
            window_name = getattr(ax_win, "name", None) or app.localizedName() or "window"
            crop_path, _ = screenshot_window_to_file(
                app.localizedName(),
                window_name,
                os.path.join(output_screenshot_dir, f"{app.localizedName()}_{window_name}_cropped.png")
            )
            segmented_path = segment_window_components(ui_window, crop_path)
            screenshot_info_list.append({
                "app": app_bundle,
                "window_name": window_name,
                "cropped_screenshot_path": crop_path,
                "segmented_screenshot_path": segmented_path
            })

    return all_ui_elements, screenshot_info_list


def main(app_bundles, output_accessibility_file, output_screenshot_dir, max_depth,
         include_menubar=False, include_dock=False):
    store_screen_scaling_factor()

    all_elements = []
    all_screenshots = []

    workspace = AppKit.NSWorkspace.sharedWorkspace()
    for app_bundle in app_bundles:
        app = apps.application_for_bundle(app_bundle, workspace)
        if app is None:
            print(f"App {app_bundle} not found or not running.")
    time.sleep(1)

    full_screen_path = None
    if output_screenshot_dir:
        os.makedirs(output_screenshot_dir, exist_ok=True)
        full_screen_path = os.path.join(output_screenshot_dir, "full_screen.png")
        capture_full_screen(full_screen_path)

    # Build global visible index (front->back)
    global_vis_index = _build_global_visible_index(app_bundles)

    for app_bundle in app_bundles:
        print(f"Processing app: {app_bundle}")
        elements, screenshots = process_app(
            app_bundle, max_depth, output_screenshot_dir, global_vis_index=global_vis_index
        )
        all_elements.extend(elements)
        all_screenshots.extend(screenshots)

    if include_menubar:
        print("Processing Menu Bar…")
        mb_roots, mb_shots = process_menu_bar(max_depth, output_screenshot_dir)
        for r in mb_roots:
            all_elements.append(r)
        if mb_shots:
            all_screenshots.append(mb_shots)

    if include_dock:
        print("Processing Dock…")
        dock_root, dock_shots = process_dock(max_depth, output_screenshot_dir)
        if dock_root:
            all_elements.append(dock_root)
        if dock_shots:
            all_screenshots.append(dock_shots)

    accessibility_data = []
    for e in all_elements:
        d = e.to_dict()
        if getattr(e, "app_name", None):
            d["app_name"] = e.app_name
        accessibility_data.append(d)
    with open(output_accessibility_file, "w", encoding="utf-8") as f:
        json.dump(accessibility_data, f, ensure_ascii=False, indent=4)

    if all_screenshots:
        print(json.dumps(all_screenshots, indent=4))

    if full_screen_path and all_elements:
        annotated_path = os.path.join(output_screenshot_dir, "full_screen_annotated.png")
        all_elements_flat = _flatten_ui_elements(all_elements)
        draw_bounding_boxes_on_full_screen(full_screen_path, all_elements_flat, annotated_path)

def _flatten_ui_elements(ui_elements):
    flat = []
    def recurse(e):
        flat.append(e)
        for c in getattr(e, "children", []):
            recurse(c)
    for root in ui_elements:
        recurse(root)
    return flat

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--apps", type=str, nargs="+", default=None,
        help="One or more application bundle identifiers (space-separated). If omitted with --all-apps, discover visible apps automatically."
    )
    parser.add_argument("--oa", type=str, required=True, help="Accessibility output JSON file")
    parser.add_argument("--os", type=str, default=None, help="Directory to save cropped/segmented screenshots")
    parser.add_argument("--max-depth", type=int, default=None, help="Maximum depth of the accessibility tree")
    parser.add_argument("--include-menubar", action="store_true", help="Also capture the top Menu Bar (front app + system extras)")
    parser.add_argument("--include-dock", action="store_true", help="Also capture the Dock (lower/side bar) accessibility tree")
    parser.add_argument("--all-apps", action="store_true", help="Ignore -a and auto-discover visible apps .")
    args = parser.parse_args()

    target_apps = args.apps
    if args.all_apps or not target_apps:
        from macapptree.apps import list_visible_app_bundles
        target_apps = list_visible_app_bundles()

    main(
        target_apps,
        args.oa,
        args.os,
        args.max_depth,
        include_menubar=args.include_menubar,
        include_dock=args.include_dock
    )
