"""Componentes pintados a mano: perilla de 270° y botón de la cadena de efectos."""
import math

from PyQt5 import QtCore, QtGui, QtWidgets

from . import theme


def col(key):
    return QtGui.QColor(theme.current.get(key, "#888888"))


class Knob(QtWidgets.QWidget):
    """Perilla de aparato: cuerpo metálico negro con aguja y aro de LEDs que se encienden hasta el valor.
    Arrastre vertical o rueda; `fmt` convierte el valor crudo en texto."""
    valueChanged = QtCore.pyqtSignal(int)
    LEDS = 15

    def __init__(self, label, vmin, vmax, color, fmt=str, parent=None):
        super().__init__(parent)
        self.label, self.vmin, self.vmax, self.color, self.fmt = label, vmin, vmax, color, fmt
        self._v, self._drag, self._hover = vmin, None, False
        self.setFixedSize(100, 148)
        self.setCursor(QtCore.Qt.SizeVerCursor)
        self.setToolTip(label)

    def value(self):
        return self._v

    def setValue(self, v, emit=False):
        v = max(self.vmin, min(self.vmax, int(v)))
        if v != self._v:
            self._v = v
            self.update()
            if emit:
                self.valueChanged.emit(v)

    def _span(self):
        return max(1, self.vmax - self.vmin)

    def mousePressEvent(self, e):
        self._drag = (e.y(), self._v)

    def mouseMoveEvent(self, e):
        if self._drag:
            # 160 px recorren todo el rango; los rangos cortos (etiquetas) avanzan por pasos enteros
            self.setValue(round(self._drag[1] + (self._drag[0] - e.y()) / 160.0 * self._span()), emit=True)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def wheelEvent(self, e):
        self.setValue(self._v + (1 if e.angleDelta().y() > 0 else -1), emit=True)

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = QtGui.QColor(self.color)
        frac = (self._v - self.vmin) / self._span()
        cx, cy = 50.0, 60.0
        # etiqueta grabada arriba
        f = p.font()
        f.setPointSizeF(8)
        f.setBold(True)
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.3)
        p.setFont(f)
        p.setPen(col("kTextSecondary"))
        text = self.label.upper().replace("BANDWIDTH", "BW")
        text = QtGui.QFontMetrics(f).elidedText(text, QtCore.Qt.ElideRight, 98)
        p.drawText(QtCore.QRectF(0, 0, 100, 14), QtCore.Qt.AlignCenter, text)
        # aro de LEDs: se encienden hasta el valor
        for i in range(self.LEDS):
            a = math.radians(225 - 270 * i / (self.LEDS - 1))
            pt = QtCore.QPointF(cx + 38 * math.cos(a), cy - 38 * math.sin(a))
            lit = frac >= i / (self.LEDS - 1) - 1e-6 and (frac > 0 or i == 0)
            if lit:
                g = QtGui.QRadialGradient(pt, 8)
                gc = QtGui.QColor(c)
                gc.setAlpha(120 if self._hover or self._drag else 80)
                g.setColorAt(0, gc)
                g.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
                p.setPen(QtCore.Qt.NoPen)
                p.setBrush(g)
                p.drawEllipse(pt, 8, 8)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(c.lighter(125) if lit else QtGui.QColor("#2a2a2d"))
            p.drawEllipse(pt, 2.6, 2.6)
        # sombra y cuerpo metálico con rebordes
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(QtGui.QColor(0, 0, 0, 120))
        p.drawEllipse(QtCore.QPointF(cx, cy + 2), 27, 27)
        metal = QtGui.QConicalGradient(QtCore.QPointF(cx, cy), 90)
        for pos, hexc in ((0.0, "#5a5a5f"), (0.15, "#26262a"), (0.35, "#74747a"), (0.5, "#1e1e22"),
                          (0.65, "#6a6a70"), (0.85, "#26262a"), (1.0, "#5a5a5f")):
            metal.setColorAt(pos, QtGui.QColor(hexc))
        p.setBrush(metal)
        p.drawEllipse(QtCore.QPointF(cx, cy), 26, 26)
        p.setPen(QtGui.QPen(QtGui.QColor("#0c0c0e"), 1.2))
        for i in range(36):                       # moleteado del borde
            a = math.radians(i * 10)
            p.drawLine(QtCore.QPointF(cx + 23.5 * math.cos(a), cy - 23.5 * math.sin(a)),
                       QtCore.QPointF(cx + 26 * math.cos(a), cy - 26 * math.sin(a)))
        top = QtGui.QRadialGradient(QtCore.QPointF(cx - 6, cy - 8), 30)
        top.setColorAt(0, QtGui.QColor("#3a3a40"))
        top.setColorAt(1, QtGui.QColor("#121215"))
        p.setPen(QtGui.QPen(QtGui.QColor("#050506"), 1))
        p.setBrush(top)
        p.drawEllipse(QtCore.QPointF(cx, cy), 20, 20)
        ang = math.radians(225 - 270 * frac)
        p.setPen(QtGui.QPen(QtGui.QColor("#f4f4f4"), 3, cap=QtCore.Qt.RoundCap))
        p.drawLine(QtCore.QPointF(cx + 8 * math.cos(ang), cy - 8 * math.sin(ang)),
                   QtCore.QPointF(cx + 18 * math.cos(ang), cy - 18 * math.sin(ang)))
        # valor en pantallita
        f.setPointSizeF(9.5)
        f.setBold(True)
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0)
        p.setFont(f)
        pill = QtCore.QRectF(10, 114, 80, 24)
        p.setPen(QtGui.QPen(QtGui.QColor("#000000"), 1))
        p.setBrush(QtGui.QColor("#120d03"))
        p.drawRoundedRect(pill, 5, 5)
        p.setPen(QtGui.QColor("#ffb52e"))
        p.drawText(pill, QtCore.Qt.AlignCenter, self.fmt(self._v))


