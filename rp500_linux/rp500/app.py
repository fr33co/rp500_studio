"""Ventana principal de RP500 Studio."""
import json
import os
import sys
import time
import xml.etree.ElementTree as ET

from PyQt5 import QtCore, QtGui, QtWidgets

from . import device, files, model, theme
from . import protocol as px
from .widgets import Card, ChainButton, FlowLayout, GlowPanel, Knob, OverlayCombo, Switch

BACKUPS = os.path.join(os.path.expanduser("~/.local/share/rp500-studio"), "backups")


class SaveDialog(QtWidgets.QDialog):
    """Elige el preset de usuario a sobrescribir y su nombre (lista visible, sin desplegables nativos)."""

    def __init__(self, parent, names, start, name):
        super().__init__(parent)
        self.setWindowTitle("Guardar preset")
        self.setMinimumSize(380, 520)
        lay = QtWidgets.QVBoxLayout(self)
        lay.addWidget(QtWidgets.QLabel("Preset de usuario que se sobrescribirá:"))
        self.list = QtWidgets.QListWidget()
        for i, n in enumerate(names):
            self.list.addItem(f"{i + 1:02d}   {n}")
        self.list.setCurrentRow(start)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        lay.addWidget(self.list, 1)
        lay.addWidget(QtWidgets.QLabel("Nombre (máx. 11 caracteres):"))
        self.edit = QtWidgets.QLineEdit(name[:11])
        self.edit.setMaxLength(11)
        lay.addWidget(self.edit)
        box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        lay.addWidget(box)

    def slot(self):
        return self.list.currentRow()

    def name(self):
        return self.edit.text()


