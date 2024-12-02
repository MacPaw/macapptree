from hashlib import md5
import ApplicationServices
import Foundation
import AppKit
import re
import json
import copy


# convert CF attribute to python object
def CFAttributeToPyObject(attrValue):
    def list_helper(list_value):
        list_builder = []
        for item in list_value:
            list_builder.append(CFAttributeToPyObject(item))
        return list_builder

    def number_helper(number_value):
        success, int_value = Foundation.CFNumberGetValue(
            number_value, Foundation.kCFNumberIntType, None
        )
        if success:
            return int(int_value)

        success, float_value = Foundation.CFNumberGetValue(
            number_value, Foundation.kCFNumberDoubleType, None
        )
        if success:
            return float(float_value)
        return None

    def axuielement_helper(element_value):
        return element_value

    cf_attr_type = Foundation.CFGetTypeID(attrValue)
    cf_type_mapping = {
        Foundation.CFStringGetTypeID(): str,
        Foundation.CFBooleanGetTypeID(): bool,
        Foundation.CFArrayGetTypeID(): list_helper,
        Foundation.CFNumberGetTypeID(): number_helper,
        ApplicationServices.AXUIElementGetTypeID(): axuielement_helper,
    }
    try:
        return cf_type_mapping[cf_attr_type](attrValue)
    except KeyError:
        # did not get a supported CF type. Move on to AX type
        pass

    ax_attr_type = ApplicationServices.AXValueGetType(attrValue)
    ax_type_map = {
        ApplicationServices.kAXValueCGSizeType: Foundation.NSSizeFromString,
        ApplicationServices.kAXValueCGPointType: Foundation.NSPointFromString,
        ApplicationServices.kAXValueCFRangeType: Foundation.NSRangeFromString,
    }
    try:
        extracted_str = re.search("{.*}", attrValue.description()).group()
        return tuple(ax_type_map[ax_attr_type](extracted_str))
    except KeyError:
        return None


