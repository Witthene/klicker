"""Thin ctypes wrappers around the Win32 calls the clicker needs.

This module doubles as the default backend of ``ClickEngine``: it exposes
``send_click``, ``get_cursor_pos``, ``set_cursor_pos``, ``root_window_at`` and
the precise-timing helpers.
"""

import ctypes
import sys
from ctypes import wintypes as wt

if sys.platform != "win32":
    raise ImportError("Klicker funciona apenas no Windows.")

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
dwmapi = ctypes.WinDLL("dwmapi")
winmm = ctypes.WinDLL("winmm")

ULONG_PTR = ctypes.c_size_t
LRESULT = ctypes.c_ssize_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wt.LONG), ("dy", wt.LONG), ("mouseData", wt.DWORD),
                ("dwFlags", wt.DWORD), ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wt.DWORD), ("wParamL", wt.WORD), ("wParamH", wt.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = [("type", wt.DWORD), ("u", _INPUTUNION)]


class MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("pt", wt.POINT), ("mouseData", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wt.DWORD), ("scanCode", wt.DWORD), ("flags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ULONG_PTR)]


HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wt.WPARAM, wt.LPARAM)


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_int), ("AccentFlags", ctypes.c_int),
                ("GradientColor", wt.DWORD), ("AnimationId", ctypes.c_int)]


class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [("Attrib", ctypes.c_int), ("pvData", ctypes.c_void_p), ("cbData", ctypes.c_size_t)]


INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
BUTTON_FLAGS = {
    "left": (0x0002, 0x0004),
    "right": (0x0008, 0x0010),
    "middle": (0x0020, 0x0040),
    "x1": (0x0080, 0x0100),
    "x2": (0x0080, 0x0100),
}
XBUTTON_DATA = {"x1": 1, "x2": 2}
MOUSEEVENTF_WHEEL, MOUSEEVENTF_HWHEEL = 0x0800, 0x1000
MOUSEEVENTF_MOVE, MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_ABSOLUTE = 0x0001, 0x4000, 0x8000
SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN, SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN = 76, 77, 78, 79
KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, KEYEVENTF_SCANCODE = 0x1, 0x2, 0x8
WH_KEYBOARD_LL, WH_MOUSE_LL = 13, 14
WM_QUIT = 0x0012
WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP = 0x100, 0x101, 0x104, 0x105
WM_MOUSEMOVE, WM_MOUSEWHEEL, WM_MOUSEHWHEEL = 0x200, 0x20A, 0x20E
MOUSE_BUTTON_MESSAGES = {
    0x201: ("down", "left"), 0x202: ("up", "left"),
    0x204: ("down", "right"), 0x205: ("up", "right"),
    0x207: ("down", "middle"), 0x208: ("up", "middle"),
    0x20B: ("down", "x"), 0x20C: ("up", "x"),
}
LLMHF_INJECTED, LLKHF_EXTENDED, LLKHF_INJECTED = 0x1, 0x1, 0x10
VK_PAUSE, VK_SCROLL = 0x13, 0x91
INJECTED_TAG = 0x47434C4B  # "GCLK", lets other tools recognise our synthetic input
SM_SWAPBUTTON = 23
GA_ROOT = 2
WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
HWND_TOPMOST, HWND_NOTOPMOST = -1, -2
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
WCA_ACCENT_POLICY = 19
ACCENT_DISABLED, ACCENT_ENABLE_ACRYLICBLURBEHIND = 0, 4
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2

