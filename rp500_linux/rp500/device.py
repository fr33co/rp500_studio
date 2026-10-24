"""Acceso a la RP500 por USB-MIDI (ALSA rawmidi, /dev/snd/midiC*D*), con hilo lector.

Los mensajes que la pedalera envía por su cuenta (perillas, cambio de preset) salen por señales Qt;
las respuestas a una petición se entregan por una cola, así que `request` se puede llamar desde el hilo de la GUI.
"""
import os
import queue
import select
import subprocess
import threading
import time

from PyQt5 import QtCore

from . import protocol as px


class DeviceError(Exception):
    pass


def find_device():
    try:
        out = subprocess.run(["amidi", "-l"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError) as e:
        raise DeviceError(f"No se pudo ejecutar amidi: {e}")
    for line in out.splitlines()[1:]:
        if "RP500" in line:
            card, dev = line.split()[1][3:].split(",")[:2]
            return f"/dev/snd/midiC{card}D{dev}"
    raise DeviceError("No se ve la RP500 por USB (amidi -l).")


def pedal_present():
    try:
        find_device()
        return True
    except DeviceError:
        return False


class Pedal(QtCore.QObject):
    param_changed = QtCore.pyqtSignal(int, int, int)   # id, posición, valor (movido en la pedalera)
    preset_moved = QtCore.pyqtSignal(int, int)         # banco, índice cargados en el buffer de edición
    lost = QtCore.pyqtSignal()

    def __init__(self, path=None):
        super().__init__()
        try:
            self.fd = os.open(path or find_device(), os.O_RDWR | os.O_NONBLOCK)
        except OSError as e:
            raise DeviceError(f"No se pudo abrir el dispositivo: {e}")
        self._q = queue.Queue()
        self._lock = threading.Lock()
        self._stop = False
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    GUI_MODE = 12298   # como gdigi: avisa a la pedalera de que hay un editor conectado

    def gui_mode(self, on):
        self.set_param(self.GUI_MODE, 0, int(on))
        time.sleep(0.05)

    def close(self):
        if not self._stop:
            try:
                self.gui_mode(False)
            except OSError:
                pass
        self._stop = True
        self._t.join(1)
        try:
            os.close(self.fd)
        except OSError:
            pass

    def _reader(self):
        buf = b""
        while not self._stop:
            try:
                if not select.select([self.fd], [], [], 0.2)[0]:
                    continue
                buf += os.read(self.fd, 4096)
            except OSError:
                if not self._stop:
                    self.lost.emit()
                return
            while b"\xF7" in buf:
                msg, buf = buf[:buf.index(b"\xF7") + 1], buf[buf.index(b"\xF7") + 1:]
                if b"\xF0" in msg:
                    self._dispatch(msg[msg.index(b"\xF0"):])

    def _dispatch(self, msg):
        if len(msg) < 10:
            return
        proc, data = px.parse(msg)
        if proc == px.NOTIFY and data and data[0] == px.NOTIFY_PRESET_MOVED and len(data) >= 5:
            if data[3] == px.BANK_EDIT:
                self.preset_moved.emit(data[1], data[2])
        elif proc == px.PARAM and not self._lock.locked():
            pid, pos, val, _ = px.dec_param(data)
            self.param_changed.emit(pid, pos, val)
        else:
            self._q.put((proc, data))

    def send(self, frame):
        try:
            os.write(self.fd, frame)
        except OSError:
            self.lost.emit()

    def request(self, proc, data=b"", want=None, timeout=2.0):
        """Envía y devuelve (proc, datos) del primer mensaje con proc==want (por defecto, proc+1)."""
        want = want if want is not None else proc + 1
        with self._lock:
            while not self._q.empty():
                self._q.get_nowait()
            self.send(px.frame(proc, data))
            return self._wait(want, timeout)

    def _wait(self, want, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                p, d = self._q.get(timeout=max(0.01, end - time.time()))
            except queue.Empty:
                break
            if p == want:
                return p, d
            if p == px.NACK:
                raise DeviceError("La pedalera rechazó la orden (NACK).")
        raise DeviceError("La pedalera no respondió.")

    # --- lectura ---
    def identify(self):
        _, d = self.request(px.WHO_AM_I_REQ, b"\x7f\x7f\x7f")
        if d[2:3] != bytes([px.PRODUCT_RP500]):
            raise DeviceError("El dispositivo no es una RP500.")

    def config(self):
        _, d = self.request(px.CONFIG_REQ)
        return {"os": d[0], "bank": d[5], "preset": d[6]} if len(d) > 6 else {}

    def names(self, bank):
        _, d = self.request(px.NAMES_REQ, bytes([bank]))
        n, out, i = d[1], [], 2
        while len(out) < n and i < len(d):
            j = d.index(b"\0", i)
            out.append(d[i:j].decode("latin1").strip())
            i = j + 1
        return out

    def linkable(self):
        """Parámetros asignables al pedal: [(id, posición)], el primero es «None» (0, 0)."""
        _, d = self.request(px.LINKABLE_REQ, b"\x00\x01", want=px.LINKABLE)
        n = (d[2] << 8) | d[3]
        return [((d[4 + i * 3] << 8) | d[5 + i * 3], d[6 + i * 3]) for i in range(n)]

    def read_preset(self, bank=px.BANK_EDIT, idx=0):
        """-> (nombre, {(id, pos): valor}). Lee START, los bloques de parámetros y END."""
        with self._lock:
            while not self._q.empty():
                self._q.get_nowait()
            self.send(px.frame(px.PRESET_REQ, bytes([bank, idx])))
            _, d = self._wait(px.PRESET_START, 2.0)
            end = d.index(b"\0", 2)
            name, params = d[2:end].decode("latin1").strip(), {}
            while True:
                p, d = self._wait_any((px.PRESET_PARAMS, px.PRESET_END), 2.0)
                if p == px.PRESET_END:
                    break
                total, i = (d[0] << 8) | d[1], 2
                for _ in range(total):
                    pid, pos, val, n = px.dec_param(d[i:])
                    params[(pid, pos)] = val
                    i += n
            return name, params

    def _wait_any(self, wants, timeout):
        end = time.time() + timeout
        while time.time() < end:
            try:
                p, d = self._q.get(timeout=max(0.01, end - time.time()))
            except queue.Empty:
                break
            if p in wants:
                return p, d
        raise DeviceError("La pedalera no respondió.")

    # --- escritura ---
    def set_param(self, pid, pos, val):
        self.send(px.param_set(pid, pos, val))

    def load_preset(self, bank, idx):
        self.send(px.frame(px.MOVE_PRESET, bytes([bank, idx, px.BANK_EDIT, 0, 0, 1])))

    def store_preset(self, idx, name):
        """Guarda el buffer de edición en el preset de usuario idx con ese nombre."""
        self.send(px.frame(px.MOVE_PRESET, bytes([px.BANK_EDIT, 0, px.BANK_USER, idx])
                           + name.encode("latin1", "replace")[:11] + b"\0\x01"))

    def send_preset(self, name, params):
        """Carga un preset completo en el buffer de edición (RAM), como hace gdigi al abrir un archivo."""
        self.send(px.frame(px.PRESET_START, bytes([px.BANK_EDIT, 0]) + name.encode("latin1", "replace")[:11]
                           + b"\0\0\x02"))
        items = list(params.items())
        body = bytes([len(items) >> 8, len(items) & 0xFF])
        for (pid, pos), val in items:
            body += bytes([pid >> 8, pid & 0xFF, pos]) + px.enc_value(val)
        self.send(px.frame(px.PRESET_PARAMS, body))
