import os, sys, select, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rp500_linux"))
from rp500 import protocol as px
fd = os.open("/dev/snd/midiC1D0", os.O_RDWR | os.O_NONBLOCK)
def rx(t=1.0):
    buf, end = b"", time.time() + t
    while time.time() < end:
        if select.select([fd], [], [], 0.1)[0]:
            buf += os.read(fd, 4096)
    return [m + b"\xF7" for m in buf.split(b"\xF7") if m]
def ask(proc, data=b"", t=1.0):
    os.write(fd, px.frame(proc, data)); return rx(t)
for m in ask(px.WHO_AM_I_REQ, b"\x7f\x7f\x7f"): print("whoami", m.hex(" "), px.parse(m))
for m in ask(px.CONFIG_REQ): print("config", px.parse(m))
for m in ask(px.NAMES_REQ, bytes([px.BANK_USER]), 2):
    p, d = px.parse(m); print("names proc", hex(p), d[:80])
