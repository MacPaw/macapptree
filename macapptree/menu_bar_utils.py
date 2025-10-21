from __future__ import annotations
import os
from typing import Optional, Tuple, List, Dict, Any

import AppKit
import ApplicationServices

import macapptree.apps as apps
from macapptree.uielement import UIElement, element_attribute
from macapptree.window_tools import store_screen_scaling_factor, segment_window_components, propagate_screen_rect
from macapptree.extractor import extract_window
from macapptree.screenshot_app_window import capture_full_screen
from macapptree.screenshot_app_window import crop_screenshot


class MenuBarCapture:
    @staticmethod
    def _menu_bar_tl_rect() -> Tuple[int, int, int, int]:
        screen = AppKit.NSScreen.mainScreen().frame()
        sw, sh = int(screen.size.width), int(screen.size.height)
        thickness = int(AppKit.NSStatusBar.systemStatusBar().thickness())
        return (0, 0, sw, thickness)

    @staticmethod
    def _menubar_ax_for_front_app():
        ws = AppKit.NSWorkspace.sharedWorkspace()
        front = ws.frontmostApplication()
        if not front:
            return None
        ax_app = apps.application_for_process_id(front.processIdentifier())
        try:
            return element_attribute(ax_app, ApplicationServices.kAXMenuBarAttribute)
        except Exception:
            return None

    @staticmethod
    def _menubar_ax_for_system():
        ws = AppKit.NSWorkspace.sharedWorkspace()
        for ra in ws.runningApplications():
            if ra.bundleIdentifier() == "com.apple.SystemUIServer":
                return apps.application_for_process_id(ra.processIdentifier())
        return None

    def capture(
        self,
        max_depth: Optional[int] = None,
        output_screenshot_dir: Optional[str] = None,
    ):
        store_screen_scaling_factor()

        x_tl, y_tl, w, h = self._menu_bar_tl_rect()
        win_rect_tl = [x_tl, y_tl, x_tl + w, y_tl + h]

        roots: List[UIElement] = []
        shot_info = None

        # left (front app) menu
        ax_mb_left = self._menubar_ax_for_front_app()
        if ax_mb_left:
            mb_left = UIElement(
                ax_mb_left,
                max_depth=max_depth,
                parents_visible_bbox=[0, 0, w, h],
            )
            mb_left.app_name = "MenuBar (App)"
            mb_left.window_screen_rect = win_rect_tl
            extract_window(
                mb_left, "front.app.menubar", None,
                perform_hit_test=False, print_nodes=False, max_depth=max_depth
            )
            propagate_screen_rect(mb_left, win_rect_tl)
            roots.append(mb_left)

        # right (system extras)
        ax_sys = self._menubar_ax_for_system()
        if ax_sys:
            try:
                ax_mb_right = element_attribute(ax_sys, ApplicationServices.kAXMenuBarAttribute) or ax_sys
            except Exception:
                ax_mb_right = ax_sys
            mb_right = UIElement(
                ax_mb_right,
                max_depth=max_depth,
                parents_visible_bbox=[0, 0, w, h],
            )
            mb_right.app_name = "MenuBar (System)"
            mb_right.window_screen_rect = win_rect_tl
            extract_window(
                mb_right, "com.apple.SystemUIServer", None,
                perform_hit_test=False, print_nodes=False, max_depth=max_depth
            )
            propagate_screen_rect(mb_right, win_rect_tl)
            roots.append(mb_right)

        if output_screenshot_dir:
            os.makedirs(output_screenshot_dir, exist_ok=True)
            full_path = os.path.join(output_screenshot_dir, "menubar_full.png")
            capture_full_screen(full_path)

        
            crop_path = full_path.replace(".png", "_cropped.png")
            _ = crop_screenshot(full_path, (x_tl, y_tl, w, h), crop_path)

            if roots:
                segment_window_components(roots[0], crop_path)
            shot_info = {
                "app": "menubar",
                "window_name": "MenuBar",
                "cropped_screenshot_path": crop_path,
                "segmented_screenshot_path": crop_path.replace(".png", "_segmented.png"),
            }

        return roots, shot_info