# UIElement class which represents accessibility element and all its attributes
class UIElement:

    # calculate hash for the element
    def calculate_hashes(self):
        self.identifier = self.component_hash()
        self.content_identifier = self.children_content_hash(self.children)

    def __init__(self, element, offset_x=0, offset_y=0, max_depth=None, parents_visible_bbox=None):
        # set attributes

        self.ax_element = element
        self.content_identifier = ""
        self.identifier = ""
        self.name = ""
        # self.action_items = []
        self.children = []
        self.description = ""
        self.role_description = ""
        self.value = None
        self.max_depth = max_depth

        # set role
        self.role = element_attribute(element, ApplicationServices.kAXRoleAttribute)
        if self.role is None:
            self.role = "No role"

        # set name
        self.name = element_attribute(element, ApplicationServices.kAXTitleAttribute)
        if self.name is not None:
            self.name = self.name.replace(" ", "_")

        # set enabled
        self.enabled = element_attribute(
            element, ApplicationServices.kAXEnabledAttribute
        )
        if self.enabled is None:
            self.enabled = False

        # set position and size
        position = element_attribute(element, ApplicationServices.kAXPositionAttribute)
        size = element_attribute(element, ApplicationServices.kAXSizeAttribute)
        start_position = element_value(
            position, ApplicationServices.kAXValueCGPointType
        )

        if self.role == "AXWindow":
            offset_x = start_position.x
            offset_y = start_position.y

        self.absolute_position = copy.copy(start_position)
        self.position = start_position
        if self.position is not None:
            self.position.x -= max(0, offset_x)
            self.position.y -= max(0, offset_y)
        self.size = element_value(size, ApplicationServices.kAXValueCGSizeType)

        self._set_bboxes(parents_visible_bbox)

        # set component center
        if start_position is None or self.size is None:
            print("Position is None")
            return
        self.center = (
            start_position.x + offset_x + self.size.width / 2,
            start_position.y + offset_y + self.size.height / 2,
        )

        self.description = element_attribute(
            element, ApplicationServices.kAXDescriptionAttribute
        )
        self.role_description = element_attribute(
            element, ApplicationServices.kAXRoleDescriptionAttribute
        )
        attribute_value = element_attribute(
            element, ApplicationServices.kAXValueAttribute
        )

        # set value
        self.value = attribute_value
        if attribute_value is not None:
            if isinstance(attribute_value, Foundation.NSArray):
                self.value = []
                for value in attribute_value:
                    self.value.append(value)
            if isinstance(attribute_value, ApplicationServices.AXUIElementRef):
                self.value = UIElement(attribute_value, offset_x, offset_y)

        # set children
        if self.max_depth is None or self.max_depth > 0:
            self.children, self.action_items = self._get_children_and_actions(element, start_position, offset_x, offset_y)
        else:
            self.children, self.action_items = [], []

        self.calculate_hashes()

        self.unrolled = False

    def _set_bboxes(self, parents_visible_bbox):
        if not self.position or not self.size:
            self.bbox = None
            self.visible_bbox = None
            return
        self.bbox = [int(self.position.x), 
                     int(self.position.y), 
                     int(self.position.x + self.size.width), 
                     int(self.position.y + self.size.height)]
        if parents_visible_bbox:
            # check if not intersected
            if  self.bbox[0] > parents_visible_bbox[2] or \
                self.bbox[1] > parents_visible_bbox[3] or \
                self.bbox[2] < parents_visible_bbox[0] or \
                self.bbox[3] < parents_visible_bbox[1]:
                self.visible_bbox = None
            else:
                self.visible_bbox = [int(max(self.bbox[0], parents_visible_bbox[0])), 
                                    int(max(self.bbox[1], parents_visible_bbox[1])),
                                    int(min(self.bbox[2], parents_visible_bbox[2])),
                                    int(min(self.bbox[3], parents_visible_bbox[3]))]
        else:
            self.visible_bbox = self.bbox

    def _get_children_and_actions(self, element, start_position, offset_x, offset_y):
        action_items = []
        children_all = []

        # search for all children
        children = element_attribute(element, ApplicationServices.kAXChildrenAttribute)
        error, actions = ApplicationServices.AXUIElementCopyActionNames(element, None)
        if error == 0 and actions is not None and len(actions) > 0:
            action_items = actions

        if children is not None and len(children) > 0:
            # make children structure flat if it is a group and has only one child
            if self.role == "AXGroup" and len(children) == 1:
                child_position = element_attribute(
                    children[0], ApplicationServices.kAXPositionAttribute
                )
                child_position_value = element_value(
                    child_position, ApplicationServices.kAXValueCGPointType
                )
                child_size = element_attribute(
                    children[0], ApplicationServices.kAXSizeAttribute
                )
                child_size_value = element_value(
                    child_size, ApplicationServices.kAXValueCGSizeType
                )
                if (
                        start_position == child_position_value
                        and self.size == child_size_value
                ):
                    children_elements = element_attribute(
                        children[0], ApplicationServices.kAXChildrenAttribute
                    )
                    if children_elements is not None and len(children_elements) > 0:
                        found_children = UIElement.children(
                            children[0], offset_x, offset_y, self.max_depth, self.visible_bbox
                        )
                        children_all = found_children
                    else:
                        children_all = UIElement.children(element, offset_x, offset_y, self.max_depth, self.visible_bbox)
                else:
                    children_all = UIElement.children(element, offset_x, offset_y, self.max_depth, self.visible_bbox)
            else:
                children_all = UIElement.children(element, offset_x, offset_y, self.max_depth, self.visible_bbox)

        children_all = [element for element in children_all if element.position is not None]
        children_all = sorted(
            children_all, key=lambda x: (x.position.y, x.position.x)
        )
        children_all.reverse()

        return children_all, action_items

    def recursive_children(self):
        if len(self.children) == 0:
            children_all, _ = self._get_children_and_actions(self.ax_element, self.position, 0, 0)
        else:
            children_all = self.children
        recursive_children = []
        for child in children_all:
            recursive_children.append(child)
            recursive_children.extend(child.recursive_children())
        return recursive_children

    # calculate hash for the element
    def hash_from_string(self, string):
        if string is None or string == "":
            return ""
        return md5(string.encode()).hexdigest()

    def component_hash(self):
        if self.position is None or self.size is None:
            return ""
        position_string = f"{self.position.x:.0f};{self.position.y:.0f}"
        size_string = f"{self.size.width:.0f};{self.size.height:.0f}"
        enabled_string = str(self.enabled)
        # if self.value is not None:
        #     enabled_string += str(self.value)
        return self.hash_from_string(
            position_string + size_string + enabled_string + self.role
        )

    def content_hash(self, element):
        description = ""
        if element.description is not None:
            description = element.description

        role_description = ""
        if element.role_description is not None:
            role_description = element.role_description

        name = ""
        if element.name is not None:
            name = element.name

        value = ""
        if element.value is not None:
            value = str(element.value)
        return self.hash_from_string(description + role_description + name + value)

    def children_content_hash(self, children):
        if len(children) == 0:
            return ""
        all_content_hashes = []
        all_hashes = []
        for child in children:
            all_content_hashes.append(child.content_identifier)
            all_hashes.append(child.identifier)
        all_content_hashes.sort()
        if len(all_content_hashes) == 0:
            return ""
        content_hash = self.hash_from_string("".join(all_content_hashes))
        content_structure_hash = self.hash_from_string("".join(all_hashes))
        return self.hash_from_string(content_hash.join(content_structure_hash))

    # search for the root window
    @classmethod
    def find_root_element(cls, element):
        role = element_attribute(element, ApplicationServices.kAXRoleAttribute)
        sub_role = element_attribute(element, ApplicationServices.kAXSubroleAttribute)
        if role == "AXWindow" or sub_role == "AXHostingView":
            return element
        else:
            parent = element_attribute(element, ApplicationServices.kAXParentAttribute)
            if parent is not None:
                return cls.find_root_element(parent)
        return None

    # parse children
    @classmethod
    def children(cls, element, offset_x=0, offset_y=0, max_depth=None, visible_bbox=None):
        children = element_attribute(element, ApplicationServices.kAXChildrenAttribute)
        visible_children = element_attribute(
            element, ApplicationServices.kAXVisibleChildrenAttribute
        )
        found_children = []
        if children is not None:
            found_children.extend(children)
        else:
            if visible_children is not None:
                found_children.extend(visible_children)

        result = []
        if max_depth is None or max_depth > 0:
            for child in found_children:
                child = cls(child, offset_x, offset_y, max_depth - 1 if max_depth is not None else None, visible_bbox)
                result.append(child)
        return result

    # to dict
    def to_dict(self):
        def children_to_dict(children):
            result = []
            for child in children:
                result.append(child.to_dict())
            return result

        value = self.value
        if isinstance(value, UIElement):
            value = json.dumps(value.to_dict(), indent=4)
        elif isinstance(value, AppKit.NSDate):
            value = str(value)

        if self.absolute_position is not None:
            absolute_position = f"{self.absolute_position.x:.2f};{self.absolute_position.y:.2f}"
        else:
            absolute_position = ""

        if self.position is not None:
            position = f"{self.position.x:.2f};{self.position.y:.2f}"
        else:
            position = ""

        if self.size is not None:
            size = f"{self.size.width:.0f};{self.size.height:.0f}"
        else:
            size = ""

        return {
            "id": self.identifier,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "role_description": self.role_description,
            "value": value,
            "absolute_position": absolute_position,
            "position": position,
            "size": size,
            "enabled": self.enabled,
            "bbox": self.bbox,
            "visible_bbox": self.visible_bbox,
            "children": children_to_dict(self.children),
        }

    #  additional checks

    # check if element is a button
    def is_button(self) -> bool:
        return self.role == "AXButton"


