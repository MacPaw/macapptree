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
) -> List[Tuple[int, str, str]]:  # Changed return type to List
    result = []  # Initialize a list to store results
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
) -> List[Tuple[int, str]]:  # Changed return type to List[Tuple[int, str]]
    windows = get_window_info()
    parent = parent.lower()
    result = []  # Initialize a list to store results

    for num, owner, window_name, (x, y, width, height) in gen_ids_from_info(windows):
        if parent == owner.lower():
            if window_name == STATUS_BAR_WINDOW_IDENTIFIER:
                print(f"Skipping status bar window: {num}")
            else:
                window_name = window_name.replace(" ", "_")
                result.append((num, window_name, (x, y, width, height)))

    return result  # Return the list of window IDs


# take screenshot
def take_screenshot(window: int, filename: str, output_folder: str = None) -> str:
    if output_folder:
        filename = os.path.join(output_folder, filename)

        # create the output folder if it does not exist
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

    # Load the screenshot image
    screenshot = Image.open(image_path)

    # Unpack the window coordinates (left, top, width, height)
    left, top, width, height = window_coords

    # Calculate the right and bottom coordinates
    right = left + width
    bottom = top + height

    # Crop the image using the window's bounds
    cropped_image = screenshot.crop((int(left * backing_scale_factor),
                                     int(top * backing_scale_factor),
                                     int(right * backing_scale_factor),
                                     int(bottom * backing_scale_factor)))

    # Save the cropped image
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
        
        if decoded_name == decoded_window_name or decoded_window_name == app_name or window_name == "":  # Sometimes popup windows have an empty name
            return identifier, decoded_name, window_coords
    
    # if nothing found, try again with 'startwith'
    for identifier, name, window_coords in windows:
        decoded_name = unidecode(name)
        
        if decoded_window_name.startswith(decoded_name):  # Sometimes popup windows have an empty name
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
def gen_windows(application_name: str) -> List[int]:  # Changed return type to List[int]
    windows = list(gen_window_ids(application_name))  # Convert generator to list
    if not windows:  # Check if the list is empty
        print(f"Window with parent {application_name} not found.")
    return windows  # Return the list of windows


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