class Lcd(QtWidgets.QWidget):
    """Pantalla LCD ámbar: número y nombre del preset, bloque/tipo seleccionado y último parámetro tocado."""
    AMBER = QtGui.QColor("#ffb52e")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._num, self._name, self._l2, self._l3 = "--", "—", "", ""
        self.setMinimumSize(420, 104)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)

    def setText(self, name):
        self._name = name or "—"
        self.update()

    def text(self):
        return self._name

    def setNumber(self, n):
        self._num = n
        self.update()

    def setInfo(self, l2, l3=None):
        self._l2 = l2
        if l3 is not None:
            self._l3 = l3
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(1, 1, self.width() - 2, self.height() - 2)
        p.setPen(QtGui.QPen(QtGui.QColor("#000000"), 3))
        g = QtGui.QLinearGradient(r.topLeft(), r.bottomLeft())
        g.setColorAt(0, QtGui.QColor("#241802"))
        g.setColorAt(1, QtGui.QColor("#0f0a01"))
        p.setBrush(g)
        p.drawRoundedRect(r, 10, 10)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 181, 46, 40), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRoundedRect(r.adjusted(5, 5, -5, -5), 7, 7)
        mono = QtGui.QFont("DejaVu Sans Mono")
        mono.setStyleHint(QtGui.QFont.Monospace)

        def text(rect, s, size, bold, alpha=255, flags=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter):
            mono.setPointSizeF(size)
            mono.setBold(bold)
            p.setFont(mono)
            glow = QtGui.QColor(self.AMBER)
            glow.setAlpha(int(alpha * 0.28))
            p.setPen(glow)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):      # resplandor
                p.drawText(rect.translated(dx, dy), flags, s)
            c = QtGui.QColor(self.AMBER)
            c.setAlpha(alpha)
            p.setPen(c)
            p.drawText(rect, flags, s)

        m = 18
        text(QtCore.QRectF(m, 8, 96, 52), self._num, 27, True)
        text(QtCore.QRectF(m + 100, 8, self.width() - m * 2 - 100, 52), self._name.upper(), 24, True)
        text(QtCore.QRectF(m, 60, self.width() - m * 2, 18), self._l2, 11, True, 230)
        text(QtCore.QRectF(m, 78, self.width() - m * 2, 18), self._l3, 10, False, 160)
        p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0, 40), 1))        # líneas de barrido
        for y in range(int(r.top()) + 4, int(r.bottom()) - 3, 3):
            p.drawLine(int(r.left()) + 4, y, int(r.right()) - 4, y)


