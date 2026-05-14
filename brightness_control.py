"""
WiZ Light Brightness Control — Shift + Volume Knob
===================================================
- Shift + Volume Up/Down  → brightness naik/turun
- Volume tanpa Shift      → volume sistem normal

Requirements:
    python -m pip install keyboard pywizlight

Jalankan sebagai Administrator di Windows.
Auto-start: python brightness_control.py --install
Hapus     : python brightness_control.py --uninstall
"""

import asyncio
import ctypes
import logging
import os
import sys
import time

import keyboard
from pywizlight import wizlight, PilotBuilder
from pywizlight.exceptions import WizLightConnectionError, WizLightTimeOutError

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiz.log")
handlers = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
if sys.stdout and sys.stdout.isatty():
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=handlers,
)
bright_log = logging.getLogger("bright")
bright_log.setLevel(logging.INFO)
if sys.stdout and sys.stdout.isatty():
    bright_log.addHandler(logging.StreamHandler(sys.stdout))
    bright_log.propagate = False

logger = logging.getLogger(__name__)

# ===================
# KONFIGURASI
# ===================

LIGHT_IP        = "YOUR_WIZ_LIGHT_IP" # Ganti dengan IP lampu WiZ Anda
BRIGHTNESS_STEP = 36 # Naik/turun sensitivitas per klik (255/7)
DEBOUNCE_S      = 0.08
RECONNECT_S     = 10

SC_VOLUME_UP   = -175
SC_VOLUME_DOWN = -174
SC_SHIFT_L     = 42
SC_SHIFT_R     = 54

VK_VOLUME_UP   = 0xAF
VK_VOLUME_DOWN = 0xAE

# ===================
# Win32 SendInput
# ===================

_user32 = ctypes.windll.user32
_KEYEVENTF_KEYUP = 0x0002
_INPUT_KEYBOARD  = 1

class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk",         ctypes.c_ushort),
        ("wScan",       ctypes.c_ushort),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type",    ctypes.c_ulong),
        ("ki",      _KEYBDINPUT),
        ("padding", ctypes.c_ubyte * 8),
    ]

def _build_vk_inputs(vk: int):
    arr = (_INPUT * 2)()
    for i, flags in enumerate([0, _KEYEVENTF_KEYUP]):
        arr[i].type   = _INPUT_KEYBOARD
        arr[i].ki.wVk = vk
        arr[i].ki.dwFlags = flags
    return arr

_VOL_UP_INPUTS   = _build_vk_inputs(VK_VOLUME_UP)
_VOL_DOWN_INPUTS = _build_vk_inputs(VK_VOLUME_DOWN)
_INPUT_SIZE      = ctypes.sizeof(_INPUT)

def _send_volume(up: bool):
    inputs = _VOL_UP_INPUTS if up else _VOL_DOWN_INPUTS
    _user32.SendInput(2, inputs, _INPUT_SIZE)


# ===================
# Controller
# ===================

