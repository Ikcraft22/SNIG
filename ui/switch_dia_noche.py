"""
Widget interactivo de modo Claro / Oscuro con diseño de Sol, Luna Creciente, Nubes y Estrellas.
Fiel al diseño original y animación de 'Dark-Light-Mode-Switch' (preview.gif).
"""

import sys
from pathlib import Path
from PyQt5.QtCore import (
    Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtProperty, pyqtSignal, QPointF
)
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient, QPainterPath, QPen, QCursor
)
from PyQt5.QtSvg import QSvgRenderer


class SwitchDiaNoche(QWidget):
    """
    Interruptor animado Día / Noche (Modo Claro / Oscuro) idéntico a preview.gif.
    - Modo Claro: Sol brillante (#FFC187) con resplandor cálido y nubes flotantes.
    - Modo Oscuro: Luna creciente (#DEE5F3 con recorte oscuro #565C6B) y cielo estrellado.
    """
    toggled = pyqtSignal(bool)
    animationFinished = pyqtSignal(bool)

    def __init__(self, parent=None, checked=False, width=120, height=52):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._checked = bool(checked)
        self._progress = 1.0 if self._checked else 0.0
        self._hover = False
        
        # Dimensiones estándar proporcionales a 150x65
        self._custom_w = width
        self._custom_h = height
        self.setFixedSize(self._custom_w, self._custom_h)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAccessibleName("Cambiar tema de color")
        self.setAccessibleDescription(
            "Alterna entre modo claro y modo oscuro. Usa Espacio o Intro para cambiar."
        )
        self.actualizar_tooltip()

        # Animación suave de transición
        self._anim = QPropertyAnimation(self, b"progreso", self)
        self._anim.setDuration(500)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._anim.finished.connect(self._notificar_animacion_finalizada)

        # Cargar recursos SVG
        self._assets_dir = Path(__file__).resolve().parent / "assets"
        self._svg_cloud1 = self._cargar_svg("cloud_1.svg")
        self._svg_cloud2 = self._cargar_svg("cloud_2.svg")
        self._svg_cloud3 = self._cargar_svg("cloud_3.svg")
        self._svg_cloud4 = self._cargar_svg("cloud_4.svg")
        self._svg_stars = self._cargar_svg("stars.svg")

    def _cargar_svg(self, nombre: str):
        ruta = self._assets_dir / nombre
        if ruta.exists():
            return QSvgRenderer(str(ruta))
        return None

    def actualizar_tooltip(self):
        if self._checked:
            self.setToolTip("Modo Oscuro activado (Clic para cambiar a Modo Claro)")
            self.setAccessibleDescription(
                "Modo oscuro activado. Pulsa Espacio o Intro para cambiar a modo claro."
            )
        else:
            self.setToolTip("Modo Claro activado (Clic para cambiar a Modo Oscuro)")
            self.setAccessibleDescription(
                "Modo claro activado. Pulsa Espacio o Intro para cambiar a modo oscuro."
            )

    # ---- Propiedad animable de progreso (0.0 = Día, 1.0 = Noche) ----
    @pyqtProperty(float)
    def progreso(self) -> float:
        return self._progress

    @progreso.setter
    def progreso(self, val: float):
        self._progress = max(0.0, min(1.0, float(val)))
        self.update()

    # ---- Estado y Métodos Públicos ----
    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool, animar: bool = True):
        checked = bool(checked)
        if self._checked == checked and not (self._anim.state() == QPropertyAnimation.Running):
            return

        self._checked = checked
        self.actualizar_tooltip()
        target = 1.0 if checked else 0.0

        if animar and self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._progress)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._anim.stop()
            self._progress = target
            self.update()

    def toggle(self):
        self.setChecked(not self._checked, animar=True)
        self.toggled.emit(self._checked)

    def _notificar_animacion_finalizada(self):
        """Informa cuándo termina la transición visual del interruptor."""
        target = 1.0 if self._checked else 0.0
        if abs(self._progress - target) < 0.001:
            self.animationFinished.emit(self._checked)

    # ---- Eventos de interacción ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle()
        super().mousePressEvent(event)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.toggle()
        else:
            super().keyPressEvent(event)

    # ---- Renderizado con fidelidad total a preview.gif ----
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        w = float(self.width())
        h = float(self.height())
        scale = h / 65.0
        p = self._progress  # 0.0 (Día) -> 1.0 (Noche)
        radius = h / 2.0
        border_w = 2.0 * scale

        # Path del interior (clipping para nubes, estrellas y fondos)
        pill_rect = QRectF(1.0 * scale, 1.0 * scale, w - 2.0 * scale, h - 2.0 * scale)
        pill_path = QPainterPath()
        pill_path.addRoundedRect(pill_rect, radius - 1.0 * scale, radius - 1.0 * scale)

        # -------------------------------------------------------------
        # 1. Borde Exterior con Gradiente
        # Día:   linear-gradient(to bottom, #a2d1fd, #cde7ff)
        # Noche: linear-gradient(to bottom, #000000, #6c7384)
        # -------------------------------------------------------------
        border_rect = QRectF(border_w / 2.0, border_w / 2.0, w - border_w, h - border_w)
        border_path = QPainterPath()
        border_path.addRoundedRect(border_rect, radius - border_w / 2.0, radius - border_w / 2.0)

        painter.save()
        if p < 1.0:
            border_dia = QLinearGradient(0, 0, 0, h)
            border_dia.setColorAt(0.0, QColor("#a2d1fd"))
            border_dia.setColorAt(1.0, QColor("#cde7ff"))
            painter.setOpacity(1.0 - p)
            painter.setPen(QPen(border_dia, border_w))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(border_path)

        if p > 0.0:
            border_noche = QLinearGradient(0, 0, 0, h)
            border_noche.setColorAt(0.0, QColor("#273449"))
            border_noche.setColorAt(1.0, QColor("#46546b"))
            painter.setOpacity(p)
            painter.setPen(QPen(border_noche, border_w))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(border_path)
        painter.restore()

        # -------------------------------------------------------------
        # 2. Fondo Interior con Gradiente (Día: #73bbff->#a2d1fd / Noche: #2b3347->#181d27)
        # -------------------------------------------------------------
        painter.save()
        painter.setClipPath(pill_path)

        # Fondo diurno
        if p < 1.0:
            grad_dia = QLinearGradient(0, 0, 0, h)
            grad_dia.setColorAt(0.0, QColor("#73bbff"))
            grad_dia.setColorAt(1.0, QColor("#a2d1fd"))
            painter.setOpacity(1.0 - p)
            painter.fillPath(pill_path, grad_dia)

        # Fondo nocturno
        if p > 0.0:
            grad_noche = QLinearGradient(0, h, 0, 0)
            grad_noche.setColorAt(0.0, QColor("#2b3347"))
            grad_noche.setColorAt(1.0, QColor("#181d27"))
            painter.setOpacity(p)
            painter.fillPath(pill_path, grad_noche)

        # -------------------------------------------------------------
        # 3. Estrellas (Modo Noche) - suben desde abajo hacia el centro
        # -------------------------------------------------------------
        if self._svg_stars and p > 0.01:
            painter.setOpacity(p)
            stars_w = 80.0 * scale
            stars_h = 52.0 * scale
            stars_x = 4.0 * scale
            y_centro = (h - stars_h) / 2.0
            y_offset = (1.0 - p) * (h * 0.9)
            stars_rect = QRectF(stars_x, y_centro + y_offset, stars_w, stars_h)
            self._svg_stars.render(painter, stars_rect)

        # -------------------------------------------------------------
        # 4. Nubes (Modo Día) - idénticas a style.css
        # -------------------------------------------------------------
        if p < 0.99:
            op_clouds = 1.0 - p
            cloud_w = 88.0 * scale
            cloud_h = 50.0 * scale

            # Cloud 1 (opacidad 0.95, day: left 0, bottom -55% -> night: left -110px, bottom -35%)
            if self._svg_cloud1:
                painter.setOpacity(op_clouds * 0.95)
                c1_x = (0.0 * (1.0 - p) + (-110.0 * scale) * p)
                c1_bottom = (-0.55 * h * (1.0 - p) + (-0.35 * h) * p)
                c1_y = h - cloud_h - c1_bottom
                self._svg_cloud1.render(painter, QRectF(c1_x, c1_y, cloud_w, cloud_h))

            # Cloud 2 (opacidad 0.60, day: left 25px, bottom -45% -> night: left -110px, bottom -15%)
            if self._svg_cloud2:
                painter.setOpacity(op_clouds * 0.60)
                c2_x = ((25.0 * scale) * (1.0 - p) + (-110.0 * scale) * p)
                c2_bottom = (-0.45 * h * (1.0 - p) + (-0.15 * h) * p)
                c2_y = h - cloud_h - c2_bottom
                self._svg_cloud2.render(painter, QRectF(c2_x, c2_y, cloud_w, cloud_h))

            # Cloud 3 (opacidad 0.95, day: right 0px, bottom -40% -> night: right -110px, bottom -15%)
            if self._svg_cloud3:
                painter.setOpacity(op_clouds * 0.95)
                c3_x = (w - cloud_w) + (110.0 * scale * p)
                c3_bottom = (-0.40 * h * (1.0 - p) + (-0.15 * h) * p)
                c3_y = h - cloud_h - c3_bottom
                self._svg_cloud3.render(painter, QRectF(c3_x, c3_y, cloud_w, cloud_h))

            # Cloud 4 (opacidad 0.60, day: right -25px, bottom -16% -> night: right -110px, bottom -5%)
            if self._svg_cloud4:
                painter.setOpacity(op_clouds * 0.60)
                c4_x = (w - cloud_w + 25.0 * scale) + (110.0 * scale * p)
                c4_bottom = (-0.16 * h * (1.0 - p) + (-0.05 * h) * p)
                c4_y = h - cloud_h - c4_bottom
                self._svg_cloud4.render(painter, QRectF(c4_x, c4_y, cloud_w, cloud_h))

        painter.restore()

        # -------------------------------------------------------------
        # 5. Pomo Principal: Sol Dorado a Luna Creciente Plateada
        # Proporciones exactas de CSS:
        # --sunmoon-size: 55px; --switch-padding-x: 5px;
        # -------------------------------------------------------------
        padding_x = 5.0 * scale
        orb_size = 55.0 * scale
        orb_y = (h - orb_size) / 2.0
        min_x = padding_x
        max_x = w - orb_size - padding_x
        curr_x = min_x + (max_x - min_x) * p
        orb_center = QPointF(curr_x + orb_size / 2.0, orb_y + orb_size / 2.0)
        orb_rect = QRectF(curr_x, orb_y, orb_size, orb_size)

        painter.save()

        # A) Resplandor exterior (box-shadow)
        if p < 0.9:
            # Sol: box-shadow: 0px 0px 11.7px 0px #FFC187, 0px 0px 20px 0px #ffc18768
            sun_glow_rad = orb_size * 0.90
            sun_glow = QRadialGradient(orb_center, sun_glow_rad)
            sun_glow.setColorAt(0.0, QColor(255, 193, 135, int(180 * (1.0 - p))))
            sun_glow.setColorAt(0.65, QColor(255, 193, 135, int(70 * (1.0 - p))))
            sun_glow.setColorAt(1.0, QColor(255, 193, 135, 0))
            painter.setBrush(sun_glow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(orb_center, sun_glow_rad, sun_glow_rad)

        if p > 0.1:
            # Luna: box-shadow: 0px 0px 51.7px 0px #dee5f3
            moon_glow_rad = orb_size * 1.15
            moon_glow = QRadialGradient(orb_center, moon_glow_rad)
            moon_glow.setColorAt(0.0, QColor(222, 229, 243, int(150 * p)))
            moon_glow.setColorAt(0.60, QColor(222, 229, 243, int(55 * p)))
            moon_glow.setColorAt(1.0, QColor(222, 229, 243, 0))
            painter.setBrush(moon_glow)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(orb_center, moon_glow_rad, moon_glow_rad)

        # B) Cuerpo base del Sol/Luna (#FFC187 en día, #dee5f3 en noche)
        r_base = int(255 * (1.0 - p) + 222 * p)
        g_base = int(193 * (1.0 - p) + 229 * p)
        b_base = int(135 * (1.0 - p) + 243 * p)
        base_color = QColor(r_base, g_base, b_base)

        painter.setBrush(base_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(orb_rect)

        # C) Efecto Darkside (.darkside en CSS):
        # top: 2px, left: 2px, width: 75%, height: 75%
        # background-color: #FFC187 en día, #565c6b en noche
        darkside_size = orb_size * 0.75
        darkside_offset = 2.0 * scale
        darkside_rect = QRectF(
            curr_x + darkside_offset,
            orb_y + darkside_offset,
            darkside_size,
            darkside_size
        )

        if p > 0.005:
            # Interpolar de #FFC187 (255, 193, 135) a #565c6b (86, 92, 107)
            r_ds = int(255 * (1.0 - p) + 86 * p)
            g_ds = int(193 * (1.0 - p) + 92 * p)
            b_ds = int(135 * (1.0 - p) + 107 * p)
            darkside_color = QColor(r_ds, g_ds, b_ds)

            painter.setBrush(darkside_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(darkside_rect)

        painter.restore()

        # Resaltado al hacer hover
        if self._hover:
            painter.save()
            hover_pen = QPen(QColor(203, 213, 225, 45), 1.5)
            painter.setPen(hover_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(border_path)
            painter.restore()
        if self.hasFocus():
            painter.save()
            painter.setPen(QPen(QColor("#f59e0b"), 3.0))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(
                QRectF(3, 3, w - 6, h - 6),
                radius - 3,
                radius - 3,
            )
            painter.restore()
