# -*- coding: utf-8 -*-
"""
LG TV IR Remote Control
Python + Kivy app for Pydroid 3 (Android) using phone's built-in IR blaster.
Protocol: NEC (standard for most LG TVs)

REQUIREMENTS (install inside Pydroid 3 via pip):
    pip install kivy
    pip install pyjnius   (usually already bundled with Pydroid 3)

NOTE: Your phone MUST have a physical IR blaster (infrared LED).
Most Xiaomi, Huawei, and some Samsung phones have this; iPhones do NOT.
"""

import time
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp

# ----------------------------------------------------------------------
# Try to load Android's ConsumerIrManager via pyjnius.
# On desktop / non-Android systems, this will fail silently and the app
# will run in "simulation mode" (prints to console instead of sending IR).
# ----------------------------------------------------------------------
ANDROID = True
try:
    from jnius import autoclass, cast

    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Context = autoclass('android.content.Context')

    activity = PythonActivity.mActivity
    ir_service = activity.getSystemService(Context.CONSUMER_IR_SERVICE)
    ir_manager = cast('android.hardware.ConsumerIrManager', ir_service)

    HAS_IR = ir_manager.hasIrEmitter() if ir_manager else False
except Exception as e:
    ANDROID = False
    HAS_IR = False
    print("Not running on Android or pyjnius unavailable:", e)


# ----------------------------------------------------------------------
# NEC PROTOCOL ENCODER
# ----------------------------------------------------------------------
# NEC frame structure (in microseconds), carrier = 38kHz:
#   9000  leading burst
#   4500  leading space
#   For each of 32 bits (address, ~address, command, ~command):
#       560   burst
#       560 or 1690   space (0 or 1)
#   560   final burst (stop bit)
#
# LG remotes commonly use NEC with address 0x04 (many LG TVs) or a
# device-specific address. We use the widely-compatible generic LG
# address 0x04 here. If a button doesn't work on your TV, the hex
# code can be swapped out easily below.
# ----------------------------------------------------------------------

CARRIER_FREQ = 38000  # Hz, standard for NEC/LG

def nec_pattern(address, command):
    """
    Build a pulse pattern (list of microsecond durations) for NEC protocol.
    Pattern alternates: burst, space, burst, space, ...
    Returns a list of ints as required by Android's ConsumerIrManager.transmit().
    """
    pattern = [9000, 4500]  # leading burst + space

    def add_bit(bit):
        pattern.append(560)  # burst
        pattern.append(1690 if bit else 560)  # space

    def add_byte(byte_val):
        for i in range(8):
            bit = (byte_val >> i) & 1  # LSB first
            add_bit(bit)

    addr = address & 0xFF
    addr_inv = (~addr) & 0xFF
    cmd = command & 0xFF
    cmd_inv = (~cmd) & 0xFF

    add_byte(addr)
    add_byte(addr_inv)
    add_byte(cmd)
    add_byte(cmd_inv)

    pattern.append(560)  # final stop burst
    return pattern


def send_ir(address, command, label=""):
    """Transmit an NEC IR code, or simulate if not on Android/no IR emitter."""
    pattern = nec_pattern(address, command)

    if ANDROID and HAS_IR:
        try:
            # pyjnius supports passing a Python list directly for an int[]
            # parameter as long as every element is a plain Python int.
            # The previous java.lang.reflect.Array approach produced an
            # Object, not a primitive int[], which corrupted the Parcel.
            int_pattern = [int(v) for v in pattern]
            ir_manager.transmit(int(CARRIER_FREQ), int_pattern)
            print("Sent IR: %s (addr=0x%02X cmd=0x%02X) pattern_len=%d" %
                  (label, address, command, len(int_pattern)))
            return True, "Sent: %s" % label
        except Exception as e:
            err = "IR transmit FAILED: %s" % str(e)
            print(err)
            return False, err
    else:
        print("[SIMULATION] Would send: %s (addr=0x%02X cmd=0x%02X)" % (label, address, command))
        return True, "[SIM] %s" % label


# ----------------------------------------------------------------------
# LG TV COMMAND TABLE (NEC address 0x04 - common LG TV address)
# These are widely-used LG NEC command codes. If a button doesn't
# work on your specific model, that command can be replaced.
# ----------------------------------------------------------------------
LG_ADDRESS = 0x04