class ConnectPage(QtWidgets.QWidget):
    chosen = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        lay = QtWidgets.QVBoxLayout(self)
        lay.setAlignment(QtCore.Qt.AlignCenter)
        title = QtWidgets.QLabel("RP500 Studio")
        title.setStyleSheet("font-size: 34px; font-weight: bold;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        self.hint = QtWidgets.QLabel()
        self.hint.setAlignment(QtCore.Qt.AlignCenter)
        self.card = QtWidgets.QPushButton("DigiTech RP500   ·   USB")
        self.card.setObjectName("devcard")
        self.card.setFixedSize(360, 72)
        self.card.clicked.connect(self.chosen)
        for w in (title, self.hint):
            lay.addWidget(w)
        lay.addSpacing(18)
        lay.addWidget(self.card, 0, QtCore.Qt.AlignCenter)
        self.refresh()

    def refresh(self):
        ok = device.pedal_present()
        self.card.setVisible(ok)
        self.hint.setText("Pulsa el dispositivo para conectar." if ok else
                          "Conecta la RP500 por USB y enciéndela…")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RP500 Studio")
        self.resize(1180, 740)
        self.setMinimumSize(980, 600)
        self.themes = theme.load_themes()
        self.catalog = model.load_catalog()
        self.blocks = model.chain(self.catalog)
        self.pedal = None
        self.values = {}          # {(id, posición): valor crudo} del buffer de edición
        self.bank = px.BANK_USER
        self.cur_slot = None      # preset de la lista que está cargado
        self.sel = 0              # bloque seleccionado en la cadena
        self.knobs = {}           # {(id, pos): Knob} del bloque visible
        self.types = {}           # {(type_id, pos): QComboBox}
        self.syncing = False
        self.mods = model.load_modifiers()
        self.linkable = []

        self.stack = QtWidgets.QStackedWidget()
        self.setCentralWidget(self.stack)
        self.connect_page = ConnectPage()
        self.connect_page.chosen.connect(self.connect_pedal)
        self.stack.addWidget(self.connect_page)
        self.stack.addWidget(self._build_main())
        self._build_menu()
        self.apply_theme(self.themes[theme.DEFAULT])

        self.poll = QtCore.QTimer(self, interval=1500)
        self.poll.timeout.connect(self._poll)
        self.poll.start()
        self.refresh_timer = QtCore.QTimer(self, singleShot=True, interval=150)
        self.refresh_timer.timeout.connect(self.refresh_preset)

    # ---------- construcción ----------
    def _build_menu(self):
        fm = self.menuBar().addMenu("&Archivo")
        fm.addAction("Exportar preset actual…", self.export_preset)
        fm.addAction("Importar preset al buffer…", self.import_preset)
        fm.addSeparator()
        fm.addAction("Respaldar los 100 presets de usuario…", self.backup_bank)
        m = self.menuBar().addMenu("&Tema")
        grp = QtWidgets.QActionGroup(self)
        for label, t in self.themes.items():
            a = m.addAction(label)
            a.setCheckable(True)
            a.setChecked(label == theme.DEFAULT)
            grp.addAction(a)
            a.triggered.connect(lambda _=False, t=t: self.apply_theme(t))
        self.menuBar().addMenu("&Ayuda").addAction("Acerca de", lambda: QtWidgets.QMessageBox.about(
            self, "RP500 Studio", "Editor no oficial para la DigiTech RP500.\nProtocolo basado en gdigi (GPLv3).\n"
            "Úsalo bajo tu responsabilidad: escribe en la memoria de la pedalera."))

    def _build_main(self):
        root = QtWidgets.QWidget()
        root.setObjectName("root")
        h = QtWidgets.QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        side = QtWidgets.QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(250)
        sl = QtWidgets.QVBoxLayout(side)
        self.status_dev = QtWidgets.QLabel("RP500 · conectada")
        self.status_dev.setStyleSheet("font-weight: bold;")
        self.bank_box = OverlayCombo()
        self.bank_box.addItems(["Presets de usuario", "Presets de sistema"])
        self.bank_box.activated.connect(self.change_bank)
        self.search = QtWidgets.QLineEdit(placeholderText="Buscar preset…")
        self.search.textChanged.connect(self.filter_presets)
        self.plist = QtWidgets.QListWidget()
        self.plist.currentRowChanged.connect(self.pick_preset)
        for w in (self.status_dev, self.bank_box, self.search, self.plist):
            sl.addWidget(w)
        h.addWidget(side)

        right = QtWidgets.QVBoxLayout()
        right.setContentsMargins(22, 18, 22, 14)
        top = QtWidgets.QHBoxLayout()
        self.title = QtWidgets.QLabel("—")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.save_btn = QtWidgets.QPushButton("Guardar en…")
        self.save_btn.clicked.connect(self.save_as)
        self.reload_btn = QtWidgets.QPushButton("Releer")
        self.reload_btn.clicked.connect(self.refresh_preset)
        top.addWidget(self.title, 1)
        top.addWidget(self.reload_btn)
        top.addWidget(self.save_btn)
        right.addLayout(top)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(8)
        self.chips = []
        for i, (name, color, items) in enumerate(self.blocks):
            c = ChainButton(name, color, can_toggle=any(it["on_id"] >= 0 for it in items))
            c.selected.connect(lambda i=i: self.select_block(i))
            c.toggled.connect(lambda on, i=i: self.toggle_block(i, on))
            self.chips.append(c)
            row.addWidget(c)
        right.addSpacing(10)
        right.addLayout(row)

        self.panel = GlowPanel()
        self.panel_lay = QtWidgets.QVBoxLayout(self.panel)
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea, QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.setWidget(self.panel)
        right.addSpacing(10)
        right.addWidget(scroll, 1)
        self.statusbar = QtWidgets.QLabel("")
        self.statusbar.setStyleSheet("color: gray;")
        right.addWidget(self.statusbar)
        h.addLayout(right, 1)
        return root

    def apply_theme(self, t):
        theme.set_current(t)
        self.setStyleSheet(theme.stylesheet(t))
        if self.pedal:
            self.build_panel()
        for c in self.chips:
            c.update()

    def say(self, text):
        self.statusbar.setText(text)

    # ---------- conexión ----------
    def _poll(self):
        if self.stack.currentIndex() == 0:
            self.connect_page.refresh()
        elif not device.pedal_present():
            self.disconnect_pedal("RP500 desconectada.")

    def connect_pedal(self):
        try:
            self.pedal = device.Pedal()
            self.pedal.identify()
            self.pedal.gui_mode(True)
            cfg = self.pedal.config()
            self.pedal.param_changed.connect(self.on_param)
            self.pedal.preset_moved.connect(lambda b, i: self.refresh_timer.start())
            self.pedal.lost.connect(lambda: self.disconnect_pedal("Se perdió la conexión."))
            self.stack.setCurrentIndex(1)
            self.load_names()
            self.refresh_preset()
            self.say(f"Conectada · firmware {cfg.get('os', '?')}")
        except device.DeviceError as e:
            if self.pedal:
                self.pedal.close()
                self.pedal = None
            QtWidgets.QMessageBox.warning(self, "RP500", str(e))

    def disconnect_pedal(self, why):
        if self.pedal:
            self.pedal.close()
            self.pedal = None
        self.stack.setCurrentIndex(0)
        self.connect_page.hint.setText(why)

    def closeEvent(self, e):
        if self.pedal:
            self.pedal.close()
        super().closeEvent(e)

    # ---------- presets ----------
    def load_names(self):
        self.syncing = True
        self.plist.clear()
        try:
            names = self.pedal.names(self.bank)
        except device.DeviceError as e:
            names = []
            self.say(str(e))
        for i, n in enumerate(names):
            self.plist.addItem(f"{i + 1:02d}   {n}")
        self.filter_presets(self.search.text())
        self.syncing = False

    def filter_presets(self, text):
        for i in range(self.plist.count()):
            self.plist.item(i).setHidden(text.lower() not in self.plist.item(i).text().lower())

    def change_bank(self, i):
        self.bank = (px.BANK_USER, px.BANK_SYSTEM)[i]
        self.save_btn.setEnabled(self.bank == px.BANK_USER)
        if self.pedal:
            self.load_names()

    def pick_preset(self, row):
        if self.syncing or row < 0 or not self.pedal:
            return
        self.cur_slot = row
        self.pedal.load_preset(self.bank, row)
        self.refresh_timer.start()

    def refresh_preset(self):
        if not self.pedal:
            return
        try:
            name, params = self.pedal.read_preset()
        except device.DeviceError as e:
            self.say(str(e))
            return
        self.values = params
        try:
            self.linkable = self.pedal.linkable()
        except device.DeviceError:
            pass
        self.title.setText(name or "—")
        self.build_panel()
        self.sync_chips()
        self.say(f"Preset «{name}» leído · {len(params)} parámetros")

    # ---------- cadena y panel ----------
    def block_on(self, items):
        for it in items:
            if it["on_id"] >= 0:
                v = self.values.get((it["on_id"], it["position"]), 1)
                return (not v) if it["on_id"] == model.AMP_BYPASS_ID else bool(v)
        return True

    def sync_chips(self):
        for i, (c, (_, _, items)) in enumerate(zip(self.chips, self.blocks)):
            c.setOn(self.block_on(items))
            c.setActive(i == self.sel)

    def select_block(self, i):
        self.sel = i
        self.build_panel()
        self.sync_chips()

    def toggle_block(self, i, on):
        for it in self.blocks[i][2]:
            if it["on_id"] >= 0:
                raw = (0 if on else 1) if it["on_id"] == model.AMP_BYPASS_ID else int(on)
                self.send(it["on_id"], it["position"], raw)
                break
        self.sync_chips()

    def send(self, pid, pos, val):
        self.values[(pid, pos)] = val
        if self.pedal:
            self.pedal.set_param(pid, pos, val)
            self.say(f"Enviado a la RP500: id {pid} pos {pos} = {val}")
        else:
            self.say("Sin conexión con la RP500: el cambio no se envió.")

    def clear_panel(self):
        while self.panel_lay.count():
            w = self.panel_lay.takeAt(0)
            if w.widget():
                w.widget().deleteLater()
        self.knobs.clear()
        self.types.clear()

    @staticmethod
    def card_title(name, it):
        if it["label"] and not it["label"].startswith("Enable"):
            return it["label"]
        return {"Amp": "Amplificador", "Equalizer": "Ecualizador", "Compressor": "Compresor", "Noisegate": "Puerta de ruido",
                "Distortion": "Distorsión", "Mod/FX": "Modulación / FX"}.get(name, name)

    def make_card(self, name, title, color, on_items=None):
        """Tarjeta con cabecera: categoría, título, interruptor (si el bloque se enciende) y un hueco para el tipo."""
        card = Card(color)
        lay = QtWidgets.QVBoxLayout(card)
        lay.setContentsMargins(26, 18, 22, 20)
        lay.setSpacing(12)
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(12)
        titles = QtWidgets.QVBoxLayout()
        titles.setSpacing(0)
        cat = QtWidgets.QLabel(name.upper())
        cat.setStyleSheet(f"color: {color}; font-size: 10px; font-weight: bold; letter-spacing: 2px;")
        ttl = QtWidgets.QLabel(title)
        ttl.setStyleSheet("font-size: 19px; font-weight: bold;")
        titles.addWidget(cat)
        titles.addWidget(ttl)
        head.addLayout(titles)
        head.addStretch(1)
        lay.addLayout(head)
        if on_items is not None and any(it["on_id"] >= 0 for it in on_items):
            sw = Switch(color)
            sw.setOn(self.block_on(on_items))
            sw.toggled.connect(lambda on: (self.toggle_block(self.sel, on), sw.setOn(on)))
            head.addWidget(sw)
        return card, lay, head

    @staticmethod
    def pill_style(color):
        c = QtGui.QColor(color)
        return (f"QComboBox#type {{ background: rgba({c.red()},{c.green()},{c.blue()},0.16); border: 1px solid {color};"
                f" color: {color}; }}")

    def add_knob(self, flow, p, color):
        v = p["values"]
        lo, hi = model.value_range(v)
        k = Knob(p["label"], lo, hi, color, fmt=lambda raw, v=v: model.format_value(v, raw))
        k.setValue(self.values.get((p["id"], p["position"]), lo))
        k.valueChanged.connect(lambda raw, p=p: self.send(p["id"], p["position"], raw))
        self.knobs[(p["id"], p["position"])] = k
        flow.addWidget(k)

    def build_panel(self):
        self.clear_panel()
        name, color, items = self.blocks[self.sel]
        self.panel.setColor(color)
        if name == "Pedal":
            return self.build_pedal_panel(color)
        for it in items:
            if not it["types"]:
                continue
            card, lay, head = self.make_card(name, self.card_title(name, it), color,
                                             items if it is items[-1] or len(items) == 1 else None)
            cur = it["types"][0]
            if it["type_id"] >= 0:
                tv = self.values.get((it["type_id"], it["position"]))
                combo = OverlayCombo()
                combo.setObjectName("type")
                for t in it["types"]:
                    combo.addItem(t["label"], t["type"])
                idx = max(0, combo.findData(tv))
                combo.setCurrentIndex(idx)
                cur = it["types"][idx]
                combo.activated.connect(lambda _, c=combo, it=it: self.change_type(it, c.currentData()))
                combo.setStyleSheet(self.pill_style(color))
                head.insertWidget(1, combo)
                self.types[(it["type_id"], it["position"])] = combo
            flow = FlowLayout(spacing=10)
            for p in cur["params"]:
                if p["values"]:
                    self.add_knob(flow, p, color)
            if flow.count():
                lay.addLayout(flow)
            else:
                note = QtWidgets.QLabel("Este tipo no tiene parámetros ajustables.")
                note.setStyleSheet(f"color: {theme.current['kTextMuted']};")
                lay.addWidget(note)
            self.panel_lay.addWidget(card)
        self.panel_lay.addStretch(1)

    def build_pedal_panel(self, color):
        card, lay, head = self.make_card("Pedal de expresión", "Asignación", color)
        combo = OverlayCombo()
        combo.setObjectName("type")
        combo.setMaxVisibleItems(20)
        for pid, pos in self.linkable:
            m = self.mods.get((pid, pos))
            combo.addItem(m["label"] if m else f"id {pid} pos {pos}", (pos << 16) | pid)
        cur = self.values.get((model.EXP_ASSIGN, model.EXP_POS), 0)
        combo.setCurrentIndex(max(0, combo.findData(cur)))
        combo.activated.connect(lambda _, c=combo: self.change_pedal(c.currentData()))
        combo.setStyleSheet(self.pill_style(color))
        head.insertWidget(1, combo)
        m = self.mods.get((cur & 0xFFFF, cur >> 16))
        if m and m["values"]:
            v = m["values"]
            flow = FlowLayout(spacing=10)
            for label, pid in (("Min", model.EXP_MIN), ("Max", model.EXP_MAX)):
                self.add_knob(flow, {"label": label, "id": pid, "position": model.EXP_POS, "values": v}, color)
            lay.addLayout(flow)
        self.panel_lay.addWidget(card)
        self.panel_lay.addStretch(1)

    def change_pedal(self, packed):
        self.send(model.EXP_ASSIGN, model.EXP_POS, packed)
        self.refresh_timer.start(250)   # Min/Max cambian de rango con el parámetro asignado

    def change_type(self, it, t):
        self.send(it["type_id"], it["position"], t)
        self.refresh_timer.start(250)   # la pedalera responde con los valores por defecto del nuevo tipo

    def on_param(self, pid, pos, val):
        self.values[(pid, pos)] = val
        k = self.knobs.get((pid, pos))
        if k:
            k.setValue(val)
        c = self.types.get((pid, pos))
        if c and c.currentData() != val:
            self.refresh_timer.start()
        if any(it["on_id"] == pid for _, _, its in self.blocks for it in its):
            self.sync_chips()
        self.say(f"Desde la pedalera: id {pid} pos {pos} = {val}")

    # ---------- archivos ----------
    def export_preset(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Exportar preset", f"{self.title.text().strip()}.rp500p",
                                                        "Preset RP500 (*.rp500p)")
        if path:
            files.write_rp500p(path, self.title.text(), self.values, self.catalog, self.mods)
            self.say(f"Exportado a {path}")

    def import_preset(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Importar preset", "",
                                                        "Preset RP500 (*.rp500p *.json)")
        if not path or not self.pedal:
            return
        try:
            name, params = files.read_preset_file(path)
            if not params:
                raise ValueError("no contiene parámetros")
            self.pedal.send_preset(name, params)
        except (OSError, ValueError, KeyError, ET.ParseError) as e:
            QtWidgets.QMessageBox.warning(self, "Importar", f"Archivo no válido: {e}")
            return
        self.refresh_timer.start(400)
        self.say("Preset cargado en el buffer de edición (no guardado en flash).")

    def backup_bank(self):
        if not self.pedal:
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Respaldo", f"rp500_usuario_{time.strftime('%Y%m%d')}.json",
                                                        "Respaldo (*.json)")
        if not path:
            return
        out = []
        try:
            for i in range(100):
                self.say(f"Leyendo preset {i + 1}/100…")
                QtWidgets.QApplication.processEvents()
                n, v = self.pedal.read_preset(px.BANK_USER, i)
                out.append({"name": n, "params": [[a, b, c] for (a, b), c in v.items()]})
            with open(path, "w") as f:
                json.dump(out, f)
        except (device.DeviceError, OSError) as e:
            QtWidgets.QMessageBox.warning(self, "Respaldo", str(e))
            return
        self.say(f"Respaldo de {len(out)} presets guardado en {path}")

    # ---------- guardar ----------
    def save_as(self):
        if not self.pedal:
            return
        names = self.pedal.names(px.BANK_USER)
        start = self.cur_slot if self.bank == px.BANK_USER and self.cur_slot is not None else 0
        dlg = SaveDialog(self, names, start, self.title.text())
        if dlg.exec_() != QtWidgets.QDialog.Accepted:
            return
        idx, name = dlg.slot(), dlg.name()
        if QtWidgets.QMessageBox.question(self, "Confirmar", f"Se sobrescribirá «{names[idx]}» (nº {idx + 1}) "
                                          f"con «{name[:11]}». Se guarda una copia del original.") \
                != QtWidgets.QMessageBox.Yes:
            return
        try:
            old_name, old = self.pedal.read_preset(px.BANK_USER, idx)
            os.makedirs(BACKUPS, exist_ok=True)
            with open(os.path.join(BACKUPS, f"user{idx + 1:02d}_{time.strftime('%Y%m%d_%H%M%S')}.json"), "w") as f:
                json.dump({"name": old_name, "params": [[i, p, v] for (i, p), v in old.items()]}, f)
            self.pedal.store_preset(idx, name[:11])
            time.sleep(0.5)
            self.say(f"Guardado en {idx + 1:02d}. Respaldo en {BACKUPS}")
            self.load_names()
        except (device.DeviceError, OSError) as e:
            QtWidgets.QMessageBox.warning(self, "No se pudo guardar", str(e))


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("RP500 Studio")
    app.setDesktopFileName("rp500-studio")
    svg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "app_icon.svg")
    app.setWindowIcon(QtGui.QIcon.fromTheme("rp500-studio", QtGui.QIcon(svg)))
    w = MainWindow()
    w.showMaximized()
    sys.exit(app.exec_())
