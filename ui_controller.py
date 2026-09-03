# -*- coding: utf-8 -*-
"""
ui_controller.py
================
Native Windows UIAutomation & Accessibility Control Engine for Real Jarvis.
Directly interacts with native desktop controls (Buttons, Edits, Menus, Tabs, TreeViews)
across any Windows application (VS Code, File Explorer, Excel, Word, Chrome, Settings)
without relying on pixel coordinates.
"""

import time
import re

try:
    import uiautomation as auto
    import win32gui
    import win32con
    import win32process
    import pyautogui
except ImportError:
    auto = None
    win32gui = None
    win32con = None
    win32process = None
    pyautogui = None


def is_available() -> bool:
    return auto is not None and win32gui is not None


def get_foreground_control():
    """Returns root UI element for the current active/foreground window."""
    if not auto or not win32gui:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            return auto.ControlFromHandle(hwnd)
    except Exception as e:
        print(f"[get_foreground_control error: {e}]")
    return None


def get_window_by_title(title_query: str):
    """Finds top-level window by title substring."""
    if not auto:
        return None
    try:
        return auto.WindowControl(searchDepth=1, SubName=title_query)
    except Exception:
        return None


def click_native_element(element_name: str, control_type: str = None, window_title: str = None) -> dict:
    """
    Finds native UI element by name (and optional control_type like Button, MenuItem, TabItem, Hyperlink)
    and clicks/invokes it directly.
    """
    if not is_available():
        return {"success": False, "message": "UI Automation library not available."}

    root = get_window_by_title(window_title) if window_title else get_foreground_control()
    if not root:
        root = auto.GetRootControl()

    target_name = element_name.strip()
    print(f"[ui_controller] Searching for native element: '{target_name}' (type={control_type})")

    try:
        # Search strategy 1: exact or partial name match across children
        control = None
        
        # Build search kwargs
        kwargs = {"searchDepth": 8}
        if control_type:
            kwargs["ControlType"] = getattr(auto.ControlType, control_type + "Control", None)
            # Remove None if not found
            if kwargs["ControlType"] is None:
                del kwargs["ControlType"]

        # Try searching by SubName
        control = root.Control(SubName=target_name, **kwargs)
        if not control.Exists(maxSearchSeconds=1.5):
            # Try case-insensitive search by traversing controls
            def _find_match(ctrl, depth):
                if depth > 7:
                    return None
                try:
                    name = ctrl.Name
                    if name and target_name.lower() in name.lower():
                        return ctrl
                    for child in ctrl.GetChildren():
                        res = _find_match(child, depth + 1)
                        if res:
                            return res
                except Exception:
                    pass
                return None
            
            control = _find_match(root, 0)

        if control and control.Exists(0.1):
            name = control.Name
            c_type = control.ControlTypeName
            
            # Try native invoke pattern first (fastest and doesn't require moving mouse)
            invoked = False
            try:
                invoke_pat = control.GetInvokePattern()
                if invoke_pat:
                    invoke_pat.Invoke()
                    invoked = True
            except Exception:
                pass

            if not invoked:
                try:
                    toggle_pat = control.GetTogglePattern()
                    if toggle_pat:
                        toggle_pat.Toggle()
                        invoked = True
                except Exception:
                    pass

            if not invoked:
                # Fallback to coordinate click on center of native bounding rect
                control.Click()

            return {
                "success": True,
                "message": f"Successfully clicked native {c_type} '{name}'."
            }
        else:
            return {
                "success": False,
                "message": f"Native element '{target_name}' nahi mila active window me."
            }

    except Exception as e:
        print(f"[click_native_element error: {e}]")
        return {"success": False, "message": f"Error clicking element: {str(e)}"}