class Switch(QtWidgets.QWidget):
    """Interruptor tipo píldora."""
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color, self.on = color, True
        self.setFixedSize(46, 26)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def setOn(self, on):
        if on != self.on:
            self.on = on
            self.update()

    def mousePressEvent(self, e):
        self.toggled.emit(not self.on)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = QtGui.QColor(self.color)
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(c if self.on else col("kElevated"))
        p.drawRoundedRect(QtCore.QRectF(1, 1, 44, 24), 12, 12)
        p.setBrush(QtGui.QColor("#ffffff") if self.on else col("kTextMuted"))
        p.drawEllipse(QtCore.QRectF(23 if self.on else 4, 4, 18, 18))


def draw_plate(p, r, accent=None, radius=12):
    """Placa del chasis: degradado negro, reborde y tornillos en las esquinas."""
    path = QtGui.QPainterPath()
    path.addRoundedRect(r, radius, radius)
    g = QtGui.QLinearGradient(r.topLeft(), r.bottomLeft())
    g.setColorAt(0, QtGui.QColor("#232326"))
    g.setColorAt(1, QtGui.QColor("#131315"))
    p.fillPath(path, g)
    p.setPen(QtGui.QPen(QtGui.QColor("#070708"), 1.5))
    p.drawPath(path)
    p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 22), 1))
    p.drawRoundedRect(r.adjusted(1.5, 1.5, -1.5, -1.5), radius - 1, radius - 1)
    for sx, sy in ((r.left() + 11, r.top() + 11), (r.right() - 11, r.top() + 11),
                   (r.left() + 11, r.bottom() - 11), (r.right() - 11, r.bottom() - 11)):
        sg = QtGui.QRadialGradient(QtCore.QPointF(sx - 1, sy - 1), 6)
        sg.setColorAt(0, QtGui.QColor("#6a6a70"))
        sg.setColorAt(1, QtGui.QColor("#2a2a2e"))
        p.setPen(QtGui.QPen(QtGui.QColor("#050506"), 1))
        p.setBrush(sg)
        p.drawEllipse(QtCore.QPointF(sx, sy), 4.2, 4.2)
        p.setPen(QtGui.QPen(QtGui.QColor("#0a0a0b"), 1.2))
        p.drawLine(QtCore.QPointF(sx - 2.4, sy + 1.2), QtCore.QPointF(sx + 2.4, sy - 1.2))
    if accent is not None:                                        # serigrafía: línea fina de color bajo la cabecera
        line = QtGui.QColor(accent)
        line.setAlpha(150)
        p.setPen(QtGui.QPen(line, 1.5))
        p.drawLine(QtCore.QPointF(r.left() + 26, r.top() + 64), QtCore.QPointF(r.right() - 26, r.top() + 64))


