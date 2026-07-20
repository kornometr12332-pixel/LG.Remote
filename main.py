# -*- coding: utf-8 -*-
"""
LG TV IR Remote Control
Python + Kivy app for Pydroid 3 (Android) using phone's built-in IR blaster.
Protocol: NEC (standard for most LG TVs)
"""

import time
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.metrics import dp
from kivy.graphics import Color, RoundedRectangle, Ellipse
from kivy.core.window import Window

# ----------------------------------------------------------------------
# Try to load Android's ConsumerIrManager via pyjnius.
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
# NEC PROTOCOL ENCODER (UNCHANGED)
# ----------------------------------------------------------------------
CARRIER_FREQ = 38000

def nec_pattern(address, command):
    pattern = [9000, 4500]

    def add_bit(bit):
        pattern.append(560)
        pattern.append(1690 if bit else 560)

    def add_byte(byte_val):
        for i in range(8):
            bit = (byte_val >> i) & 1
            add_bit(bit)

    addr = address & 0xFF
    addr_inv = (~addr) & 0xFF
    cmd = command & 0xFF
    cmd_inv = (~cmd) & 0xFF

    add_byte(addr)
    add_byte(addr_inv)
    add_byte(cmd)
    add_byte(cmd_inv)

    pattern.append(560)
    return pattern


def send_ir(address, command, label=""):
    pattern = nec_pattern(address, command)

    if ANDROID and HAS_IR:
        try:
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
# LG TV COMMAND TABLE
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

# Candidate codes for the channel-list button. Different LG TV models/years
# use different codes for this button, so the LIST button below cycles
# through them one at a time - press it repeatedly (no rebuild needed)
# until the channel list appears on the TV, then note which number worked.
LIST_CANDIDATES = [0x5B, 0x53, 0x1A, 0x4C, 0x0B, 0x1E, 0x1F]


# ----------------------------------------------------------------------
# UI COLORS - dark real-remote look
# ----------------------------------------------------------------------
BG_COLOR = (0.07, 0.07, 0.08, 1)        # near-black body
BTN_COLOR = (0.16, 0.16, 0.18, 1)       # dark gray circular buttons
BTN_PRESSED = (0.28, 0.28, 0.32, 1)
POWER_COLOR = (0.75, 0.12, 0.12, 1)     # red power button
OK_COLOR = (0.15, 0.4, 0.85, 1)         # blue OK button
TEXT_COLOR = (0.92, 0.92, 0.92, 1)


class RoundButton(Button):
    """A circular/rounded flat button drawn manually (real-remote look)."""
    def __init__(self, bg_color=BTN_COLOR, radius=None, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)  # hide default kivy bg
        self.color = TEXT_COLOR
        self.bold = True
        self.bg_color = bg_color
        self._radius = radius
        with self.canvas.before:
            self._color_instr = Color(*self.bg_color)
            self._shape = RoundedRectangle(pos=self.pos, size=self.size, radius=[self._get_radius()])
        self.bind(pos=self._update_shape, size=self._update_shape)
        self.bind(state=self._update_color)

    def _get_radius(self):
        if self._radius is not None:
            return self._radius
        return min(self.width, self.height) / 2 if self.width and self.height else dp(28)

    def _update_shape(self, *args):
        self._shape.pos = self.pos
        self._shape.size = self.size
        self._shape.radius = [self._get_radius()]

    def _update_color(self, *args):
        self._color_instr.rgba = BTN_PRESSED if self.state == "down" else self.bg_color


class LGRemoteLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        with self.canvas.before:
            Color(*BG_COLOR)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(24)])
        self.bind(pos=self._update_bg, size=self._update_bg)

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(10))
        self.add_widget(root)

        status_text = "IR: %s" % ("Ready" if HAS_IR else "Simulation mode")
        self.status_label = Label(
            text=status_text,
            size_hint=(1, 0.05),
            color=(0.3, 0.85, 0.4, 1) if HAS_IR else (0.85, 0.5, 0.2, 1),
            bold=True,
            font_size="13sp",
        )
        root.add_widget(self.status_label)

        # ---- Top row: Power / Input / Mute / List ----
        top_row = BoxLayout(size_hint=(1, 0.11), spacing=dp(14), padding=(dp(16), 0))
        top_row.add_widget(self._make_round("POWER", "PWR", bg=POWER_COLOR, font_size="14sp"))
        top_row.add_widget(self._make_round("INPUT", "IN", font_size="14sp"))
        top_row.add_widget(self._make_round("MUTE", "MUTE", font_size="12sp"))
        self.list_index = 0
        self.list_btn = self._make_round("LIST", "LIST #1", font_size="12sp")
        self.list_btn.bind(on_press=lambda instance: self.on_list_button())
        top_row.add_widget(self.list_btn)
        root.add_widget(top_row)

        # ---- D-Pad in a circular cluster ----
        dpad_container = FloatLayout(size_hint=(1, 0.30))
        dpad_size = dp(220)
        dpad_wrap = BoxLayout(size_hint=(None, None), size=(dpad_size, dpad_size),
                               pos_hint={"center_x": 0.5, "center_y": 0.5})
        dpad = GridLayout(cols=3, rows=3, spacing=dp(3))
        dpad.add_widget(Label())
        dpad.add_widget(self._make_round("UP", "UP", font_size="13sp"))
        dpad.add_widget(Label())
        dpad.add_widget(self._make_round("LEFT", "LEFT", font_size="13sp"))
        dpad.add_widget(self._make_round("OK", "OK", bg=OK_COLOR, font_size="16sp"))
        dpad.add_widget(self._make_round("RIGHT", "RIGHT", font_size="13sp"))
        dpad.add_widget(Label())
        dpad.add_widget(self._make_round("DOWN", "DOWN", font_size="13sp"))
        dpad.add_widget(Label())
        dpad_wrap.add_widget(dpad)
        dpad_container.add_widget(dpad_wrap)
        root.add_widget(dpad_container)

        # ---- Menu / Back / Home ----
        row3 = BoxLayout(size_hint=(1, 0.09), spacing=dp(14))
        row3.add_widget(self._make_pill("BACK", "Back"))
        row3.add_widget(self._make_pill("HOME", "Home"))
        row3.add_widget(self._make_pill("MENU", "Menu"))
        root.add_widget(row3)

        # ---- Volume / Channel ----
        vc_row = BoxLayout(size_hint=(1, 0.11), spacing=dp(24), padding=(dp(10), 0))

        vol_col = BoxLayout(orientation="vertical", spacing=dp(6))
        vol_label = Label(text="VOL", size_hint=(1, 0.01), font_size="10sp", color=(0.6, 0.6, 0.6, 1))
        vol_row = BoxLayout(spacing=dp(8))
        vol_row.add_widget(self._make_round("VOL_UP", "+"))
        vol_row.add_widget(self._make_round("VOL_DOWN", "-"))
        vol_col.add_widget(vol_label)
        vol_col.add_widget(vol_row)

        ch_col = BoxLayout(orientation="vertical", spacing=dp(6))
        ch_label = Label(text="CH", size_hint=(1, 0.01), font_size="10sp", color=(0.6, 0.6, 0.6, 1))
        ch_row = BoxLayout(spacing=dp(8))
        ch_row.add_widget(self._make_round("CH_UP", "+"))
        ch_row.add_widget(self._make_round("CH_DOWN", "-"))
        ch_col.add_widget(ch_label)
        ch_col.add_widget(ch_row)

        vc_row.add_widget(vol_col)
        vc_row.add_widget(ch_col)
        root.add_widget(vc_row)

        # ---- Numpad ----
        numpad = GridLayout(cols=3, size_hint=(1, 0.34), spacing=dp(8), padding=(dp(20), dp(4)))
        for n in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]:
            numpad.add_widget(self._make_round(n, n, font_size="17sp"))
        numpad.add_widget(Label())
        numpad.add_widget(self._make_round("0", "0", font_size="17sp"))
        numpad.add_widget(Label())
        root.add_widget(numpad)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _make_round(self, cmd_key, text, bg=BTN_COLOR, font_size="16sp"):
        btn = RoundButton(text=text, bg_color=bg, font_size=font_size,
                           size_hint=(1, 1))
        btn.bind(on_press=lambda instance, k=cmd_key: self.on_button(k))
        return btn

    def _make_pill(self, cmd_key, text):
        btn = RoundButton(text=text, bg_color=BTN_COLOR, font_size="13sp",
                           radius=dp(18), size_hint=(1, 1))
        btn.bind(on_press=lambda instance, k=cmd_key: self.on_button(k))
        return btn

    def on_button(self, cmd_key):
        command = LG_COMMANDS.get(cmd_key)
        if command is None:
            return
        success, msg = send_ir(LG_ADDRESS, command, label=cmd_key)
        self.status_label.text = msg
        self.status_label.color = (0.3, 0.85, 1, 1) if success else (1, 0.3, 0.3, 1)

    def on_list_button(self):
        # Sends the next candidate code each press so you don't need to
        # rebuild the app to try different LIST codes. The button label
        # and status bar show which candidate number was just sent -
        # remember that number once the channel list appears on the TV.
        code = LIST_CANDIDATES[self.list_index]
        n = self.list_index + 1
        success, msg = send_ir(LG_ADDRESS, code, label="LIST #%d (0x%02X)" % (n, code))
        self.status_label.text = msg
        self.status_label.color = (0.3, 0.85, 1, 1) if success else (1, 0.3, 0.3, 1)
        self.list_index = (self.list_index + 1) % len(LIST_CANDIDATES)
        self.list_btn.text = "LIST #%d" % (self.list_index + 1)


class LGRemoteApp(App):
    def build(self):
        self.title = "LG IR Remote"
        Window.clearcolor = BG_COLOR
        return LGRemoteLayout()


if __name__ == "__main__":
    LGRemoteApp().run()
		
