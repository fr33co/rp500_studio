"""Componentes pintados a mano: perilla de 270° y botón de la cadena de efectos."""
import math

from PyQt5 import QtCore, QtGui, QtWidgets

from . import theme


def col(key):
    return QtGui.QColor(theme.current.get(key, "#888888"))


class Knob(QtWidgets.QWidget):
    """Perilla con arco de 270°, resplandor, aguja y valor en píldora. Arrastre vertical o rueda."""
    valueChanged = QtCore.pyqtSignal(int)

    def __init__(self, label, vmin, vmax, color, fmt=str, parent=None):
        super().__init__(parent)
        self.label, self.vmin, self.vmax, self.color, self.fmt = label, vmin, vmax, color, fmt
        self._v, self._drag, self._hover = vmin, None, False
        self.setFixedSize(100, 132)
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
        cx, cy, d = 50.0, 42.0, 66.0
        r = QtCore.QRectF(cx - d / 2, cy - d / 2, d, d)
        # pista y resplandor del arco activo
        p.setPen(QtGui.QPen(col("kElevated"), 6, cap=QtCore.Qt.RoundCap))
        p.drawArc(r, -135 * 16, -270 * 16)
        span = int(-270 * max(frac, 0.003) * 16)
        glow = QtGui.QColor(c)
        glow.setAlpha(110 if self._hover or self._drag else 60)
        p.setPen(QtGui.QPen(glow, 13, cap=QtCore.Qt.RoundCap))
        p.drawArc(r, -135 * 16, span)
        grad = QtGui.QConicalGradient(r.center(), 225)
        grad.setColorAt(0.0, c.lighter(135))
        grad.setColorAt(0.75, c)
        p.setPen(QtGui.QPen(QtGui.QBrush(grad), 6, cap=QtCore.Qt.RoundCap))
        p.drawArc(r, -135 * 16, span)
        # cuerpo de la perilla con aguja
        body = r.adjusted(11, 11, -11, -11)
        bg = QtGui.QRadialGradient(body.center() - QtCore.QPointF(0, 6), body.width() * 0.7)
        bg.setColorAt(0, col("kElevated").lighter(125))
        bg.setColorAt(1, col("kCard").darker(115))
        p.setPen(QtGui.QPen(col("kBorder"), 1))
        p.setBrush(bg)
        p.drawEllipse(body)
        ang = math.radians(225 - 270 * frac)
        rad = body.width() / 2
        p.setPen(QtGui.QPen(c, 3, cap=QtCore.Qt.RoundCap))
        p.drawLine(QtCore.QPointF(cx + rad * 0.35 * math.cos(ang), cy - rad * 0.35 * math.sin(ang)),
                   QtCore.QPointF(cx + rad * 0.82 * math.cos(ang), cy - rad * 0.82 * math.sin(ang)))
        # valor en píldora y etiqueta
        f = p.font()
        f.setPointSizeF(9.5)
        f.setBold(True)
        p.setFont(f)
        pill = QtCore.QRectF(8, 82, 84, 22)
        p.setPen(QtCore.Qt.NoPen)
        fill = QtGui.QColor(c)
        fill.setAlpha(34)
        p.setBrush(fill)
        p.drawRoundedRect(pill, 11, 11)
        p.setPen(c.lighter(115))
        p.drawText(pill, QtCore.Qt.AlignCenter, self.fmt(self._v))
        f.setBold(False)
        f.setPointSizeF(9)
        p.setFont(f)
        p.setPen(col("kTextSecondary"))
        p.drawText(QtCore.QRectF(0, 106, 100, 26), QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop
                   | QtCore.Qt.TextWordWrap, self.label)


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


class Card(QtWidgets.QFrame):
    """Tarjeta de efecto: degradado, borde sutil, barra y resplandor del color de la categoría."""

    def __init__(self, color, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor(color)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, False)

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        r = QtCore.QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        path = QtGui.QPainterPath()
        path.addRoundedRect(r, 18, 18)
        g = QtGui.QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, col("kCard").lighter(108))
        g.setColorAt(1, col("kSurface"))
        p.fillPath(path, g)
        p.save()
        p.setClipPath(path)
        glow = QtGui.QRadialGradient(r.topRight() + QtCore.QPointF(-30, 30), 260)
        top = QtGui.QColor(self.color)
        top.setAlpha(46)
        glow.setColorAt(0, top)
        glow.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(r, glow)
        p.fillRect(QtCore.QRectF(0, 0, 5, self.height()), self.color)
        p.restore()
        edge = QtGui.QColor(self.color)
        edge.setAlpha(70)
        p.setPen(QtGui.QPen(edge, 1))
        p.drawPath(path)


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
    """Fondo del panel de detalle: resplandor suave del color del bloque seleccionado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.color = QtGui.QColor("#888888")
        self.setStyleSheet("background: transparent;")

    def setColor(self, c):
        self.color = QtGui.QColor(c)
        self.update()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        g = QtGui.QRadialGradient(QtCore.QPointF(self.width() * 0.5, 0), max(self.width(), 400) * 0.7)
        c = QtGui.QColor(self.color)
        c.setAlpha(36)
        g.setColorAt(0, c)
        g.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
        p.fillRect(self.rect(), g)


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
    """Bloque de la cadena: píldora con nombre, punto de encendido y color de categoría."""
    selected = QtCore.pyqtSignal()
    toggled = QtCore.pyqtSignal(bool)

    def __init__(self, name, color, can_toggle=True, parent=None):
        super().__init__(parent)
        self.name, self.color, self.can_toggle = name, color, can_toggle
        self.on, self.active = True, False
        self.setMinimumSize(78, 64)
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
        return QtCore.QRectF(self.width() / 2 - 12, 9, 24, 22)

    def mousePressEvent(self, e):
        if self.can_toggle and self._dot().adjusted(-6, -6, 6, 6).contains(e.pos()):
            self.toggled.emit(not self.on)
        else:
            self.selected.emit()

    def paintEvent(self, _):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        c = QtGui.QColor(self.color)
        body = QtCore.QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
        p.setBrush(col("kElevated") if self.active else col("kCard"))
        p.setPen(QtGui.QPen(c if self.active else col("kBorder"), 2 if self.active else 1))
        p.drawRoundedRect(body, 12, 12)
        d = self._dot()
        lit = self.on or not self.can_toggle
        pen = QtGui.QPen(c if lit else col("kTextMuted"), 1.8, cap=QtCore.Qt.RoundCap, join=QtCore.Qt.RoundJoin)
        if lit:
            glow = QtGui.QRadialGradient(d.center(), 22)
            gc = QtGui.QColor(c)
            gc.setAlpha(60)
            glow.setColorAt(0, gc)
            glow.setColorAt(1, QtGui.QColor(0, 0, 0, 0))
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(glow)
            p.drawEllipse(d.center(), 22, 22)
        draw_icon(p, self.name, d, pen)
        f = p.font()
        f.setPointSizeF(9.5)
        f.setBold(True)
        p.setFont(f)
        p.setPen(col("kTextPrimary") if self.on else col("kTextMuted"))
        p.drawText(QtCore.QRectF(0, 34, self.width(), 24), QtCore.Qt.AlignCenter, self.name)


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
