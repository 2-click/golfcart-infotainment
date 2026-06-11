"""CartView -- deckungsgleicher PNG-Layer-Stack mit synchroner Blink-Logik.

Alle PNGs haben dieselbe Canvas-Groesse und werden position-exakt uebereinander
gezeichnet. Die Sichtbarkeit folgt dem VehicleState (Closed-Loop: IST-Status
der SPS). Blinkende Layer (beacon, blinker_*) schaltet EIN zentraler QTimer
synchron um.

Die Layer werden in einem einzigen paintEvent uebereinandergelegt (statt als
gestapelte QLabel). Das komponiert die Transparenz zuverlaessig -- gestapelte
ueberlappende QLabel rendern beim Verschachteln/Grab nicht verlaesslich.
Echte Assets ersetzen die Platzhalter 1:1 (gleiche Dateinamen/Groesse).
"""

import math
import os

from PySide6.QtCore import Qt, QRect, QRectF, QPointF, QTimer, Signal
from PySide6.QtGui import (QPixmap, QImage, QPainter, QColor, QBrush, QPen, QFont,
                           QRadialGradient, QLinearGradient, QConicalGradient)
from PySide6.QtWidgets import QWidget

import config
from core import netinfo
from . import theme

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# PNG-Layer (Stapel-Reihenfolge, unten -> oben). Nur Assets, die es real gibt.
# horn hat bewusst keinen Layer. Alle Lichter ausser beacon haben (noch) kein
# Asset -> als gemalter Glow (siehe GLOW_LIGHTS).
LAYER_ORDER = [
    "cart_base",
    "beacon",
]

# Lichtpositionen in PNG-Koordinaten der cart_base-Canvas (1213x925), vom
# Nutzer eingemessen.
# Front-Lichtcluster: je Cluster sitzen Scheinwerfer UND Blinker am selben Punkt.
HEADLIGHT_RIGHT = (863, 635)
HEADLIGHT_LEFT = (1074, 596)
# Arbeitsscheinwerfer: ein Spot mittig auf der Dachvorderkante.
WORKLIGHT_CENTER = (854, 128)

# Enden des Warnbalkens -> zusaetzlicher weicher Glow beim Blitzen (das
# beacon.png-Asset bleibt; der Glow legt nur einen Schein darueber).
BEACON_GLOW_PTS = [(732, 40), (914, 59)]

# Gemalte Glow-Lichter: (actuator, [Positionen], Farbe, Radius_px, soft).
# Radius in PNG-Pixeln -> wird ins Ziel-Rechteck mitskaliert. soft=True ->
# weicher Schein ohne hellen Kern (fuer den Warnbalken, der schon leuchtet).
# Reihenfolge = Zeichenreihenfolge (spaetere liegen oben).
GLOW_LIGHTS = [
    ("day_lights",    [HEADLIGHT_RIGHT, HEADLIGHT_LEFT], QColor("#f4f8ff"), 48, False),
    ("low_beam",      [HEADLIGHT_RIGHT, HEADLIGHT_LEFT], QColor("#f4f8ff"), 100, False),
    ("high_beam",     [HEADLIGHT_RIGHT, HEADLIGHT_LEFT], QColor("#3d7bff"), 132, False),
    ("work_light",    [WORKLIGHT_CENTER],                 QColor("#ffd08a"), 90, False),
    ("blinker_right", [HEADLIGHT_RIGHT],                 QColor("#ff9b1a"), 80, False),
    ("blinker_left",  [HEADLIGHT_LEFT],                  QColor("#ff9b1a"), 80, False),
    ("beacon",        BEACON_GLOW_PTS,                   QColor("#ff8a1e"), 85, True),
]


