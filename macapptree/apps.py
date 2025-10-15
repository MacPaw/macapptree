import ApplicationServices
import macapptree.uielement as uielement
import subprocess
from time import sleep
import Quartz
import AppKit
from typing import List, Dict, Tuple
from macapptree.screenshot_app_window import get_window_info


# system apps we want to exclude from the list of visible apps
_SYSTEM_EXCLUDES = {
    "Window Server",
    "Dock",
    "Control Center",
    "Notification Center",
    "loginwindow",
    "Spotlight",
    "ScreensaverEngine",
}

DOCK_BUNDLE = "com.apple.dock"

def _get_running_apps_for_bundles(bundle_ids: List[str]) -> Tuple[Dict[int,str], Dict[str, AppKit.NSRunningApplication]]:
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    pid_to_bundle = {}
    bundle_to_app = {}
    for app in workspace.runningApplications():
        bid = app.bundleIdentifier()
        if bid in bundle_ids:
            pid_to_bundle[int(app.processIdentifier())] = bid
            bundle_to_app[bid] = app
    return pid_to_bundle, bundle_to_app

def _pid_to_bundle_map():
    ws = AppKit.NSWorkspace.sharedWorkspace()
    mapping = {}
    for ra in ws.runningApplications():
        bid = ra.bundleIdentifier()
        if bid:
            mapping[int(ra.processIdentifier())] = bid
    return mapping

def list_visible_app_bundles(extras_exclude: set[str] | None = None) -> list[str]:
    excludes = set(extras_exclude or set()) | _SYSTEM_EXCLUDES
    pid2bundle = _pid_to_bundle_map()

    wins = Quartz.CGWindowListCopyWindowInfo(
        Quartz.kCGWindowListExcludeDesktopElements | Quartz.kCGWindowListOptionOnScreenOnly,
        Quartz.kCGNullWindowID,
    )

    bundles = []
    seen = set()
    for w in wins:
        if int(w.get("kCGWindowLayer", 0)) != 0:
            continue
        owner = w.get("kCGWindowOwnerName", "").strip()
        if not owner or owner in excludes:
            continue
        pid = w.get("kCGWindowOwnerPID")
        if pid is None:
            continue
        pid = int(pid)
        bid = pid2bundle.get(pid)
        if not bid:
            continue
        if bid not in seen:
            bundles.append(bid)
            seen.add(bid)

    return bundles



def application_for_process_id(pid):
    return ApplicationServices.AXUIElementCreateApplication(pid)


# get windows for application
def windows_for_application(app):
    err, value = ApplicationServices.AXUIElementCopyAttributeValue(
        app, ApplicationServices.kAXWindowsAttribute, None
    )
    if err != ApplicationServices.kAXErrorSuccess:
        if err == ApplicationServices.kAXErrorNotImplemented:
            print("Attribute not implemented")
        else:
            print("Error retrieving attribute")
        return []
    return uielement.CFAttributeToPyObject(value)


def application_for_bundle(app_bundle, workspace):
    for app in workspace.runningApplications():
        if app_bundle is not None:
            if app.bundleIdentifier() == app_bundle:
                return app
            

# check if application is running
def check_app_running(workspace, app_bundle):
    for app in workspace.runningApplications():
        if app.bundleIdentifier() == app_bundle:
            return True
    return False


# launch the application
def launch_app(bundle_id):
    subprocess.check_call(["open", "-b", bundle_id])
    sleep(3)

def dock_ax_application():
    import AppKit
    workspace = AppKit.NSWorkspace.sharedWorkspace()
    for app in workspace.runningApplications():
        if app.bundleIdentifier() == DOCK_BUNDLE:
            return ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
    return None

def get_visible_windows_for_bundles(bundle_ids: List[str]) -> List[Dict]:
    pid_map, _ = _get_running_apps_for_bundles(bundle_ids)

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
