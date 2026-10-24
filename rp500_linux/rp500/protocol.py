"""Protocolo SysEx de la DigiTech RP500 (familia RP, mensajes empaquetados a 7 bits).

Formato: F0 00 00 10 <dev> <family> <product> <proc> <datos empaquetados> <chk> F7, con chk = XOR de todo
lo que va entre F0 y chk. Basado en el análisis del proyecto gdigi (GPLv3).
"""

MANUF = b"\x00\x00\x10"
FAMILY_RP, PRODUCT_RP500 = 0x5E, 0x05

WHO_AM_I_REQ, WHO_AM_I = 0x01, 0x02
CONFIG_REQ, CONFIG = 0x08, 0x09
GLOBALS_REQ, GLOBALS = 0x10, 0x11
NAMES_REQ, NAMES = 0x21, 0x22
NAME_REQ, NAME_SET = 0x28, 0x29
PRESET_REQ, PRESET_START, PRESET_END, PRESET_PARAMS = 0x2A, 0x2B, 0x2C, 0x2D
MOVE_PRESET = 0x39
LINKABLE_REQ, LINKABLE = 0x3A, 0x3B
PARAM_REQ, PARAM = 0x40, 0x41
NOTIFY = 0x70
ACK, NACK = 0x7E, 0x7F

BANK_SYSTEM, BANK_USER, BANK_EDIT = 0, 1, 4
NOTIFY_PRESET_MOVED = 3


def pack(data: bytes) -> bytes:
    out, status, sidx = bytearray(), 0, 0
    for i, b in enumerate(data):
        if i % 7 == 0:
            if i:
                out[sidx] = status
            status, sidx = 0, len(out)
            out.append(0)
        out.append(b & 0x7F)
        status |= (b & 0x80) >> ((i % 7) + 1)
    if data:
        out[sidx] = status
    return bytes(out)


def unpack(packed: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(packed), 8):
        status, chunk = packed[i], packed[i + 1:i + 8]
        for x, b in enumerate(chunk):
            out.append(b | ((status << (x + 1)) & 0x80))
    return bytes(out)


def frame(proc: int, data: bytes = b"", device=0x7F, family=FAMILY_RP, product=PRODUCT_RP500) -> bytes:
    body = MANUF + bytes([device, family, product, proc]) + pack(data)
    chk = 0
    for b in body:
        chk ^= b
    return b"\xF0" + body + bytes([chk]) + b"\xF7"


def parse(msg: bytes):
    """Devuelve (proc, datos desempaquetados). No valida el checksum (el firmware no siempre lo cuadra)."""
    return msg[7], unpack(msg[8:-2])


def enc_value(v: int) -> bytes:
    if v < 0x80:
        return bytes([v])
    n = max(2, (v.bit_length() + 7) // 8)
    return bytes([0x80 | n]) + v.to_bytes(n, "big")


def dec_value(b: bytes):
    """-> (valor, bytes consumidos). Los valores >0x80 llevan longitud en el primer byte."""
    if b[0] > 0x80:
        n = b[0] & 0x7F
        return int.from_bytes(b[1:1 + n], "big"), 1 + n
    return b[0], 1


def param_set(pid: int, pos: int, val: int) -> bytes:
    return frame(PARAM, bytes([pid >> 8, pid & 0xFF, pos]) + enc_value(val))


def param_req(pid: int, pos: int) -> bytes:
    return frame(PARAM_REQ, bytes([pid >> 8, pid & 0xFF, pos]))


def dec_param(data: bytes):
    pid, pos = (data[0] << 8) | data[1], data[2]
    val, n = dec_value(data[3:])
    return pid, pos, val, 3 + n
