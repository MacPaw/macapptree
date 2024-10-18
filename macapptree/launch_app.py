import macapptree.apps as apps
import argparse
import AppKit


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Parse -a argument")
    arg_parser.add_argument("-a", type=str, help="The application bundle identifier")

    args = arg_parser.parse_args()
    app_bundle = args.a

    workspace = AppKit.NSWorkspace.sharedWorkspace()
    if not apps.check_app_running(workspace, app_bundle):
        apps.launch_app(app_bundle)