user32.SendInput.argtypes = (wt.UINT, ctypes.POINTER(INPUT), ctypes.c_int)
user32.SendInput.restype = wt.UINT
user32.GetCursorPos.argtypes = (ctypes.POINTER(wt.POINT),)
user32.GetCursorPos.restype = wt.BOOL
user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
user32.SetCursorPos.restype = wt.BOOL
user32.WindowFromPoint.argtypes = (wt.POINT,)
user32.WindowFromPoint.restype = wt.HWND
user32.GetAncestor.argtypes = (wt.HWND, wt.UINT)
user32.GetAncestor.restype = wt.HWND
user32.GetSystemMetrics.argtypes = (ctypes.c_int,)
user32.GetSystemMetrics.restype = ctypes.c_int
user32.RegisterHotKey.argtypes = (wt.HWND, ctypes.c_int, wt.UINT, wt.UINT)
user32.RegisterHotKey.restype = wt.BOOL
user32.UnregisterHotKey.argtypes = (wt.HWND, ctypes.c_int)
user32.UnregisterHotKey.restype = wt.BOOL
user32.MapVirtualKeyW.argtypes = (wt.UINT, wt.UINT)
user32.MapVirtualKeyW.restype = wt.UINT
user32.GetKeyNameTextW.argtypes = (wt.LONG, wt.LPWSTR, ctypes.c_int)
user32.GetKeyNameTextW.restype = ctypes.c_int
user32.SetWindowPos.argtypes = (wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT)
user32.SetWindowPos.restype = wt.BOOL
user32.SetWindowsHookExW.argtypes = (ctypes.c_int, HOOKPROC, wt.HINSTANCE, wt.DWORD)
user32.SetWindowsHookExW.restype = wt.HHOOK
user32.UnhookWindowsHookEx.argtypes = (wt.HHOOK,)
user32.UnhookWindowsHookEx.restype = wt.BOOL
user32.CallNextHookEx.argtypes = (wt.HHOOK, ctypes.c_int, wt.WPARAM, wt.LPARAM)
user32.CallNextHookEx.restype = LRESULT
user32.GetMessageW.argtypes = (ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT)
user32.GetMessageW.restype = wt.BOOL
user32.PostThreadMessageW.argtypes = (wt.DWORD, wt.UINT, wt.WPARAM, wt.LPARAM)
user32.PostThreadMessageW.restype = wt.BOOL
user32.GetForegroundWindow.restype = wt.HWND
kernel32.GetCurrentThreadId.restype = wt.DWORD
kernel32.GetModuleHandleW.argtypes = (wt.LPCWSTR,)
kernel32.GetModuleHandleW.restype = wt.HMODULE
dwmapi.DwmSetWindowAttribute.argtypes = (wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD)
dwmapi.DwmSetWindowAttribute.restype = ctypes.c_long


# --- Mouse -------------------------------------------------------------------

def send_click(button="left", count=1):
    """Press and release ``button`` ``count`` times in one atomic SendInput call."""
    # Like AutoIt's PRIMARY/SECONDARY handling: SendInput talks about physical
    # buttons, so honour the "swap mouse buttons" accessibility setting.
    if button in ("left", "right") and user32.GetSystemMetrics(SM_SWAPBUTTON):
        button = "right" if button == "left" else "left"
    down, up = BUTTON_FLAGS[button]
    n = 2 * count
    events = (INPUT * n)()
    for i in range(n):
        events[i].type = INPUT_MOUSE
        events[i].mi.dwFlags = down if i % 2 == 0 else up
        events[i].mi.dwExtraInfo = INJECTED_TAG
    if user32.SendInput(n, events, ctypes.sizeof(INPUT)) != n:
        raise ctypes.WinError(ctypes.get_last_error())


def _send(events):
    n = len(events)
    arr = (INPUT * n)(*events)
    if user32.SendInput(n, arr, ctypes.sizeof(INPUT)) != n:
        raise ctypes.WinError(ctypes.get_last_error())


def _mouse_input(flags, data=0):
    event = INPUT(type=INPUT_MOUSE)
    event.mi.dwFlags = flags
    event.mi.mouseData = data & 0xFFFFFFFF
    event.mi.dwExtraInfo = INJECTED_TAG
    return event