class Card(QtWidgets.QFrame):
    """Tarjeta de efecto con aspecto de placa del aparato."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        draw_plate(p, QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1), self.color)


class Plate(QtWidgets.QFrame):
    """Placa sin acento (contenedor de la fila de botones y de la pantalla)."""

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        draw_plate(p, QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1))


class FlowLayout(QtWidgets.QLayout):
    """Reparte los widgets en filas y salta de línea según el ancho disponible."""

    def __init__(self, parent=None, spacing=6):
        super().__init__(parent)
        self._items, self._sp = [], spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, w):
        return self._do(QtCore.QRect(0, 0, w, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QtCore.QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        return s + QtCore.QSize(m.left() + m.right(), m.top() + m.bottom())

    def _do(self, rect, test):
        x, y, line_h = rect.x(), rect.y(), 0
        for it in self._items:
            w, h = it.sizeHint().width(), it.sizeHint().height()
            if x + w > rect.right() + 1 and line_h > 0:
                x, y, line_h = rect.x(), y + line_h + self._sp, 0
            if not test:
                it.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), it.sizeHint()))
            x += w + self._sp
            line_h = max(line_h, h)
        return y + line_h - rect.y()


class GlowPanel(QtWidgets.QWidget):
    """Fondo del panel de detalle: chasis oscuro con un leve tinte del color del bloque seleccionado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor("#888888")
        self.setStyleSheet("background: transparent;")

    def setColor(self, c):
        self.color = QtGui.QColor(c)
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        g = QtGui.QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QtGui.QColor("#0e0e10"))
        g.setColorAt(1, QtGui.QColor("#09090a"))
        p.fillRect(self.rect(), g)
        rg = QtGui.QRadialGradient(QtCore.QPointF(self.width() * 0.5, 0), max(self.width(), 400) * 0.6)
        c = QtGui.QColor(self.color)
        c.setAlpha(22)
        rg.setColorAt(0, c)
        rg.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), rg)


def draw_icon(p, name, r, pen):
    """Glifos simples por categoría, dibujados en el rectángulo r."""
    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    cx, cy = x + w / 2, y + h / 2
    p.setPen(pen)
    p.setBrush(QtCore.Qt.NoBrush)
    path = QtGui.QPainterPath()
    if name == "Wah":
        path.moveTo(x + 2, y + h - 3); path.lineTo(x + w - 2, y + h - 11); path.lineTo(x + w - 2, y + h - 3); path.closeSubpath()
        path.moveTo(x + w * 0.35, y + h - 7); path.lineTo(x + w * 0.35, y + 3)
    elif name == "Compressor":
        path.moveTo(x + 3, y + 3); path.lineTo(cx - 2, cy); path.lineTo(x + 3, y + h - 3)
        path.moveTo(x + w - 3, y + 3); path.lineTo(cx + 2, cy); path.lineTo(x + w - 3, y + h - 3)
    elif name == "Distortion":
        path.moveTo(cx + 3, y + 1); path.lineTo(x + 5, cy + 2); path.lineTo(cx, cy + 2); path.lineTo(cx - 3, y + h - 1)
        path.lineTo(x + w - 5, cy - 2); path.lineTo(cx, cy - 2); path.closeSubpath()
    elif name == "Amp":
        path.addRoundedRect(QtCore.QRectF(x + 1, y + 3, w - 2, h - 6), 4, 4)
        for i in range(3):
            path.addEllipse(QtCore.QPointF(x + 6 + i * (w - 12) / 2, cy), 1.6, 1.6)
    elif name == "Cab":
        path.addRoundedRect(QtCore.QRectF(x + 3, y + 1, w - 6, h - 2), 4, 4)
        path.addEllipse(QtCore.QPointF(cx, cy + 2), 5.5, 5.5)
        path.addEllipse(QtCore.QPointF(cx, y + 6), 1.4, 1.4)
    elif name == "Equalizer":
        for i, hh in enumerate((0.35, 0.7, 0.5)):
            px = x + 4 + i * (w - 8) / 2
            path.moveTo(px, y + 2); path.lineTo(px, y + h - 2)
            path.addRect(QtCore.QRectF(px - 2.5, y + 2 + (h - 4) * (1 - hh) - 2, 5, 4))
    elif name == "Noisegate":
        for i in range(4):
            hh = (0.25, 0.5, 0.9, 0.9)[i] * (h - 4)
            path.moveTo(x + 4 + i * (w - 8) / 3, y + h - 2); path.lineTo(x + 4 + i * (w - 8) / 3, y + h - 2 - hh)
    elif name == "Mod/FX":
        path.moveTo(x + 1, cy)
        path.cubicTo(x + w * 0.2, y - 3, x + w * 0.4, y - 3, cx, cy)
        path.cubicTo(x + w * 0.6, y + h + 3, x + w * 0.8, y + h + 3, x + w - 1, cy)
    elif name == "Delay":
        for i, rr in enumerate((3, 5, 7)):
            path.addEllipse(QtCore.QPointF(x + 5 + i * (w - 10) / 2, cy), rr * 0.6, rr * 0.6 + 1)
    elif name == "Reverb":
        for rr in (4, 8, 12):
            path.addEllipse(QtCore.QPointF(x + 4, cy), rr, rr * 0.85)
    elif name == "Pedal":
        path.moveTo(x + 4, y + h - 2); path.lineTo(x + w - 4, y + h - 2); path.lineTo(x + w - 2, y + 3); path.lineTo(x + 6, y + 6)
        path.closeSubpath()
    else:
        path.addEllipse(r.adjusted(4, 4, -4, -4))
    p.drawPath(path)