class CartView(QWidget):
    # 5 Klicks auf den Cart -> versteckten PIN-Dialog anfordern.
    pinRequested = Signal()
    adminChanged = Signal(bool)
    PIN_CLICKS = 5
    CLICK_RESET_MS = 1500  # Klicks muessen in diesem Fenster aufeinanderfolgen
    RAINBOW_HOLD_MS = 10000  # Bestaetigungs-Rand bleibt 10 s, dann Fade
    FADE_STEP = 0.04         # pro Tick (~33 ms) -> ~0,8 s Ausblenden

    def __init__(self, state, blink, parent=None):
        super().__init__(parent)
        self.state = state
        self.blink = blink
        self.setFixedSize(config.CART_AREA, config.CART_AREA)

        # IPv4-Anzeige im Admin-Modus (Ethernet/WLAN). Wird per Timer aktuell
        # gehalten und nur gemalt, wenn der Admin-Modus aktiv ist.
        self._ips: dict[str, str] = {}
        self._ip_timer = QTimer(self)
        self._ip_timer.timeout.connect(self._refresh_ips)

        # Versteckter 5-Klick-Trigger.
        self._click_count = 0
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._reset_clicks)

        # Admin-Modus: animierter Regenbogen-Rand entlang der Cart-Kontur.
        # Der Rand ist nur eine kurze Bestaetigung -> blendet nach RAINBOW_HOLD
        # aus, der Admin-Modus selbst bleibt aber aktiv.
        self._admin = False
        self._rainbow_on = False
        self._rainbow_phase = 0.0
        self._rainbow_opacity = 1.0
        self._fading = False
        self._cart_scaled = None  # Cache der skalierten Base fuer die Kontur
        self._rainbow_timer = QTimer(self)
        self._rainbow_timer.timeout.connect(self._rainbow_tick)
        self._fade_after = QTimer(self)
        self._fade_after.setSingleShot(True)
        self._fade_after.timeout.connect(self._start_fade)

        # Pixmaps in nativer (deckungsgleicher) Groesse laden. Skaliert wird
        # erst im paintEvent in EIN gemeinsames Zielrechteck -> alle Layer
        # bleiben pixelgenau uebereinander, unabhaengig vom Seitenverhaeltnis.
        self._pixmaps: dict[str, QPixmap] = {}
        for name in LAYER_ORDER:
            self._pixmaps[name] = QPixmap(os.path.join(ASSET_DIR, f"{name}.png"))

        # Blinken (ruhiger Blinker + Doppelblitz der Rundumleuchte) kommt
        # zentral vom BlinkController -> synchron mit der Telltale-Leiste.
        self.blink.tick.connect(self.update)
        self.state.changed.connect(self.update)

        # Temporaerer Kalibrier-Modus (CART_CALIBRATE=1): Klicks sammeln und
        # als PNG-Koordinaten anzeigen, um Lichtpositionen zu finden.
        self._calibrate = config.CART_CALIBRATE
        self._marks: list[tuple[int, int]] = []

    # ------------------------------------------------------------------
    # Versteckter 5-Klick-Trigger + Admin-Modus
    # ------------------------------------------------------------------
    def _reset_clicks(self):
        self._click_count = 0

    def set_admin(self, on: bool):
        if on == self._admin:
            return
        self._admin = on
        self.adminChanged.emit(on)
        if on:
            self._show_rainbow()
            self._refresh_ips()       # sofort fuellen, dann periodisch
            self._ip_timer.start(5000)
        else:
            self._hide_rainbow()
            self._ip_timer.stop()
            self._ips = {}
        self.update()

    def _refresh_ips(self):
        ips = netinfo.ipv4_addresses()
        if ips != self._ips:
            self._ips = ips
            self.update()

    def is_admin(self) -> bool:
        return self._admin

    def _show_rainbow(self):
        self._rainbow_on = True
        self._fading = False
        self._rainbow_opacity = 1.0
        self._rainbow_timer.start(33)        # ~30 fps Animation
        self._fade_after.start(self.RAINBOW_HOLD_MS)

    def _hide_rainbow(self):
        self._rainbow_on = False
        self._fading = False
        self._rainbow_timer.stop()
        self._fade_after.stop()

    def _start_fade(self):
        self._fading = True

    def _rainbow_tick(self):
        self._rainbow_phase = (self._rainbow_phase + 0.015) % 1.0
        if self._fading:
            self._rainbow_opacity -= self.FADE_STEP
            if self._rainbow_opacity <= 0.0:
                self._rainbow_opacity = 0.0
                self._rainbow_on = False
                self._fading = False
                self._rainbow_timer.stop()
        self.update()

    def _layer_visible(self, name: str) -> bool:
        if name == "cart_base":
            return True
        # Sichtbar, wenn aktiv UND (sofern blinkend) in der EIN-Blinkphase.
        return self.state.get_actuator(name) and self.blink.is_on(name)

    def _target_rect(self) -> QRect:
        """Zielrechteck: Base seitenverhaeltnis-treu in das Widget einpassen
        und zentrieren. Alle Layer teilen sich dieses Rechteck."""
        base = self._pixmaps.get("cart_base")
        ww, wh = self.width(), self.height()
        if base is None or base.isNull() or base.width() == 0:
            return QRect(0, 0, ww, wh)
        scale = min(ww / base.width(), wh / base.height())
        tw, th = round(base.width() * scale), round(base.height() * scale)
        return QRect((ww - tw) // 2, (wh - th) // 2, tw, th)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)
        target = self._target_rect()

        # --- Hintergrund hinter dem Cart (flache Fuellung -- bewusst kein
        #     Verlauf, das bandet auf dem Produktionsdisplay) ---
        painter.fillRect(self.rect(), theme.BG_PANEL)

        base = self._pixmaps.get("cart_base")

        # --- Bodenreflexion (gespiegelte Base, ausgeblendet) ---
        if base is not None and not base.isNull():
            refl_h = int(target.height() * 0.34)
            painter.save()
            painter.setOpacity(0.18)
            # Spiegeln an der Unterkante des Carts.
            painter.translate(0, 2 * target.bottom())
            painter.scale(1, -1)
            painter.drawPixmap(target, base)
            painter.restore()
            # Reflexion nach unten weich ausblenden -- Endfarbe = Hintergrund,
            # damit die Reflexion sauber im flachen BG_PANEL verschwindet.
            fade = QLinearGradient(0, target.bottom(), 0, target.bottom() + refl_h)
            c0 = QColor(theme.BG_PANEL); c0.setAlpha(0)
            fade.setColorAt(0.0, c0)
            fade.setColorAt(1.0, theme.BG_PANEL)
            painter.setBrush(QBrush(fade))
            painter.setPen(Qt.NoPen)
            painter.drawRect(QRectF(0, target.bottom(), self.width(), refl_h + 2))

        # --- Layer-Stack (Base + sichtbare Lichter) ---
        for name in LAYER_ORDER:
            pix = self._pixmaps.get(name)
            if pix is None or pix.isNull():
                continue
            if self._layer_visible(name):
                painter.drawPixmap(target, pix)

        # --- Gemalte Glow-Lichter (Scheinwerfer + Blinker, kein Asset) ---
        if base is not None and not base.isNull():
            scale = target.width() / base.width()
            for name, positions, color, radius, soft in GLOW_LIGHTS:
                if not (self.state.get_actuator(name) and self.blink.is_on(name)):
                    continue
                for px, py in positions:
                    cx = target.left() + px * scale
                    cy = target.top() + py * scale
                    self._draw_glow(painter, cx, cy, radius * scale, color, soft)

        # --- Admin: IPv4-Adressen unter dem Cart anzeigen (nur wenn vorhanden) ---
        if self._admin and self._ips:
            self._draw_ip_overlay(painter, target)

        # --- Kalibrier-Overlay (temporaer) ---
        if self._calibrate:
            self._draw_calibration(painter, target, base)

        # --- Admin-Bestaetigung: animierter Regenbogen entlang der Kontur ---
        if self._rainbow_on:
            self._draw_rainbow_outline(painter, target)
        painter.end()

    def _draw_ip_overlay(self, painter, target):
        """Zeigt die aktuellen IPv4-Adressen (Ethernet/WLAN) zentriert unter
        dem Cart. Label links, Adresse rechts; fehlt eine Adresse -> '--'."""
        rows = [("ETH", self._ips.get("eth")), ("WIFI", self._ips.get("wifi"))]
        painter.save()
        painter.setFont(theme.mono(13))
        fm = painter.fontMetrics()
        line_h = fm.height() + 4
        # Box-Breite an laengster Zeile (Label + Abstand + Adresse) ausrichten.
        widest = max(fm.horizontalAdvance(f"{lab}    {ip or '--'}")
                     for lab, ip in rows)
        pad = 12
        box_w = widest + 2 * pad
        box_h = line_h * len(rows) + 2 * pad
        cx = self.width() / 2
        # Unter dem Cart platzieren, aber sicher im Widget halten.
        top = min(target.bottom() + 16, self.height() - box_h - 8)
        box = QRectF(cx - box_w / 2, top, box_w, box_h)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.drawRoundedRect(box, 8, 8)

        inner_w = box_w - 2 * pad
        y = top + pad
        for lab, ip in rows:
            cell = QRectF(box.left() + pad, y, inner_w, line_h)
            painter.setPen(theme.TEXT_DIM)
            painter.drawText(cell, Qt.AlignLeft | Qt.AlignVCenter, lab)
            painter.setPen(theme.ICE if ip else theme.TEXT_FAINT)
            painter.drawText(cell, Qt.AlignRight | Qt.AlignVCenter, ip or "--")
            y += line_h
        painter.restore()

    def _ensure_cart_scaled(self, tw, th):
        c = self._cart_scaled
        if c is None or c.width() != tw or c.height() != th:
            base = self._pixmaps.get("cart_base")
            self._cart_scaled = base.scaled(tw, th, Qt.IgnoreAspectRatio,
                                            Qt.SmoothTransformation)
        return self._cart_scaled

    def _draw_rainbow_outline(self, painter, target):
        """Regenbogen-Kontur entlang ALLER Alpha-Kanten des Base-PNG.

        Trick: Silhouette an mehreren Offsets zeichnen (Dilatation) und die
        Original-Silhouette abziehen -> uebrig bleibt ein Randring exakt entlang
        der Kontur. Dieser wird mit dem rotierenden Regenbogen eingefaerbt.
        """
        base = self._pixmaps.get("cart_base")
        if base is None or base.isNull():
            return
        tw, th = target.width(), target.height()
        if tw <= 0 or th <= 0:
            return
        cart = self._ensure_cart_scaled(tw, th)

        w = 2.5  # Randbreite in px (halbiert)
        ring = QImage(tw, th, QImage.Format_ARGB32_Premultiplied)
        ring.fill(Qt.transparent)
        rp = QPainter(ring)
        rp.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # Dilatation: Silhouette ringfoermig versetzt aufsummieren.
        steps = 16
        for k in range(steps):
            a = 2 * math.pi * k / steps
            rp.drawPixmap(QPointF(math.cos(a) * w, math.sin(a) * w), cart)
        # Original-Silhouette abziehen -> nur der Randring bleibt.
        rp.setCompositionMode(QPainter.CompositionMode_DestinationOut)
        rp.drawPixmap(QPointF(0, 0), cart)
        # Ring mit Regenbogen einfaerben (Form bleibt erhalten).
        rp.setCompositionMode(QPainter.CompositionMode_SourceIn)
        grad = QConicalGradient(tw / 2, th / 2, 0)
        n = 12
        for i in range(n + 1):
            hue = (i / n + self._rainbow_phase) % 1.0
            grad.setColorAt(i / n, QColor.fromHsvF(hue, 0.85, 1.0))
        rp.fillRect(0, 0, tw, th, QBrush(grad))
        rp.end()

        painter.setOpacity(self._rainbow_opacity)
        painter.drawImage(target.topLeft(), ring)
        painter.setOpacity(1.0)

    # ------------------------------------------------------------------
    # Kalibrier-Modus: Klick -> PNG-Koordinaten
    # ------------------------------------------------------------------
    def _widget_to_png(self, wx, wy):
        base = self._pixmaps.get("cart_base")
        target = self._target_rect()
        if base is None or base.isNull() or target.width() == 0:
            return None
        scale = target.width() / base.width()
        px = round((wx - target.left()) / scale)
        py = round((wy - target.top()) / scale)
        return px, py

    def mousePressEvent(self, event):
        if not self._calibrate:
            # Versteckter Trigger: 5 Klicks in Folge -> PIN-Dialog anfordern.
            self._click_count += 1
            self._click_timer.start(self.CLICK_RESET_MS)
            if self._click_count >= self.PIN_CLICKS:
                self._click_count = 0
                self._click_timer.stop()
                if self._admin:
                    self.set_admin(False)   # im Admin-Modus: 5 Klicks = verlassen
                else:
                    self.pinRequested.emit()
            return super().mousePressEvent(event)
        pos = event.position()
        mapped = self._widget_to_png(pos.x(), pos.y())
        if mapped is not None:
            self._marks.append(mapped)
            print(f"[cart-calibrate] PNG x={mapped[0]} y={mapped[1]}", flush=True)
            self.update()

    def _draw_calibration(self, painter, target, base):
        if base is None or base.isNull():
            return
        scale = target.width() / base.width()
        painter.setFont(QFont(theme.MONO_FAMILY, 11, QFont.Bold))
        for px, py in self._marks:
            cx = target.left() + px * scale
            cy = target.top() + py * scale
            # Fadenkreuz
            painter.setPen(QPen(QColor("#00e5ff"), 1.5))
            painter.drawLine(QPointF(cx - 12, cy), QPointF(cx + 12, cy))
            painter.drawLine(QPointF(cx, cy - 12), QPointF(cx, cy + 12))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), 7, 7)
            # Koordinaten-Label mit dunklem Hintergrund
            txt = f"{px},{py}"
            tw = painter.fontMetrics().horizontalAdvance(txt) + 8
            box = QRectF(cx + 12, cy - 22, tw, 18)
            painter.setBrush(QBrush(QColor(0, 0, 0, 180)))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(box, 4, 4)
            painter.setPen(QColor("#00e5ff"))
            painter.drawText(box, Qt.AlignCenter, txt)
        # Hinweis oben
        painter.setPen(QColor("#00e5ff"))
        painter.setFont(QFont(theme.SANS_FAMILY, 10))
        painter.drawText(QRectF(6, 4, self.width() - 12, 20),
                         Qt.AlignLeft | Qt.AlignVCenter,
                         "KALIBRIERUNG: auf Scheinwerfer tippen")

    @staticmethod
    def _draw_glow(painter, cx, cy, r, color, soft=False):
        """Radialer Lichtschein. soft=True -> weicher Halo ohne hellen Kern
        (fuer Lichter, die bereits ein leuchtendes Asset haben)."""
        grad = QRadialGradient(cx, cy, r)
        if soft:
            c0 = QColor(color); c0.setAlpha(150)
            c1 = QColor(color); c1.setAlpha(80)
            edge = QColor(color); edge.setAlpha(0)
            grad.setColorAt(0.0, c0)
            grad.setColorAt(0.45, c1)
            grad.setColorAt(1.0, edge)
        else:
            core = QColor(color); core.setAlpha(235)
            mid = QColor(color); mid.setAlpha(150)
            edge = QColor(color); edge.setAlpha(0)
            grad.setColorAt(0.0, QColor(255, 255, 255, 230))  # heisser Kern
            grad.setColorAt(0.18, core)
            grad.setColorAt(0.5, mid)
            grad.setColorAt(1.0, edge)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(grad))
        painter.drawEllipse(QPointF(cx, cy), r, r)