def set_native_edit_text(element_name: str, value: str, window_title: str = None, press_enter: bool = False) -> dict:
    """
    Locates native text/edit input box and writes text directly.
    """
    if not is_available():
        return {"success": False, "message": "UI Automation not available."}

    root = get_window_by_title(window_title) if window_title else get_foreground_control()
    if not root:
        root = auto.GetRootControl()

    try:
        edit_ctrl = root.EditControl(searchDepth=8, SubName=element_name) if element_name else root.EditControl(searchDepth=6)
        if not edit_ctrl.Exists(maxSearchSeconds=1.5):
            # Fallback search any edit control
            edit_ctrl = root.EditControl(searchDepth=6)

        if edit_ctrl and edit_ctrl.Exists(0.5):
            edit_ctrl.SetFocus()
            time.sleep(0.1)
            
            # Try ValuePattern
            try:
                val_pat = edit_ctrl.GetValuePattern()
                if val_pat:
                    val_pat.SetValue(value)
                else:
                    edit_ctrl.SendKeys(value)
            except Exception:
                edit_ctrl.SendKeys(value)

            if press_enter:
                time.sleep(0.1)
                auto.SendKeys("{Enter}")

            return {
                "success": True,
                "message": f"Typed '{value}' into {edit_ctrl.Name or 'Input field'}."
            }
        else:
            return {
                "success": False,
                "message": "Input edit field nahi mila."
            }
    except Exception as e:
        return {"success": False, "message": f"Type error: {str(e)}"}


def list_clickable_elements(window_title: str = None, limit: int = 15) -> list:
    """
    Returns a list of all visible native interactive elements in active window
    (buttons, menus, links, edits, tabs).
    """
    if not is_available():
        return []

    root = get_window_by_title(window_title) if window_title else get_foreground_control()
    if not root:
        return []

    elements = []
    try:
        def _traverse(ctrl, depth):
            if depth > 6 or len(elements) >= limit:
                return
            try:
                name = (ctrl.Name or "").strip()
                c_type = ctrl.ControlTypeName
                
                # Check interactive control types
                if name and c_type in ("ButtonControl", "MenuItemControl", "TabItemControl", 
                                      "HyperlinkControl", "CheckBoxControl", "RadioButtonControl", "EditControl"):
                    c_short = c_type.replace('Control', '')
                    elements.append(f"[{c_short}] '{name}'")
                
                for child in ctrl.GetChildren():
                    _traverse(child, depth + 1)
            except Exception:
                pass

        _traverse(root, 0)
    except Exception as e:
        print(f"[list_clickable_elements error: {e}]")

    return elements[:limit]


def arrange_window(action: str, window_title: str = None) -> dict:
    """
    Window positioning and layout management:
    - maximize, minimize, restore, snap_left, snap_right, center
    """
    if not win32gui or not win32con:
        return {"success": False, "message": "win32gui not available"}

    try:
        hwnd = None
        if window_title:
            def _find_hw(h, _):
                nonlocal hwnd
                if win32gui.IsWindowVisible(h) and window_title.lower() in win32gui.GetWindowText(h).lower():
                    hwnd = h
            win32gui.EnumWindows(_find_hw, None)
        else:
            hwnd = win32gui.GetForegroundWindow()

        if not hwnd:
            return {"success": False, "message": "Window nahi mili."}

        title = win32gui.GetWindowText(hwnd)

        if action == "maximize":
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return {"success": True, "message": f"{title} maximize kar diya."}
        elif action == "minimize":
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return {"success": True, "message": f"{title} minimize kar diya."}
        elif action == "restore":
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return {"success": True, "message": f"{title} restore kar diya."}
        elif action == "snap_left":
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            win32gui.SetForegroundWindow(hwnd)
            pyautogui.hotkey('win', 'left')
            return {"success": True, "message": f"{title} left side snap kar diya."}
        elif action == "snap_right":
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.1)
            win32gui.SetForegroundWindow(hwnd)
            pyautogui.hotkey('win', 'right')
            return {"success": True, "message": f"{title} right side snap kar diya."}

        return {"success": False, "message": f"Unknown window action '{action}'."}
    except Exception as e:
        return {"success": False, "message": f"Window arrange error: {str(e)}"}
