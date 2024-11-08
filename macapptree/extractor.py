from macapptree.uielement import UIElement
import AppKit
import ApplicationServices
import macapptree.uielement as uielement
import macapptree.files as files
import macapptree.window_tools as window_tools


# perform a hit test on the specified point
def hit_test(point, window_element):
    window_point = window_tools.convert_point_to_window(point, window_element.position)
    system_component = ApplicationServices.AXUIElementCreateSystemWide()
    err, value = ApplicationServices.AXUIElementCopyElementAtPosition(
        system_component, window_point.x, window_point.y, None
    )
    if err == ApplicationServices.kAXErrorSuccess:
        return value
    return None


def extract_with_hit_test(window, app_bundle, output_file, print_nodes, max_depth):
    window_offset_x = window.position.x
    window_offset_y = window.position.y

    print("Parsing window using hit test")
    point = AppKit.NSMakePoint(window_offset_x + 50, window_offset_y + 50)
    group_element = hit_test(point, window)

    if group_element is None:
        print("Hit test failed")
        return False

    # find the root window
    found_root_element = UIElement.find_root_element(group_element)
    root_element = UIElement(found_root_element, window_offset_x, window_offset_y, max_depth)
    parent_window = uielement.element_attribute(
        found_root_element, ApplicationServices.kAXWindowAttribute
    )
    if parent_window is not None:
        parent_window_element = UIElement(
            parent_window, window_offset_x, window_offset_y, max_depth
        )

        if window_tools.windows_are_equal(window, parent_window_element):
            element_not_found = True
            for child in window.children:
                if (
                    child.identifier == root_element.identifier
                    and child.content_identifier == root_element.content_identifier
                ):
                    element_not_found = False
            if element_not_found:
                window.children.append(root_element)
                window.calculate_hashes()
    else:
        window.children.append(root_element)
        window.calculate_hashes()

    # print the node with its children and attributes
    if print_nodes:
        uielement.print_node(root_element)

    files.store_data_to_file(window, output_file)

    return True



# extract the window
def extract_window(
    window, app_bundle, output_file, perform_hit_test, print_nodes, max_depth
) -> bool:
    if window is None:
        return False

    if perform_hit_test:
        print("Parsing window using hit test")
        return extract_with_hit_test(window, app_bundle, output_file, print_nodes, max_depth)

    else:
        print("Parsing regular window structure")
        files.store_data_to_file(window, output_file)

        return True