def _move_input(x, y):
    """An absolute move as real mouse input, mapped onto the whole virtual desktop."""
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = max(2, user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
    height = max(2, user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
    event = _mouse_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK)
    event.mi.dx = round((x - left) * 65535 / (width - 1))
    event.mi.dy = round((y - top) * 65535 / (height - 1))
    return event


def send_mouse_button(button, down):
    """Replay a recorded button exactly as captured (no swap correction)."""
    flags = BUTTON_FLAGS[button][0 if down else 1]
    _send([_mouse_input(flags, XBUTTON_DATA.get(button, 0))])


def click_at(button, down, x, y):
    """Move there and press/release in one SendInput batch, so the target sees both."""
    flags = BUTTON_FLAGS[button][0 if down else 1]
    _send([_move_input(x, y), _mouse_input(flags, XBUTTON_DATA.get(button, 0))])
    user32.SetCursorPos(int(x), int(y))


def send_wheel(delta, horizontal=False):
    _send([_mouse_input(MOUSEEVENTF_HWHEEL if horizontal else MOUSEEVENTF_WHEEL, delta)])


def send_key(vk, scan, extended, up):
    event = INPUT(type=INPUT_KEYBOARD)
    event.ki.wVk = 0 if scan else vk
    event.ki.wScan = scan
    # Scan codes are what most games read (DirectInput / raw input); fall back to the VK.
    event.ki.dwFlags = ((KEYEVENTF_SCANCODE if scan else 0) | (KEYEVENTF_EXTENDEDKEY if extended else 0)
                        | (KEYEVENTF_KEYUP if up else 0))
    event.ki.dwExtraInfo = INJECTED_TAG
    _send([event])


def play_event(event):
    """Execute one recorded macro event (see ``macro.py`` for the format)."""
    kind = event[1]
    if kind == "move":
        set_cursor_pos(event[2], event[3])
    elif kind in ("down", "up"):
        click_at(event[2], kind == "down", event[3], event[4])
    elif kind in ("wheel", "hwheel"):
        set_cursor_pos(event[3], event[4])
        send_wheel(event[2], kind == "hwheel")
    elif kind in ("kdown", "kup"):
        send_key(event[2], event[3], event[4], kind == "kup")


def get_cursor_pos():
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def set_cursor_pos(x, y):
    # SetCursorPos alone moves the pointer without producing mouse input, so games
    # that read raw input never see the move; send a real move first, then snap
    # to the exact pixel.
    _send([_move_input(x, y)])
    user32.SetCursorPos(int(x), int(y))


def root_window_at(x, y):
    hwnd = user32.WindowFromPoint(wt.POINT(int(x), int(y)))
    if not hwnd:
        return 0
    return user32.GetAncestor(hwnd, GA_ROOT) or 0


def begin_precise_timing():
    winmm.timeBeginPeriod(1)


def end_precise_timing():
    winmm.timeEndPeriod(1)


# --- Hotkeys -----------------------------------------------------------------

_MODIFIER_NAMES = ((MOD_CONTROL, "Ctrl"), (MOD_ALT, "Alt"), (MOD_SHIFT, "Shift"), (MOD_WIN, "Win"))


def register_hotkey(hwnd, hotkey_id, vk, mods):
    return bool(user32.RegisterHotKey(wt.HWND(hwnd), hotkey_id, mods | MOD_NOREPEAT, vk))


def unregister_hotkey(hwnd, hotkey_id):
    user32.UnregisterHotKey(wt.HWND(hwnd), hotkey_id)


def vk_name(vk):
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    scan = user32.MapVirtualKeyW(vk, 0)
    # Keys in the "extended" block need bit 24 or Windows names the numpad twin.
    if vk in (0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x2D, 0x2E, 0x6F, 0x90):
        scan |= 0x100
    buf = ctypes.create_unicode_buffer(64)
    if scan and user32.GetKeyNameTextW(scan << 16, buf, 64):
        return buf.value.title()
    return f"0x{vk:02X}"


def hotkey_text(vk, mods):
    parts = [name for flag, name in _MODIFIER_NAMES if mods & flag]
    parts.append(vk_name(vk))
    return " + ".join(parts)


# --- Window chrome -----------------------------------------------------------

def set_acrylic(hwnd, enabled, tint=(0, 0, 0, 0)):
    """Blur whatever is behind the window (Windows 10 1803+). Returns success."""
    try:
        fn = user32.SetWindowCompositionAttribute
    except AttributeError:
        return False
    fn.argtypes = (wt.HWND, ctypes.POINTER(WINDOWCOMPOSITIONATTRIBDATA))
    fn.restype = wt.BOOL
    r, g, b, a = tint
    policy = ACCENT_POLICY(
        ACCENT_ENABLE_ACRYLICBLURBEHIND if enabled else ACCENT_DISABLED,
        2 if enabled else 0,
        (a << 24) | (b << 16) | (g << 8) | r,  # ABGR
        0,
    )
    data = WINDOWCOMPOSITIONATTRIBDATA(
        WCA_ACCENT_POLICY, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p), ctypes.sizeof(policy))
    return bool(fn(wt.HWND(hwnd), ctypes.byref(data)))


def set_round_corners(hwnd):
    pref = ctypes.c_int(DWMWCP_ROUND)
    dwmapi.DwmSetWindowAttribute(wt.HWND(hwnd), DWMWA_WINDOW_CORNER_PREFERENCE,
                                 ctypes.byref(pref), ctypes.sizeof(pref))


def set_topmost(hwnd, enabled):
    user32.SetWindowPos(wt.HWND(hwnd), wt.HWND(HWND_TOPMOST if enabled else HWND_NOTOPMOST),
                        0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)