LG_COMMANDS = {
    "POWER":      0x08,
    "MUTE":       0x09,
    "VOL_UP":     0x02,
    "VOL_DOWN":   0x03,
    "CH_UP":      0x00,
    "CH_DOWN":    0x01,
    "UP":         0x40,
    "DOWN":       0x41,
    "LEFT":       0x07,
    "RIGHT":      0x06,
    "OK":         0x44,
    "MENU":       0x43,
    "BACK":       0x28,
    "HOME":       0x0E,
    "INPUT":      0x0B,
    "1":          0x10,
    "2":          0x11,
    "3":          0x12,
    "4":          0x13,
    "5":          0x14,
    "6":          0x15,
    "7":          0x16,
    "8":          0x17,
    "9":          0x18,
    "0":          0x19,
}


# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
class RemoteButton(Button):
    pass


class LGRemoteLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(10), spacing=dp(8), **kwargs)

        status_text = "IR Emitter: %s" % ("OK \u2713" if HAS_IR else "NOT FOUND (simulation mode)")
        self.status_label = Label(
            text=status_text,
            size_hint=(1, 0.06),
            color=(0, 1, 0, 1) if HAS_IR else (1, 0.3, 0.3, 1),
            bold=True,
        )
        self.add_widget(self.status_label)

        self.add_widget(self._section_label("LG TV Remote"))

        # Power + Input + Mute row
        row1 = BoxLayout(size_hint=(1, 0.09), spacing=dp(6))
        row1.add_widget(self._make_btn("POWER", "Power", bg=(0.8, 0.15, 0.15, 1)))
        row1.add_widget(self._make_btn("INPUT", "Input"))
        row1.add_widget(self._make_btn("MUTE", "Mute"))
        self.add_widget(row1)

        # Volume / Channel
        row2 = BoxLayout(size_hint=(1, 0.09), spacing=dp(6))
        row2.add_widget(self._make_btn("VOL_UP", "Vol +"))
        row2.add_widget(self._make_btn("VOL_DOWN", "Vol -"))
        row2.add_widget(self._make_btn("CH_UP", "Ch +"))
        row2.add_widget(self._make_btn("CH_DOWN", "Ch -"))
        self.add_widget(row2)

        # D-Pad
        dpad = GridLayout(cols=3, size_hint=(1, 0.28), spacing=dp(4))
        dpad.add_widget(Label())
        dpad.add_widget(self._make_btn("UP", "\u25b2"))
        dpad.add_widget(Label())
        dpad.add_widget(self._make_btn("LEFT", "\u25c0"))
        dpad.add_widget(self._make_btn("OK", "OK", bg=(0.15, 0.45, 0.8, 1)))
        dpad.add_widget(self._make_btn("RIGHT", "\u25b6"))
        dpad.add_widget(Label())
        dpad.add_widget(self._make_btn("DOWN", "\u25bc"))
        dpad.add_widget(Label())
        self.add_widget(dpad)

        # Menu / Back / Home
        row3 = BoxLayout(size_hint=(1, 0.09), spacing=dp(6))
        row3.add_widget(self._make_btn("BACK", "Back"))
        row3.add_widget(self._make_btn("HOME", "Home"))
        row3.add_widget(self._make_btn("MENU", "Menu"))
        self.add_widget(row3)

        # Numpad
        self.add_widget(self._section_label("Numbers"))
        numpad = GridLayout(cols=3, size_hint=(1, 0.30), spacing=dp(4))
        for n in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            numpad.add_widget(self._make_btn(n, n))
        numpad.add_widget(Label())
        numpad.add_widget(self._make_btn("0", "0"))
        numpad.add_widget(Label())
        self.add_widget(numpad)

    def _section_label(self, text):
        return Label(text=text, size_hint=(1, 0.05), bold=True, font_size="16sp")

    def _make_btn(self, cmd_key, text, bg=(0.25, 0.25, 0.25, 1)):
        btn = RemoteButton(text=text, background_color=bg, font_size="18sp")
        btn.bind(on_press=lambda instance, k=cmd_key: self.on_button(k))
        return btn

    def on_button(self, cmd_key):
        command = LG_COMMANDS.get(cmd_key)
        if command is None:
            return
        success, msg = send_ir(LG_ADDRESS, command, label=cmd_key)
        self.status_label.text = msg
        self.status_label.color = (0.2, 0.8, 1, 1) if success else (1, 0.3, 0.3, 1)


class LGRemoteApp(App):
    def build(self):
        self.title = "LG IR Remote"
        return LGRemoteLayout()


if __name__ == "__main__":
    LGRemoteApp().run()
