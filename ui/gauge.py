"""SpeedGauge -- analoges Rund-Tacho, modern gerendert.

Retro-Instrument (270deg-Skala, Ziffernkranz, Zeiger) mit modernem Look:
abgesetzte Tiefen ueber Radialgradient, gluehender Bernstein-Fortschrittsbogen,
grosse digitale Mono-Ziffer in der Mitte.
"""

import math

from PySide6.QtCore import Qt, QRectF, QPointF, QTimer, Signal
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush,
                           QConicalGradient, QFont)
from PySide6.QtWidgets import QWidget

import config
from . import theme

START_ANGLE = 225.0   # Skalenstart (Qt-Grad, 0=3 Uhr, ggü. Uhrzeigersinn +)
SWEEP = 270.0         # Skalenumfang


class SpeedGauge(QWidget):
    # Doppeltipp -> Handgas/Tempomat-Screen oeffnen.
    doubleTapped = Signal()

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self.state = state
        self.setMinimumSize(300, 300)
        # Skalenendwert wird fluessig animiert (10 <-> 30 je nach Admin-Modus).
        self._display_max = self._target_max()
        self._anim = QTimer(self)
        self._anim.timeout.connect(self._animate_max)
        self.state.changed.connect(self._on_state)

    def _target_max(self) -> float:
        return (config.SPEEDO_MAX_ADMIN if self.state.admin_mode
                else config.SPEEDO_MAX_DEFAULT)

    def _on_state(self):
        # Bei Aenderung des Ziel-Endwerts die Animation anstossen.
        if abs(self._display_max - self._target_max()) > 0.01 and not self._anim.isActive():
            self._anim.start(16)  # ~60 fps
        self.update()

    def _animate_max(self):
        target = self._target_max()
        self._display_max += (target - self._display_max) * 0.12
        if abs(self._display_max - target) < 0.05:
            self._display_max = target
            self._anim.stop()
        self.update()

    def mouseDoubleClickEvent(self, event):
        self.doubleTapped.emit()

    def _angle_for(self, value: float) -> float:
        frac = max(0.0, min(1.0, value / self._display_max))
        # Im Uhrzeigersinn von START_ANGLE -> daher minus.
        return START_ANGLE - frac * SWEEP

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        side = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        R = side / 2 - 6
        face = QRectF(cx - R, cy - R, 2 * R, 2 * R)

        # --- Face: flache Fuellung (kein Verlauf -- bandet auf dem Display).
        #     Tiefe entsteht stattdessen durch flache Ton-Abstufung zwischen
        #     Face (dunkler) und Hub (heller) plus die Ringkonturen. ---
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(theme.BG_PANEL))
        p.drawEllipse(face)

        # Aeusserer Ring
        p.setPen(QPen(theme.STROKE, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(face)

        # --- Track (unausgefuellte Skala) ---
        track_w = R * 0.085
        track_r = R - track_w * 0.8
        track_rect = QRectF(cx - track_r, cy - track_r, 2 * track_r, 2 * track_r)
        pen = QPen(theme.STROKE_SOFT, track_w)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(track_rect, int(START_ANGLE * 16), int(-SWEEP * 16))

        # --- Tick-Marks + Beschriftung ---
        major = 5  # alle 5 km/h ein grosser Strich + Zahl
        steps = max(1, round(self._display_max))
        for v in range(0, steps + 1):
            ang = self._angle_for(v)
            a = ang * 3.14159265 / 180.0
            is_major = (v % major == 0)
            r1 = track_r - track_w * 0.6
            r2 = r1 - (R * 0.06 if is_major else R * 0.03)
            ca, sa = math.cos(a), math.sin(a)
            p.setPen(QPen(theme.TEXT_DIM if is_major else theme.TEXT_FAINT,
                          2.0 if is_major else 1.0))
            p.drawLine(QPointF(cx + ca * r1, cy - sa * r1),
                       QPointF(cx + ca * r2, cy - sa * r2))
            if is_major:
                rt = r2 - R * 0.10
                p.setFont(theme.mono(int(R * 0.085), QFont.Medium))
                p.setPen(theme.TEXT_FAINT)
                tr = QRectF(cx + ca * rt - 18, cy - sa * rt - 12, 36, 24)
                p.drawText(tr, Qt.AlignCenter, str(v))

        # --- Gefuellter Fortschrittsbogen (Speed) mit Conical-Glow ---
        speed = max(0.0, min(self._display_max, self.state.speed_kmh))
        frac = speed / self._display_max if self._display_max else 0
        if frac > 0:
            cg = QConicalGradient(cx, cy, START_ANGLE)
            cg.setColorAt(0.0, theme.AMBER_HI)
            cg.setColorAt(min(0.75, SWEEP / 360.0), theme.AMBER)
            cg.setColorAt(1.0, theme.AMBER_DEEP)
            # Glow (breiter, halbtransparent) zuerst
            glow = QColor(theme.AMBER)
            glow.setAlpha(70)
            gp = QPen(glow, track_w * 2.0)
            gp.setCapStyle(Qt.RoundCap)
            p.setPen(gp)
            p.drawArc(track_rect, int(START_ANGLE * 16), int(-SWEEP * frac * 16))
            # Eigentlicher Bogen
            ap = QPen(QBrush(cg), track_w)
            ap.setCapStyle(Qt.RoundCap)
            p.setPen(ap)
            p.drawArc(track_rect, int(START_ANGLE * 16), int(-SWEEP * frac * 16))

        # --- Zeiger (Retro), voll gezeichnet -- die Nabe verdeckt den Ansatz ---
        ang = self._angle_for(speed)
        a = ang * math.pi / 180.0
        needle_r = track_r - track_w
        tip = QPointF(cx + math.cos(a) * needle_r, cy - math.sin(a) * needle_r)
        backa = a + math.pi
        back = QPointF(cx + math.cos(backa) * R * 0.12,
                       cy - math.sin(backa) * R * 0.12)
        npen = QPen(theme.AMBER_HI, max(2.5, R * 0.022))
        npen.setCapStyle(Qt.RoundCap)
        p.setPen(npen)
        p.drawLine(back, tip)

        # --- Innere Hub-Scheibe: reservierte Freizone fuer die Anzeige ---
        # Radius so, dass zwischen Skalenring und Zahl ein klarer Ring frei
        # bleibt; Nadel/Bogen enden ausserhalb dieser Scheibe.
        hub_r = R * 0.50
        # Flache Fuellung, etwas heller als das Face -> dezente Tiefe ohne Verlauf.
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(theme.BG_ELEVATED))
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)
        p.setPen(QPen(theme.STROKE, 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(cx, cy), hub_r, hub_r)

        # --- Zentrale Digital-Anzeige (innerhalb der Hub-Scheibe) ---
        p.setPen(theme.TEXT)
        p.setFont(theme.mono(int(hub_r * 0.78), QFont.Bold))
        num_rect = QRectF(cx - hub_r, cy - hub_r * 0.72,
                          2 * hub_r, hub_r * 1.0)
        p.drawText(num_rect, Qt.AlignCenter, f"{self.state.speed_kmh:.0f}")
        p.setPen(theme.TEXT_DIM)
        p.setFont(theme.label(max(8, int(hub_r * 0.17)), spacing=3.0))
        unit_rect = QRectF(cx - hub_r, cy + hub_r * 0.30,
                           2 * hub_r, hub_r * 0.4)
        p.drawText(unit_rect, Qt.AlignCenter, "km/h")

        # --- Handgas (0..100 %): Mini-Leiste + Wert im unteren Spalt ---
        # Kein Bug-Marker auf der km/h-Skala, da das resultierende Tempo
        # nicht bekannt ist.
        throttle = self.state.throttle_pct
        if throttle > 0:
            p.setPen(theme.AMBER_HI)
            p.setFont(theme.label(max(8, int(R * 0.068)), spacing=2.0))
            p.drawText(QRectF(cx - R, cy + R * 0.52, 2 * R, R * 0.16),
                       Qt.AlignCenter, f"HANDGAS  {throttle:.0f}%")
            # Fortschrittsleiste
            bw, bh = R * 0.66, R * 0.05
            bx, by = cx - bw / 2, cy + R * 0.70
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(theme.STROKE_SOFT))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), bh / 2, bh / 2)
            p.setBrush(QBrush(theme.AMBER))
            p.drawRoundedRect(QRectF(bx, by, bw * throttle / 100.0, bh),
                              bh / 2, bh / 2)
        p.end()
