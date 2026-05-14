# WiZ Knob Brightness Control v0.1.0

Control your WiZ light brightness using your keyboard volume knob on Windows.

This project lets you use **Shift + Volume Up/Down** to control your WiZ light brightness, while keeping the normal system volume behavior when pressing the volume knob without Shift.

Built with Python, `keyboard`, and [`pywizlight`](https://github.com/sbidy/pywizlight).

---

## Features

- Shift + Volume Up/Down to control WiZ light brightness
- Volume Up/Down without Shift still controls system volume
- Ctrl + Arrow Up/Down fallback shortcut
- Auto reconnect when the light is disconnected
- Optional auto-start on Windows login via Task Scheduler
- Runs silently in the background using `pythonw.exe` when available
- Lightweight local network utility

---

## Requirements

- Windows
- Python 3.7+
- WiZ smart light
- Keyboard with volume knob or volume keys
- Same local network between your PC and WiZ light

---

## Installation

Install dependencies:

```bash
python -m pip install keyboard pywizlight
```

---

## Configuration

Set your WiZ light IP address.

### Option 1: Edit the script directly

```python
LIGHT_IP = os.getenv("WIZ_LIGHT_IP", "192.168.0.100")
```

Replace `192.168.0.100` with your WiZ light IP address.

### Option 2: Set environment variable temporarily

For CMD:

```bash
set WIZ_LIGHT_IP=192.168.0.100
python brightness_control.py
```

For PowerShell:

```powershell
$env:WIZ_LIGHT_IP="192.168.0.100"
python brightness_control.py
```

To find your WiZ light IP address, you can check your router’s connected devices list. WiZ devices usually appear with a name similar to `wiz_xxxxxx`.

---

## Run Manually

Run the script as Administrator:

```bash
python brightness_control.py
```

Administrator permission may be required because the app uses a global keyboard hook to detect volume keys.

---

## Controls

| Shortcut | Action |
|---|---|
| Shift + Volume Up | Increase WiZ brightness |
| Shift + Volume Down | Decrease WiZ brightness |
| Volume Up | Normal system volume up |
| Volume Down | Normal system volume down |
| Ctrl + Arrow Up | Increase WiZ brightness fallback |
| Ctrl + Arrow Down | Decrease WiZ brightness fallback |

---

## Auto-start on Windows Login

Install auto-start:

```bash
python brightness_control.py --install
```

Remove auto-start:

```bash
python brightness_control.py --uninstall
```

The auto-start installer uses Windows Task Scheduler.

When available, it will use `pythonw.exe` so the script can run silently in the background without opening a CMD window. If `pythonw.exe` is not found, it will safely fall back to the current Python executable.

---

## Scan Keyboard Codes

If your keyboard has different scan codes, use scan mode:

```bash
python brightness_control.py --scan
```

Press the volume knob or target keys, then update the scan code values inside the script if needed.

---

## Security Notes

This project is intended for **personal and local network use**.

The app listens to global keyboard events only to detect volume keys and modifier keys. It does **not** record, store, or transmit typed characters.

Because the script may require Administrator permission on Windows, only run code that you trust and review the script before enabling auto-start.

No passwords, API keys, or cloud credentials are required. The app only communicates with your WiZ light on your local network.

---

## Troubleshooting

### CMD window appears on startup

Make sure auto-start is installed using:

```bash
python brightness_control.py --install
```

The installer will try to use `pythonw.exe`. If `pythonw.exe` is unavailable, it will fall back to your current Python executable.

### Brightness does not reach 0%

Some WiZ lights may behave differently at very low brightness values. If needed, adjust the brightness step or minimum brightness logic inside the script.

Example:

```python
BRIGHTNESS_STEP = 36
```

### Light is not responding

Check that:

- Your PC and WiZ light are on the same Wi-Fi/local network
- The `WIZ_LIGHT_IP` value is correct
- The WiZ light is powered on
- The script is running as Administrator

---

## Credits

See [CREDITS.md](./CREDITS.md).

---

## License

MIT License