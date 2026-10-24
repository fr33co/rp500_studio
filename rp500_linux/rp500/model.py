"""Catálogo de efectos de la RP500 (extraído de gdigi, GPLv3) y formato de valores."""
import json
import os

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

CATEGORY_COLORS = {
    "Wah": "#ff2d6f", "Compressor": "#f59e0b", "Distortion": "#f97316", "Amplifier": "#10b981",
    "Equalizer": "#22d3ee", "Noisegate": "#14b8a6", "Chorus/FX": "#d946ef", "Delay": "#eab308",
    "Reverb": "#38bdf8", "Expression Pedal": "#84cc16",
}
AMP_BYPASS_ID = 12361


def load_catalog():
    with open(os.path.join(DATA, "effects.json"), encoding="utf-8") as f:
        return json.load(f)["pages"][0]["effects"]


def value_range(v):
    """Rango entero (min, max) cubriendo los tramos 'extra' (p. ej. 0..99 y 100='RHold')."""
    lo, hi = v["min"], v["max"]
    x = v.get("extra")
    while x:
        lo, hi = min(lo, x["min"]), max(hi, x["max"])
        x = x.get("extra")
    return int(lo), int(hi)


def format_value(v, raw):
    """Texto de un valor crudo, igual que la app original (etiquetas, offset, paso, sufijo)."""
    while v.get("extra") and not (v["min"] <= raw <= v["max"]):
        v = v["extra"]
    if v["type"] & 8 and v.get("labels"):
        i = int(raw - v["min"])
        return v["labels"][i] if 0 <= i < len(v["labels"]) else str(raw)
    x = (raw + v["offset"]) * v["step"]
    txt = f"{x:.{max(1, v['decimal'])}f}" if v["decimal"] or v["step"] != int(v["step"]) else f"{int(x)}"
    return txt + (v["suffix"] or "")


def chain(catalog):
    """Bloques de la cadena de señal, en orden: [(nombre, color, [items])]. Amp y Cab van separados."""
    out = []
    for e in catalog:
        if e["label"] == "Expression Pedal":
            out.append(("Pedal", CATEGORY_COLORS["Expression Pedal"], []))
            continue
        if e["label"] == "Amplifier":
            bypass, amp, cab = e["items"]
            out.append(("Amp", CATEGORY_COLORS["Amplifier"], [bypass, amp]))
            out.append(("Cab", "#60a5fa", [bypass, cab]))
        else:
            out.append((e["label"].replace("Chorus/FX", "Mod/FX"), CATEGORY_COLORS.get(e["label"], "#9ca3af"),
                        e["items"]))
    return out


EXP_ASSIGN, EXP_MIN, EXP_MAX, EXP_POS = 8194, 8195, 8196, 19


def load_modifiers():
    """{(id, posición): {label, values}} de todos los parámetros que se pueden asignar al pedal."""
    with open(os.path.join(DATA, "modifiers.json"), encoding="utf-8") as f:
        return {(m["id"], m["position"]): m for m in json.load(f)}
