#!/usr/bin/env python3
"""
Parse a ZMK keyboard's matrix-transform + default_layer bindings + kscan
GPIOs into a JSON preset usable by the KeyCheck Matrix Diagnostic mode.

Usage:
    python3 tools/parse_zmk.py <name> <transform_dtsi> <keymap_file> <left_overlay> <right_overlay>

Produces: presets/<name>.json (under docs/)
"""

import json
import re
import sys
from pathlib import Path


# Minimal ZMK keyname → HID name (matches HID_MAP in docs/index.html).
# For keys we can't map, the position is marked untestable.
ZMK_TO_HID = {
    # letters
    **{c: c.lower() for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
    # digits
    **{f"N{n}": str(n) for n in range(10)},
    # punctuation / special
    "ESC": "escape",
    "ESCAPE": "escape",
    "TAB": "tab",
    "SPACE": "spacebar",
    "BSPC": "delete_or_backspace",
    "BACKSPACE": "delete_or_backspace",
    "RET": "return_or_enter",
    "ENTER": "return_or_enter",
    "COMMA": "comma",
    "DOT": "period",
    "PERIOD": "period",
    "SLASH": "slash",
    "MINUS": "hyphen",
    "EQUAL": "equal_sign",
    "LBKT": "open_bracket",
    "RBKT": "close_bracket",
    "BSLH": "backslash",
    "SEMI": "semicolon",
    "SQT": "quote",
    "QMARK": "slash",   # ? = shift+/ on US, but produces same HID as /
    "COLON": "semicolon",
    "GRAVE": "grave_accent_and_tilde",
    "CAPS": "caps_lock",
    "CAPSLOCK": "caps_lock",
    # modifiers
    "LCTRL": "left_control",
    "LCTL":  "left_control",
    "LSHFT": "left_shift",
    "LSHIFT": "left_shift",
    "LGUI":  "left_command",
    "LALT":  "left_option",
    "RCTRL": "right_control",
    "RCTL":  "right_control",
    "RSHFT": "right_shift",
    "RSHIFT": "right_shift",
    "RGUI":  "right_command",
    "RALT":  "right_option",
    # navigation
    "DEL": "delete_forward",
    "INS": "insert",
    "HOME": "home",
    "END":  "end",
    "PG_UP": "page_up",
    "PG_DN": "page_down",
    "UP":    "up_arrow",
    "DOWN":  "down_arrow",
    "LEFT":  "left_arrow",
    "RIGHT": "right_arrow",
    # function keys
    **{f"F{n}": f"f{n}" for n in range(1, 25)},
    # misc
    "PSCRN": "print_screen",
    "C_MUTE": "mute",
    "C_VOL_UP": "volume_up",
    "C_VOL_DN": "volume_down",
    # japanese
    "JP_YEN":   "japanese_pc_yen",
    "JP_MINUS": "hyphen",          # JP keys are aliases — same HID
    "JP_AT":    "open_bracket",    # JP_AT = LBKT
    "JP_HASH":  "3",
    "JP_DLLR":  "4",
    "JP_PRCNT": "5",
    "JP_AMPS":  "6",
    "JP_LPAR":  "8",
    "JP_RPAR":  "9",
    "JP_EQUAL": "hyphen",          # JP_EQUAL = MINUS in JIS; this is approximate
    "JP_PLUS":  "semicolon",       # JP_PLUS = SEMI in JIS
    "JP_ASTRK": "quote",           # JP_ASTRK = SQT
    "JP_SLASH": "slash",
    "JP_GRAVE": "open_bracket",
    "JP_TILDE": "equal_sign",
    "JP_BSLH":  "japanese_pc_yen", # backslash on JIS sends YEN
    "JP_SEMI":  "semicolon",
    "JP_COLON": "quote",
    "JP_SQT":   "7",
    "JP_DQT":   "2",
    "JP_LBKT":  "close_bracket",
    "JP_RBKT":  "backslash",
    "JP_LBRC":  "close_bracket",
    "JP_RBRC":  "backslash",
    "JP_LT":    "comma",
    "JP_GT":    "period",
    "JP_QMARK": "slash",
    "JP_PIPE":  "japanese_pc_yen",
    "JP_CARET": "equal_sign",
    "JP_EXCL":  "1",
    # language
    "LANG1": "japanese_pc_katakana",
    "LANG2": "japanese_pc_hiragana",
}

# Hold-tap behaviors → testable arg index (the "tap" arg)
HOLD_TAP_BEHAVIORS = {
    "&mt": 1, "&lt": 1,
    "&plt": 1, "&mth": 1, "&lth": 1, "&mtt": 1, "&ltt": 1,
}

# Custom mod-morphs from Modula keymap (tap = first binding's primary kp arg)
MOD_MORPH_TO_KEY = {
    "&minus": "JP_MINUS",
    "&semi":  "JP_SEMI",
    "&sqt":   "JP_SQT",
}


def zmk_to_hid(name: str):
    return ZMK_TO_HID.get(name)


def parse_transform(dtsi_text: str):
    """Extract list of (driver, sensor) pairs from matrix-transform map."""
    m = re.search(r'matrix-transform"\s*;.*?map\s*=\s*<(.+?)>\s*;', dtsi_text, re.DOTALL)
    if not m:
        raise RuntimeError("matrix-transform map not found")
    block = m.group(1)
    # strip /* ... */ comments
    block = re.sub(r'/\*.*?\*/', '', block, flags=re.DOTALL)
    # strip // comments
    block = re.sub(r'//[^\n]*', '', block)
    pairs = re.findall(r'RC\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)', block)
    return [(int(d), int(s)) for d, s in pairs]


def parse_kscan_gpios(overlay_text: str):
    """Extract the GPIO list from `&kscan0 { ... gpios = ...; }` block."""
    m = re.search(r'&kscan0\s*\{(.*?)\};', overlay_text, re.DOTALL)
    if not m:
        return None
    block = m.group(1)
    gm = re.search(r'(?<![-\w])gpios\s*=\s*(.+?);', block, re.DOTALL)
    if not gm:
        return None
    pins = re.findall(r'<\s*&(\w+)\s+(\d+)\s*\(', gm.group(1))
    return [(bank, int(pin)) for bank, pin in pins]


def parse_kscan_inline_gpios(dtsi_text: str):
    """Same but for kscan0 / kscan1 defined inline (Modula-style)."""
    out = {}
    for m in re.finditer(r'(\w+)\s*:\s*\1\s*\{([^{}]+(?:\{[^{}]*\}[^{}]*)*)\};', dtsi_text):
        node_label = m.group(1)
        body = m.group(2)
        if 'kscan-gpio-charlieplex' not in body:
            continue
        gm = re.search(r'(?<![-\w])gpios\s*=\s*(.+?);', body, re.DOTALL)
        if not gm:
            continue
        pins = re.findall(r'<\s*&(\w+)\s+(\d+)\s*\(', gm.group(1))
        out[node_label] = [(bank, int(pin)) for bank, pin in pins]
    return out


def gpio_to_xiao_label(bank: str, pin: int):
    """Best-effort xiao_ble D-pin label."""
    table = {
        ('gpio0', 2):  'D0', ('gpio0', 3):  'D1', ('gpio0', 28): 'D2',
        ('gpio0', 29): 'D3', ('gpio0', 4):  'D4', ('gpio0', 5):  'D5',
        ('gpio1', 11): 'D6', ('gpio1', 12): 'D7', ('gpio1', 13): 'D8',
        ('gpio1', 14): 'D9', ('gpio1', 15): 'D10',
    }
    if (bank, pin) in table:
        return table[(bank, pin)]
    bank_num = bank[-1]
    return f'P{bank_num}.{pin:02d}'


def parse_default_layer_bindings(keymap_text: str):
    """Tokenize the default_layer bindings list into [(behavior, args), ...]."""
    m = re.search(r'default_layer\s*\{[^{}]*?bindings\s*=\s*<(.+?)>\s*;',
                  keymap_text, re.DOTALL)
    if not m:
        raise RuntimeError("default_layer bindings not found")
    block = m.group(1)
    # strip comments
    block = re.sub(r'//[^\n]*', '', block)
    block = re.sub(r'/\*.*?\*/', '', block, flags=re.DOTALL)
    tokens = block.split()
    out = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if not tok.startswith('&'):
            i += 1
            continue
        beh = tok
        args = []
        i += 1
        # Gather args until next behavior token. Args may include parentheses
        # (e.g. SCUP_F = MOVE_Y(120)) which were already split by whitespace.
        depth = 0
        while i < len(tokens):
            t = tokens[i]
            if t.startswith('&') and depth == 0:
                break
            args.append(t)
            depth += t.count('(') - t.count(')')
            i += 1
        out.append((beh, args))
    return out


def binding_to_hid_and_label(behavior: str, args):
    """Return (hid_name_or_None, display_label, testable)."""
    if behavior == '&kp' and args:
        return zmk_to_hid(args[0]), args[0], True
    if behavior in HOLD_TAP_BEHAVIORS:
        idx = HOLD_TAP_BEHAVIORS[behavior]
        if idx < len(args):
            tap = args[idx]
            return zmk_to_hid(tap), f"{behavior} … {tap}", True
    if behavior == '&trans':
        return None, '▽ trans', False
    if behavior == '&none':
        return None, 'none', False
    if behavior == '&mo' and args:
        return None, f"mo {args[0]}", False
    if behavior == '&tog' and args:
        return None, f"tog {args[0]}", False
    if behavior in MOD_MORPH_TO_KEY:
        zk = MOD_MORPH_TO_KEY[behavior]
        return zmk_to_hid(zk), behavior.lstrip('&'), True
    if behavior == '&mkp' and args:
        # mouse button — diagnostic via pointing_button event
        b = args[0]
        # MB1/LCLK = button1, MB2/RCLK = button2, MB3/MCLK = button3
        btn = {'MB1': 1, 'LCLK': 1, 'MB2': 2, 'RCLK': 2,
               'MB3': 3, 'MCLK': 3, 'MB4': 4, 'MB5': 5}.get(b)
        if btn:
            return f'mouse:{btn}', f"mkp {b}", True
        return None, f"mkp {b}", False
    if behavior == '&msc':
        return None, '⬔ scroll', False
    if behavior == '&bt':
        return None, ' '.join(['bt'] + args), False
    if behavior == '&out':
        return None, ' '.join(['out'] + args), False
    # custom mod-morphs we couldn't decode
    return None, behavior.lstrip('&'), False


def build_preset(name, dtsi_text, keymap_text, l_overlay_text=None,
                 r_overlay_text=None, split_at_sensor=6):
    transform = parse_transform(dtsi_text)
    bindings = parse_default_layer_bindings(keymap_text)
    if len(transform) != len(bindings):
        print(f"!! mismatch: {len(transform)} transform RCs vs {len(bindings)} bindings",
              file=sys.stderr)
    n = min(len(transform), len(bindings))

    # GPIO pin labels per side
    pin_labels_l = []
    pin_labels_r = []
    if l_overlay_text:
        pins = parse_kscan_gpios(l_overlay_text)
        if pins:
            pin_labels_l = [gpio_to_xiao_label(b, p) for b, p in pins]
    if r_overlay_text:
        pins = parse_kscan_gpios(r_overlay_text)
        if pins:
            pin_labels_r = [gpio_to_xiao_label(b, p) for b, p in pins]

    # Modula-specific: kscan defined inline
    inline = parse_kscan_inline_gpios(dtsi_text)
    if not pin_labels_l and inline:
        # take the first charlieplex
        first = next(iter(inline.values()))
        pin_labels_l = [gpio_to_xiao_label(b, p) for b, p in first]
        pin_labels_r = list(pin_labels_l)  # assume mirror

    positions = []
    for idx in range(n):
        d, s = transform[idx]
        beh, args = bindings[idx]
        hid, label, testable = binding_to_hid_and_label(beh, args)

        # Determine side. Convention: sensor < split_at_sensor → left.
        # For Modula's RC(6, *) direct kscan rows, mark as 'direct'.
        if d >= split_at_sensor:  # row offset for direct kscan in Modula
            side = 'direct'
            # use sensor < split_at_sensor for L, >= for R
            sub_side = 'L' if s < split_at_sensor else 'R'
            normalized_sensor = s if s < split_at_sensor else s - split_at_sensor
            positions.append({
                'idx': idx, 'side': 'direct', 'sub_side': sub_side,
                'driver': d, 'sensor': normalized_sensor,
                'expected': hid, 'label': label, 'testable': bool(testable),
                'binding': ' '.join([beh] + args),
            })
            continue
        if s < split_at_sensor:
            side = 'L'
            ns = s
        else:
            side = 'R'
            ns = s - split_at_sensor
        positions.append({
            'idx': idx, 'side': side,
            'driver': d, 'sensor': ns,
            'expected': hid, 'label': label, 'testable': bool(testable),
            'binding': ' '.join([beh] + args),
        })

    return {
        'name': name,
        'pinsPerSide': max(len(pin_labels_l), 6),
        'pinLabelsL': pin_labels_l,
        'pinLabelsR': pin_labels_r,
        'positions': positions,
    }


def main():
    if len(sys.argv) < 4:
        print("Usage: parse_zmk.py <name> <dtsi> <keymap> [<l_overlay> <r_overlay>]")
        sys.exit(1)
    name, dtsi, keymap = sys.argv[1], sys.argv[2], sys.argv[3]
    l_overlay = sys.argv[4] if len(sys.argv) > 4 else None
    r_overlay = sys.argv[5] if len(sys.argv) > 5 else None

    dtsi_text = Path(dtsi).read_text()
    keymap_text = Path(keymap).read_text()
    l_text = Path(l_overlay).read_text() if l_overlay else None
    r_text = Path(r_overlay).read_text() if r_overlay else None

    preset = build_preset(name, dtsi_text, keymap_text, l_text, r_text)

    # Output JSON to docs/presets/<name>.json
    out_dir = Path('docs/presets')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'{name.lower()}.json'
    out_path.write_text(json.dumps(preset, indent=2, ensure_ascii=False))
    print(f"Wrote {out_path} ({len(preset['positions'])} positions)")
    # Quick summary
    testable = sum(1 for p in preset['positions'] if p['testable'])
    print(f"  testable: {testable}, untestable: {len(preset['positions']) - testable}")
    sides = {}
    for p in preset['positions']:
        sides[p['side']] = sides.get(p['side'], 0) + 1
    print(f"  sides: {sides}")


if __name__ == '__main__':
    main()
