import ApplicationServices
import macapptree.uielement as uielement


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