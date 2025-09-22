#!/usr/bin/env python3
# capture_coords.py
# Interactive utility to capture absolute and relative coords for UI elements (Firefox window aware)
# Requires: pip install pyautogui pygetwindow

import json
import time
import sys
from typing import Dict, Tuple, List, Any

try:
    import pygetwindow as gw
    import pyautogui
except Exception as e:
    print("Missing dependency. Install with: pip install pygetwindow pyautogui")
    raise

OUT_FILE = "coords.json"


def find_firefox_window() -> Any:
    """Try to find a Firefox window. If none found, return None."""
    wins = [w for w in gw.getWindowsWithTitle("") if "Mozilla Firefox" in w.title]
    if not wins:
        return None
    win = wins[0]
    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.3)
    return win


def print_win_info(win):
    if win is None:
        print("Firefox window not found (will capture screen coords absolute).")
    else:
        print(f"Found Firefox window: '{win.title}' at ({win.left},{win.top}) size {win.width}x{win.height}")


def prompt_capture_point(prompt: str) -> Tuple[int, int]:
    input(f">>> Move your mouse over {prompt} and press ENTER in this terminal to capture position...")
    x, y = pyautogui.position()
    print(f"Captured: ({x}, {y})")
    return int(x), int(y)


def capture_points_for_labels(labels: List[str], relative_to_window: bool = True) -> Dict[str, dict]:
    win = find_firefox_window() if relative_to_window else None
    print_win_info(win)
    data = {}
    for label in labels:
        x, y = prompt_capture_point(label)
        entry = {"x": x, "y": y}
        if win:
            # compute relative coordinates (0..1)
            rx = (x - win.left) / win.width
            ry = (y - win.top) / win.height
            entry["rel_x"] = round(rx, 6)
            entry["rel_y"] = round(ry, 6)
        data[label] = entry
    return data


def capture_region(relative_to_window: bool = True) -> Dict[str, Any]:
    win = find_firefox_window() if relative_to_window else None
    print("Capture TOP-LEFT of region.")
    tlx, tly = prompt_capture_point("region TOP-LEFT")
    print("Capture BOTTOM-RIGHT of region.")
    brx, bry = prompt_capture_point("region BOTTOM-RIGHT")
    left = min(tlx, brx)
    top = min(tly, bry)
    width = abs(brx - tlx)
    height = abs(bry - tly)
    region = {
        "left": int(left),
        "top": int(top),
        "width": int(width),
        "height": int(height)
    }
    if win:
        region["rel_left"] = round((left - win.left) / win.width, 6)
        region["rel_top"] = round((top - win.top) / win.height, 6)
        region["rel_width"] = round(region["width"] / win.width, 6)
        region["rel_height"] = round(region["height"] / win.height, 6)
    print("Captured region:", region)
    return region


def save_coords(obj: dict, filename: str = OUT_FILE):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    print(f"[saved] {filename}")


def load_coords(filename: str = OUT_FILE) -> dict:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def test_clicks_from_coords(coords: dict, delay_between=1.0):
    win = find_firefox_window()
    print_win_info(win)
    if not coords:
        print("No coords loaded.")
        return
    keys = [k for k in coords.keys() if k != "script_region"]
    print("Will test click keys:", keys)
    time.sleep(1.0)
    for k in keys:
        v = coords[k]
        if "rel_x" in v and win:
            x = int(win.left + v["rel_x"] * win.width)
            y = int(win.top + v["rel_y"] * win.height)
        else:
            x = v["x"]
            y = v["y"]
        print(f"Clicking {k} at ({x},{y})")
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        time.sleep(delay_between)


def main_menu():
    print("=== Coordinate Capture Utility ===")
    print("Options:")
    print("  1 - Display live mouse position (useful for quick readout)")
    print("  2 - Interactive capture labeled points (start_campaign, im_ready, ...)")
    print("  3 - Capture a rectangular region (top-left then bottom-right)")
    print("  4 - Load coords.json and test clicks")
    print("  5 - Show current coords.json")
    print("  6 - Clear coords.json")
    print("  0 - Exit")
    while True:
        cmd = input("Choose option: ").strip()
        if cmd == "0":
            print("Exit.")
            break
        elif cmd == "1":
            print("Move the mouse; press Ctrl+C to stop.")
            try:
                pyautogui.displayMousePosition()
            except KeyboardInterrupt:
                print("\nStopped live display.")
        elif cmd == "2":
            print("Enter labels separated by comma, or press Enter to use default set.")
            s = input("Labels (default: start_campaign,im_ready,start_recording,stop_recording,submit_recording): ").strip()
            if not s:
                labels = ["start_campaign", "im_ready", "start_recording", "stop_recording", "submit_recording"]
            else:
                labels = [t.strip() for t in s.split(",") if t.strip()]
            use_win = input("Relative to Firefox window? (y/n, default y): ").strip().lower() != "n"
            new = load_coords()
            captured = capture_points_for_labels(labels, relative_to_window=use_win)
            new.update(captured)
            save_coords(new)
        elif cmd == "3":
            use_win = input("Relative to Firefox window? (y/n, default y): ").strip().lower() != "n"
            new = load_coords()
            region = capture_region(relative_to_window=use_win)
            new["script_region"] = region
            save_coords(new)
        elif cmd == "4":
            coords = load_coords()
            if not coords:
                print("coords.json empty or missing.")
                continue
            print("Loaded keys:", list(coords.keys()))
            test_clicks_from_coords(coords)
        elif cmd == "5":
            coords = load_coords()
            print(json.dumps(coords, indent=2, ensure_ascii=False))
        elif cmd == "6":
            confirm = input("Really clear coords.json? (y/N): ").strip().lower()
            if confirm == "y":
                save_coords({}, OUT_FILE)
        else:
            print("Unknown option.")


if __name__ == "__main__":
    main_menu()
