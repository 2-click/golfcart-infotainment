"""SplashScreen -- Startbildschirm mit "CUSHMAN" und Glanz-Animation.

Der Schriftzug ist mit einem metallischen Vertikalverlauf gefuellt; ein heller
Lichtstreifen wandert wiederholt darueber (Shine-Sweep). Nach kurzer Haltezeit
blendet der Splash aus und gibt das darunterliegende Cockpit frei.

Wird als Overlay-Child ueber dem MainWindow gezeigt -> das Ausblenden enthuellt
direkt das bereits gerenderte UI (kein Fensterwechsel).
"""

from PySide6.QtCore import Qt, QTimer, QRectF, Signal, QPropertyAnimation
from PySide6.QtGui import (QPainter, QColor, QFont, QFontMetricsF, QPainterPath,
                           QBrush, QPen, QLinearGradient)
from PySide6.QtWidgets import QWidget, QGraphicsOpacityEffect

from . import theme

LOGO = "CUSHMAN"
SUBTITLE = "RUNGE ENGINEERING"


class SplashScreen(QWidget):
    finished = Signal()

    SWEEPS = 1            # Anzahl Lichtstreifen-Durchlaeufe vor dem Ausblenden
    FADE_MS = 600         # Dauer des Ausblendens
    SWEEP_STEP = 0.013    # Fortschritt des Lichtstreifens pro Frame

    def __init__(self, parent=None):
        super().__init__(parent)
        self._t = -0.2     # Position des Lichtstreifens (-0.2 .. 1.2)
        self._sweeps = 0   # abgeschlossene Durchlaeufe
        self._fading = False
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 fps

    def _tick(self):
        self._t += self.SWEEP_STEP
        if self._t > 1.2:
            self._sweeps += 1
            if self._sweeps >= self.SWEEPS:
                self._begin_fade()  # nach dem letzten Sweep ausblenden
                return
            self._t = -0.2
        self.update()

    def _logo_font(self) -> QFont:
        f = QFont(theme.SANS_FAMILY)
        f.setPixelSize(max(56, int(self.height() * 0.23)))
        f.setWeight(QFont.Black)
        return f

    def _logo_path(self) -> QPainterPath:
        """CUSHMAN als Pfad, mit Tracking zwischen den Buchstaben, zentriert."""
        font = self._logo_font()
        fm = QFontMetricsF(font)
        tracking = fm.height() * 0.10
        widths = [fm.horizontalAdvance(ch) for ch in LOGO]
        total = sum(widths) + tracking * (len(LOGO) - 1)
        x = (self.width() - total) / 2
        baseline = self.height() / 2 + (fm.ascent() - fm.descent()) / 2
        path = QPainterPath()
        for ch, w in zip(LOGO, widths):
            path.addText(x, baseline, font, ch)
            x += w + tracking
        return path

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.TextAntialiasing, True)

        # Hintergrund (flache Fuellung -- bewusst kein Verlauf, das bandet auf
        # dem Produktionsdisplay)
        p.fillRect(self.rect(), theme.BG_DEEP)

        path = self._logo_path()
        rect = path.boundingRect()

        # Metallische Grundfuellung (Chrome-Verlauf)
        steel = QLinearGradient(0, rect.top(), 0, rect.bottom())
        steel.setColorAt(0.0, QColor("#aeb9c5"))
        steel.setColorAt(0.49, QColor("#6c7783"))
        steel.setColorAt(0.51, QColor("#525c68"))
        steel.setColorAt(1.0, QColor("#828d99"))
        p.fillPath(path, QBrush(steel))

        # Dezente Kontur fuer Tiefe
        p.setPen(QPen(QColor(0, 0, 0, 70), 1))
        p.drawPath(path)

        # Shine-Sweep: heller Streifen, auf die Buchstaben geclippt
        p.save()
        p.setClipPath(path)
        bw = rect.width() * 0.11
        cx = rect.left() + self._t * rect.width()
        band = QLinearGradient(cx - bw, 0, cx + bw, 0)
        band.setColorAt(0.0, QColor(255, 255, 255, 0))
        band.setColorAt(0.5, QColor(255, 255, 255, 215))
        band.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.fillRect(rect, QBrush(band))
        p.restore()

        # Untertitel
        sub = QFont(theme.SANS_FAMILY)
        sub.setPixelSize(max(12, int(self.height() * 0.032)))
        sub.setLetterSpacing(QFont.AbsoluteSpacing, 7)
        sub.setCapitalization(QFont.AllUppercase)
        p.setFont(sub)
        p.setPen(theme.TEXT_DIM)
        p.drawText(QRectF(0, rect.bottom() + 16, self.width(), 36),
                   Qt.AlignHCenter | Qt.AlignTop, SUBTITLE)
        p.end()

    def _begin_fade(self):
        if self._fading:
            return
        self._fading = True
        self._timer.stop()
        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)
        self._anim = QPropertyAnimation(effect, b"opacity", self)
        self._anim.setDuration(self.FADE_MS)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self._done)
        self._anim.start()

    def _done(self):
        self.hide()
        self.finished.emit()
        self.deleteLater()