class ChainButton(QtWidgets.QWidget):
    """Botón de la cadena: pulsador metálico con ícono y LED del color de la categoría."""
    selected = QtCore.pyqtSignal()
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, name, color, can_toggle=True, parent=None):
        super().__init__(parent)
        self.name, self.color, self.can_toggle = name, color, can_toggle
        self.on, self.active = True, False
        self.setMinimumSize(78, 78)
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def setOn(self, on):
        if on != self.on:
            self.on = on
            self.update()

    def setActive(self, a):
        self.active = a
        self.update()

    def _dot(self):
        return QtCore.QRectF(self.width() / 2 - 12, 11, 24, 22)

    def mousePressEvent(self, e):
        if self.can_toggle and self._dot().adjusted(-6, -6, 6, 6).contains(e.pos()):
            self.toggled.emit(not self.on)
        else:
            self.selected.emit()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = QtGui.QColor(self.color)
        lit = self.on or not self.can_toggle
        body = QtCore.QRectF(2, 2, self.width() - 4, self.height() - 4)
        g = QtGui.QLinearGradient(body.topLeft(), body.bottomLeft())
        g.setColorAt(0, QtGui.QColor("#4a4a50") if self.active else QtGui.QColor("#38383d"))
        g.setColorAt(1, QtGui.QColor("#1c1c20"))
        p.setPen(QtGui.QPen(c if self.active else QtGui.QColor("#08080a"), 2 if self.active else 1.5))
        p.setBrush(g)
        p.drawRoundedRect(body, 9, 9)
        p.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255, 36), 1))     # brillo del borde superior
        p.drawLine(QtCore.QPointF(body.left() + 9, body.top() + 1.5), QtCore.QPointF(body.right() - 9, body.top() + 1.5))
        d = self._dot()
        if lit:
            glow = QtGui.QRadialGradient(d.center(), 22)
            gc = QtGui.QColor(c)
            gc.setAlpha(60)
            glow.setColorAt(0, gc)
            glow.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(d.center(), 22, 22)
        draw_icon(p, self.name, d, QtGui.QPen(c if lit else col("kTextMuted"), 1.8, cap=QtCore.Qt.RoundCap,
                                              join=QtCore.Qt.RoundJoin))
        f = p.font()
        f.setPointSizeF(8.5)
        f.setBold(True)
        f.setLetterSpacing(QtGui.QFont.AbsoluteSpacing, 0.5)
        p.setFont(f)
        p.setPen(QtGui.QColor("#e8e8ea") if lit else QtGui.QColor("#6a6a70"))
        short = {"Equalizer": "EQ", "Compressor": "COMP", "Distortion": "DIST", "Noisegate": "GATE", "Reverb": "REV"}
        p.drawText(QtCore.QRectF(0, 40, self.width(), 18), QtCore.Qt.AlignCenter,
                   short.get(self.name, self.name).upper())
        # LED indicador
        led = QtCore.QPointF(self.width() / 2, 66)
        if lit:
            lg = QtGui.QRadialGradient(led, 10)
            lc = QtGui.QColor(c)
            lc.setAlpha(150)
            lg.setColorAt(0, lc)
            lg.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(lg)
            p.drawEllipse(led, 10, 10)
        p.setPen(QtGui.QPen(QtGui.QColor("#050506"), 1))
        p.setBrush(c.lighter(130) if lit else QtGui.QColor("#26262a"))
        p.drawEllipse(led, 3.6, 3.6)