# get accessibility element attribute
def element_attribute(element, attribute):
    if attribute == ApplicationServices.kAXChildrenAttribute:
        err, value = ApplicationServices.AXUIElementCopyAttributeValues(
            element, attribute, 0, 999, None
        )
        if err == ApplicationServices.kAXErrorSuccess:
            if isinstance(value, Foundation.__NSArrayM):
                return CFAttributeToPyObject(value)
            else:
                return value
    err, value = ApplicationServices.AXUIElementCopyAttributeValue(
        element, attribute, None
    )
    if err == ApplicationServices.kAXErrorSuccess:
        if isinstance(value, Foundation.__NSArrayM):
            return CFAttributeToPyObject(value)
        else:
            return value
    return None


# det accessibility element value
def element_value(element, type):
    err, value = ApplicationServices.AXValueGetValue(element, type, None)
    if err == True:
        return value
    return None


# get accessibility attribute names
def element_attribute_names(element):
    err, value = ApplicationServices.AXUIElementCopyAttributeNames(element, None)
    if err == ApplicationServices.kAXErrorSuccess:
        return value
    return []


# print node with its children and attributes
def print_node(node, level=0):
    # construct name
    name = ""
    if node.name is not None:
        name = f" ({node.name})"
    elif node.description is not None:
        name = f" ({node.description})"
    elif node.value is not None:
        name = f" ({node.value})"
    else:
        name = f" ({node.role_description})"

    name = name.replace("\n", " ")

    # construct role
    role = "No role"
    if node.role is not None:
        role = node.role

    # construct position
    position = ""
    if node.position is not None and node.size is not None:
        position = f" ({node.position.x:.0f};{node.position.y:.0f};{node.size.width:.0f};{node.size.height:.0f})"

    # print node
    print("  " * level + " " + role + position + name)
    for child in node.children:
        print_node(child, level + 1)
