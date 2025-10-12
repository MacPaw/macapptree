import ApplicationServices
import macapptree.uielement as uielement
import subprocess
from time import sleep
import Quartz
import AppKit


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
        owner = (w.get("kCGWindowOwnerName") or "").strip()
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
        if app.bundleIdentifier() == "com.apple.dock":
            return ApplicationServices.AXUIElementCreateApplication(app.processIdentifier())
    return None