class OverlayCombo(QtWidgets.QComboBox):
    """Combo cuya lista se abre DENTRO de la ventana: un clic la abre y se queda abierta.

    El desplegable nativo de Qt (ventana emergente) en Wayland se cierra al soltar el botón del ratón,
    obligando a mantenerlo pulsado. Aquí la lista es un widget hijo de la ventana: se elige con un clic,
    con las flechas + Enter, y se cierra con Esc o haciendo clic fuera.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._list = None

    def _ensure_list(self):
        if self._list is None:
            lst = QtWidgets.QListWidget(self.window())
            lst.setObjectName("overlaylist")
            lst.setFrameShape(QtWidgets.QFrame.NoFrame)
            lst.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
            lst.itemClicked.connect(self._picked)
            lst.itemActivated.connect(self._picked)
            lst.hide()
            self.destroyed.connect(lst.deleteLater)
            self._list = lst
        return self._list

    def showPopup(self):
        lst = self._ensure_list()
        if lst.isVisible():
            return self.hidePopup()
        lst.clear()
        for i in range(self.count()):
            it = QtWidgets.QListWidgetItem(self.itemIcon(i), self.itemText(i))
            lst.addItem(it)
        win = self.window()
        top_left = self.mapTo(win, QtCore.QPoint(0, self.height() + 2))
        h = max(120, min(460, win.height() - top_left.y() - 30))
        lst.setGeometry(top_left.x(), top_left.y(), self.width(), h)
        t = theme.current
        lst.setStyleSheet(
            f"QListWidget#overlaylist {{ background: {t.get('kCard', '#222')}; border: 1px solid {t.get('kAccent', '#3b9eff')};"
            f" border-radius: 6px; outline: none; }}"
            f"QListWidget#overlaylist::item {{ padding: 6px 8px; }}"
            f"QListWidget#overlaylist::item:hover {{ background: {t.get('kElevated', '#333')}; }}"
            f"QListWidget#overlaylist::item:selected {{ background: {t.get('kAccentDim', '#333')}; color: {t.get('kAccent', '#fff')}; }}")
        lst.setCurrentRow(self.currentIndex())
        lst.scrollToItem(lst.currentItem(), QtWidgets.QAbstractItemView.PositionAtCenter)
        lst.raise_()
        lst.show()
        lst.setFocus()
        QtWidgets.QApplication.instance().installEventFilter(self)

    def hidePopup(self):
        if self._list is not None and self._list.isVisible():
            self._list.hide()
            QtWidgets.QApplication.instance().removeEventFilter(self)

    def _picked(self, item):
        row = self._list.row(item)
        self.hidePopup()
        self.setCurrentIndex(row)
        self.activated.emit(row)

    def eventFilter(self, obj, e):
        if self._list is not None and self._list.isVisible():
            if e.type() == QtCore.QEvent.MouseButtonPress:
                w = QtWidgets.QApplication.widgetAt(e.globalPos())
                inside = w is not None and (w is self._list or self._list.isAncestorOf(w))
                if not inside and w is not self:
                    self.hidePopup()
            elif e.type() == QtCore.QEvent.KeyPress and e.key() == QtCore.Qt.Key_Escape:
                self.hidePopup()
                return True
        return super().eventFilter(obj, e)
