**E**mploying an Orange Pi as the central processing unit, the software captures voice commands via a Wi-Fi interface.

**W**hen a pertinent command is detected, the software establishes a Bluetooth connection with a SPIKE Prime Hub.

**A** revised MicroPython script is then transmitted to the Hub. Upon receiving the script, the Hub ceases its current activities, loads the new script, and executes it, thereby providing real-time control over LEGO components.

```
pip install -r requirements.txt
```