class BrightnessController:

    def __init__(self):
        self.light              = wizlight(LIGHT_IP)
        self.current_brightness = 128
        self._last_cmd          = 0.0
        self.is_connected       = False
        self._loop              = None
        self._shift             = False
        self._sending           = False

    async def _connect(self) -> bool:
        try:
            state = await self.light.updateState()
            if state:
                self.is_connected       = True
                self.current_brightness = state.get_brightness() or 128
                bright_log.info(f"✅ Terhubung ke {LIGHT_IP}")
                return True
        except (WizLightConnectionError, WizLightTimeOutError):
            pass
        self.is_connected = False
        return False

    async def _reconnect_loop(self):
        while True:
            await asyncio.sleep(RECONNECT_S)
            if not self.is_connected:
                bright_log.info("🔄 Mencoba reconnect...")
                await self._connect()

    async def _update(self, step: int) -> None:
        if not self.is_connected:
            return

        now = time.monotonic()
        if now - self._last_cmd < DEBOUNCE_S:
            return
        self._last_cmd = now

        self.current_brightness = max(0, min(255, self.current_brightness + step))

        try:
            await self.light.turn_on(PilotBuilder(brightness=self.current_brightness))
            if sys.stdout and sys.stdout.isatty():
                pct    = int(self.current_brightness / 255 * 100)
                filled = int(20 * pct / 100)
                bar    = "█" * filled + "░" * (20 - filled)
                bright_log.info(f"💡 [{bar}] {pct}%")
        except (WizLightConnectionError, WizLightTimeOutError):
            logger.warning("Koneksi putus, akan reconnect...")
            self.is_connected = False

    def _schedule(self, step: int):
        asyncio.run_coroutine_threadsafe(self._update(step), self._loop)

    def _on_key(self, event) -> bool:
        sc = event.scan_code

        if sc == SC_SHIFT_L or sc == SC_SHIFT_R:
            self._shift = event.event_type == keyboard.KEY_DOWN
            return True

        if sc != SC_VOLUME_UP and sc != SC_VOLUME_DOWN:
            return True

        if event.event_type != keyboard.KEY_DOWN:
            return True

        if self._sending:
            return True

        if self._shift:
            self._schedule(+BRIGHTNESS_STEP if sc == SC_VOLUME_UP else -BRIGHTNESS_STEP)
        else:
            self._sending = True
            _send_volume(sc == SC_VOLUME_UP)
            self._sending = False

        return False

    async def run(self):
        self._loop = asyncio.get_running_loop()

        if not await self._connect():
            logger.error(f"Tidak bisa terhubung ke {LIGHT_IP}. Reconnect otomatis tiap {RECONNECT_S}s.")

        keyboard.hook(self._on_key, suppress=True)
        keyboard.add_hotkey("ctrl+up",   lambda: self._schedule(+BRIGHTNESS_STEP))
        keyboard.add_hotkey("ctrl+down", lambda: self._schedule(-BRIGHTNESS_STEP))

        if sys.stdout and sys.stdout.isatty():
            print()
            print("=" * 55)
            print("🔌  WiZ BRIGHTNESS CONTROL — aktif")
            print("=" * 55)
            print(f"📍  IP Lampu   : {LIGHT_IP}")
            print(f"🎚️   Brightness : Shift + Volume Up/Down")
            print(f"🔊  Volume     : Volume Up/Down (tanpa Shift)")
            print(f"⌨️   Fallback   : Ctrl + Arrow Up/Down")
            print(f"📊  Step/klik  : {BRIGHTNESS_STEP}/255")
            print(f"📄  Log file   : {LOG_FILE}")
            print(f"⛔  Berhenti   : Ctrl+C")
            print("=" * 55)
            print()

        reconnect_task = asyncio.create_task(self._reconnect_loop())

        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            reconnect_task.cancel()
            keyboard.unhook_all()
            try:
                await self.light.async_close()
            except Exception:
                pass
            bright_log.info("✅ Program dihentikan.")


# ===================
# Auto-start Installer
# ===================

def install_autostart():
    script_path = os.path.abspath(__file__)
    python_path = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(python_path):
        python_path = sys.executable
    task_name   = "WizBrightnessControl"

    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <LogonTrigger><Enabled>true</Enabled></LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_path}</Command>
      <Arguments>"{script_path}"</Arguments>
      <WorkingDirectory>{os.path.dirname(script_path)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    xml_path = os.path.join(os.environ.get("TEMP", "."), "wiz_task.xml")
    try:
        with open(xml_path, "w", encoding="utf-16") as f:
            f.write(xml)
        os.system(f'schtasks /delete /tn "{task_name}" /f >nul 2>&1')
        result = os.system(f'schtasks /create /tn "{task_name}" /xml "{xml_path}" /f')
        if result == 0:
            print(f"\n✅ Auto-start dipasang!")
            print(f"   Task   : {task_name}")
            print(f"   Script : {script_path}")
            print(f"   Log    : {LOG_FILE}")
            print(f"\nBerjalan otomatis setiap login. Hapus: python brightness_control.py --uninstall")
        else:
            print("❌ Gagal. Jalankan CMD sebagai Administrator.")
    finally:
        try:
            os.remove(xml_path)
        except Exception:
            pass


def uninstall_autostart():
    result = os.system('schtasks /delete /tn "WizBrightnessControl" /f')
    print("✅ Dihapus." if result == 0 else "❌ Tidak ditemukan atau gagal.")


# ===================
# Entry Point
# ===================

async def main():
    await BrightnessController().run()

if __name__ == "__main__":
    if "--install" in sys.argv:
        install_autostart()
    elif "--uninstall" in sys.argv:
        uninstall_autostart()
    elif "--scan" in sys.argv:
        print("\nMODE SCAN — Tekan tombol apa saja (Ctrl+C untuk berhenti)\n")
        def show(e):
            print(f"  Key name : '{e.name}'")
            print(f"  Scan code: {e.scan_code}")
            print(f"  Event    : {e.event_type}")
            print()
        keyboard.hook(show)
        try:
            keyboard.wait()
        except KeyboardInterrupt:
            keyboard.unhook_all()
    else:
        asyncio.run(main())
