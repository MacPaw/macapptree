from PIL import Image
import subprocess
import tempfile
import json
import re
import os


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