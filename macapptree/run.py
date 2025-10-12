from PIL import Image
import subprocess
import tempfile
import json
import re
import os
from macapptree.window_tools import store_screen_scaling_factor
from macapptree.uielement import UIElement
from macapptree.extractor import extract_window
from macapptree.screenshot_app_window import screenshot_window_to_file
from macapptree.window_tools import segment_window_components
import Quartz

def get_app_bundle(app_name):
    command = ['osascript', '-e', f'id of app "{app_name}"']
    bundle = subprocess.run(command, stdout=subprocess.PIPE).stdout.decode('utf-8')[:-1]
    return bundle


def launch_app(app_bundle):
    try:
        subprocess.check_call(["python", "-m", "macapptree.launch_app", "-a", app_bundle])
    except subprocess.CalledProcessError as e:
        print(f"Failed to launch app: {app_bundle}. Error: {e.stderr}")
        raise e


def get_tree(app_bundle, max_depth=None):
    launch_app(app_bundle)

    tmp_file = tempfile.NamedTemporaryFile(delete=False)
    command = ["python", "-m", "macapptree.main", "-a", app_bundle, "--oa", tmp_file.name]
    if max_depth:
        command.extend(["--max-depth", str(max_depth)])
    try:
        subprocess.check_call(command)
        return json.load(tmp_file)
    except subprocess.CalledProcessError as e:
        print(f"Failed to extract app accessibility for {app_bundle}. Error: {e.stderr}")
        raise e
    finally:
        tmp_file.close()


def get_tree_screenshot(app_bundle, max_depth=None):
    launch_app(app_bundle)
    
    a11y_tmp_file = tempfile.NamedTemporaryFile(delete=False)
    screenshot_tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    command = ["python", "-m", "macapptree.main", 
                "-a", app_bundle, 
                "--oa", a11y_tmp_file.name,
                "--os", screenshot_tmp_file.name]
    if max_depth:
        command.extend(["--max-depth", str(max_depth)])
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        # print(result.stdout)
        json_match = re.search(r'{.*}', result.stdout, re.DOTALL)
        if not json_match:
            print(f"Failed to extract screenshots for {app_bundle}")
            return json.load(a11y_tmp_file), None, None

        json_str = json_match.group(0)
        screenshots_paths_dict = json.loads(json_str)
        croped_img = Image.open(screenshots_paths_dict["croped_screenshot_path"])
        segmented_img = Image.open(screenshots_paths_dict["segmented_screenshot_path"])

        os.remove(screenshots_paths_dict["croped_screenshot_path"])
        os.remove(screenshots_paths_dict["segmented_screenshot_path"])

        return json.load(a11y_tmp_file), croped_img, segmented_img
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Failed to extract app accessibility for {app_bundle}. Error: {e.stderr}")
        raise e
    finally:
        a11y_tmp_file.close()
        screenshot_tmp_file.close()


import macapptree.screenshot_app_window as screenshot_app_window


def get_visible_windows(app_bundles):
    """
    Public wrapper that returns visible windows for the list of bundle identifiers.
    Example:
        get_visible_windows(["com.apple.Safari", "com.apple.TextEdit"])
    """
    if not isinstance(app_bundles, (list, tuple)):
        raise ValueError("app_bundles must be a list of bundle identifiers")
    return screenshot_app_window.get_visible_windows_for_bundles(app_bundles)


# def get_trees_for_windows(bundle_ids):
#     windows = get_visible_windows(bundle_ids)
#     trees = []
#     for win in windows:
#         app_elem = Quartz.AXUIElementCreateApplication(win["pid"])
#         # Build the tree clipped to the window rectangle
#         tree = UIElement(ax_elem=app_elem, parents_visible_bbox=win["bounds"])
#         trees.append({
#             "window_info": win,
#             "tree": tree.to_dict()
#         })
#     return trees
def get_trees_for_windows(bundle_ids):
    windows = get_visible_windows(bundle_ids)

    # windows are already sorted front-to-back (z_index ascending = back, descending = front)
    # ensure front-most first
    windows.sort(key=lambda w: (-w["layer"], w["z_index"]))

    seen_regions: List[Rect] = []
    trees = []

    for win in windows:
        win_bounds: Rect = tuple(win["bounds"])
        # subtract already-seen (higher z-index) regions
        visible_regions = rect_subtract(win_bounds, seen_regions)

        if not visible_regions:
            # fully occluded -> skip
            continue

        # For now: pick the union bbox of remaining regions (simple)
        # Later we can pass multiple regions per element if needed
        vx1 = min(r[0] for r in visible_regions)
        vy1 = min(r[1] for r in visible_regions)
        vx2 = max(r[0] + r[2] for r in visible_regions)
        vy2 = max(r[1] + r[3] for r in visible_regions)
        visible_bbox = (vx1, vy1, vx2 - vx1, vy2 - vy1)

        app_elem = Quartz.AXUIElementCreateApplication(win["pid"])
        tree = UIElement(ax_elem=app_elem, parents_visible_bbox=visible_bbox)

        trees.append({
            "window_info": win,
            "tree": tree.to_dict()
        })

        # mark this window's full rect as "seen" (so windows under it are clipped)
        seen_regions.append(win_bounds)

    return trees



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="macapptree.run helper")
    parser.add_argument(
        "--list-windows",
        type=str,
        help="Comma-separated bundle identifiers to list windows for, e.g. com.apple.Safari,com.apple.TextEdit",
    )
    args = parser.parse_args()
    if args.list_windows:
        bundles = [b.strip() for b in args.list_windows.split(",") if b.strip()]
        windows = get_visible_windows(bundles)
        print(json.dumps(windows, indent=2))


# def get_trees_for_windows(bundle_ids):
#     windows = get_visible_windows(bundle_ids)
#     trees = []
#     for win in windows:
#         app_elem = Quartz.AXUIElementCreateApplication(win["pid"])
#         tree = UIElement(ax_elem=app_elem, parents_visible_bbox=win["bounds"])
#         trees.append({
#             "window_info": win,
#             "tree": tree.to_dict()
#         })
#     return trees
