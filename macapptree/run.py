from PIL import Image
import subprocess
import tempfile
import json
import re


def get_tree(app_bundle):
    tmp_file = tempfile.NamedTemporaryFile(delete=True)
    try:
        subprocess.check_call(["python", "-m", "accessibility.main", "-a", app_bundle, "--oa", tmp_file.name, "--hit-test"])
        return json.load(tmp_file)
    except subprocess.CalledProcessError as e:
        print(f"Failed to extract app accessibility for {app_bundle}. Error: {e}")
    finally:
        tmp_file.close()


def get_tree_screenshot(app_bundle):
    a11y_tmp_file = tempfile.NamedTemporaryFile(delete=True)
    screenshot_tmp_file = tempfile.NamedTemporaryFile(delete=True, suffix=".png")
    try:
        result = subprocess.run(["python", "-m", "accessibility.main", 
                               "-a", app_bundle, 
                               "--oa", a11y_tmp_file.name,
                               "--os", screenshot_tmp_file.name,
                               "--hit-test"], 
                               capture_output=True, text=True)
        json_match = re.search(r'{.*}', result.stdout, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            screenshots_paths_dict = json.loads(json_str)
            croped_img = Image.open(screenshots_paths_dict["croped_screenshot_path"])
            segmented_img = Image.open(screenshots_paths_dict["segmented_screenshot_path"])

            return json.load(a11y_tmp_file), croped_img, segmented_img
        else:
            return json.load(a11y_tmp_file)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Failed to extract app accessibility for {app_bundle}. Error: {e}")
    finally:
        a11y_tmp_file.close()
        screenshot_tmp_file.close()