"""Panel de control del ABB IRB 120 y pasaporte del Hito 1 en vivo.

Usa Qt (python_qt_binding), el mismo toolkit que RViz. La version anterior usaba
Tk, que no esta disponible para el Python 3.12 de ROS 2 Jazzy en esta instalacion.

Pestana 1: seis deslizadores, posturas de prueba y demostracion automatica; a la
derecha, la pose del TF que dibuja RViz frente a la funcion analitica DH, con el
error DeltaE contra el limite 1e-6 m de la Guia PFI.
Pestana 2: bateria DH vs URDF (poses justificadas + aleatorias) y verificacion
secuencial de las poses justificadas contra el TF de RViz.
"""

import csv
import signal
import sys
import time
from collections import deque
from pathlib import Path

import numpy as np
import rclpy
from python_qt_binding.QtCore import Qt, QTimer
from python_qt_binding.QtGui import QColor, QFont
from python_qt_binding.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64, Float64MultiArray
from tf2_ros import Buffer, TransformException, TransformListener

from irb120_hito1.kinematics.dh import (
    GRIPPER_TCP_Z_M,
    JOINT_NAMES,
    TCP_VERIFIED_ON_ROBOT,
    position_error_m,
    rotation_error_rad,
)
from irb120_hito1.motion import interpolate_demo
from irb120_hito1.nodes.fk_validator import transform_to_matrix
from irb120_hito1.slider_controls import JOINT_SLIDERS, PRESETS_DEG, command_payload
from irb120_hito1.validation import (
    DEFAULT_TOLERANCE_M,
    FRAMES,
    VALIDATION_POSES,
    analytic_transform,
    random_poses,
    rpy_deg,
    run_suite,
)
from irb120_hito1.verify_model import default_urdf_path


SLIDER_STEPS_PER_DEG = 10  # resolucion de 0.1 grados
USER_EDIT_HOLD_S = 0.6  # tras mover un control, no se sobrescribe con /joint_states
LIVE_SETTLE_S = 1.0  # espera por pose en la verificacion contra el TF de RViz

COLOR_OK = "#1b7f3b"
COLOR_FAIL = "#b3261e"
COLOR_WAIT = "#8a6d00"


class PanelNode(Node):
    """Lado ROS del panel: publica comandos y observa estados, TF y errores."""

    def __init__(self) -> None:
        super().__init__("irb120_slider_gui")
        self._command_publisher = self.create_publisher(
            Float64MultiArray, "/irb120/joint_commands_deg", 10
        )
        self.joint_state: tuple[Time, list[float]] | None = None
        # robot_state_publisher publica el TF despues del JointState: se guarda un
        # historial corto para comparar con el estado mas reciente que ya tiene TF.
        self._history: deque[tuple[Time, list[float]]] = deque(maxlen=40)
        self.validator_urdf_error_m: float | None = None
        self.validator_tf_error_m: float | None = None
        self.create_subscription(JointState, "/joint_states", self._joint_callback, 20)
        self.create_subscription(
            Float64, "/irb120/fk_position_error_m", self._urdf_error_callback, 10
        )
        self.create_subscription(
            Float64, "/irb120/fk_tf_position_error_m", self._tf_error_callback, 10
        )
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self)

    def publish_command(self, joints_deg: list[float]) -> None:
        message = Float64MultiArray()
        message.data = command_payload(joints_deg)
        self._command_publisher.publish(message)

    def lookup(self, target_frame: str, stamp: Time) -> np.ndarray | None:
        """TF base_link -> target_frame en el instante del JointState."""
        try:
            transform = self._tf_buffer.lookup_transform("base_link", target_frame, stamp)
        except TransformException:
            return None
        return transform_to_matrix(transform)

    def latest_with_tf(self, target_frame: str) -> tuple[list[float], np.ndarray] | None:
        """Estado articular mas reciente cuyo TF ya esta disponible, con ese TF."""
        for stamp, degrees in reversed(self._history):
            measured = self.lookup(target_frame, stamp)
            if measured is not None:
                return degrees, measured
        return None

    def _joint_callback(self, message: JointState) -> None:
        received = dict(zip(message.name, message.position))
        if any(name not in received for name in JOINT_NAMES):
            return
        degrees = [float(np.rad2deg(received[name])) for name in JOINT_NAMES]
        self.joint_state = (Time.from_msg(message.header.stamp), degrees)
        self._history.append(self.joint_state)

    def _urdf_error_callback(self, message: Float64) -> None:
        self.validator_urdf_error_m = float(message.data)

    def _tf_error_callback(self, message: Float64) -> None:
        self.validator_tf_error_m = float(message.data)


def _item(text: str, align_right: bool = False) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
    if align_right:
        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
    return item


def _badge(label: QLabel, text: str, color: str) -> None:
    label.setText(text)
    label.setStyleSheet(
        f"background:{color}; color:white; font-weight:bold; padding:6px 12px;"
        "border-radius:6px;"
    )


class ControlPanel(QMainWindow):
    """Ventana principal: control articular, pasaporte y bateria de pruebas."""

    def __init__(self, node: PanelNode, executor: SingleThreadedExecutor) -> None:
        super().__init__()
        self._node = node
        self._executor = executor
        self._urdf_path = default_urdf_path()
        self._last_user_edit = 0.0
        self._demo_start: float | None = None
        self._live_queue: list = []
        self._live_row = 0
        self._live_deadline = 0.0
        self._suite_results: list = []
        self._sliders: list[QSlider] = []
        self._spins: list[QDoubleSpinBox] = []

        self.setWindowTitle("ABB IRB 120 · Hito 1 · Gemelo digital y cinemática directa")
        self.resize(1200, 780)

        central = QWidget()
        layout = QVBoxLayout(central)
        title = QLabel("ABB IRB 120 · Panel de control y pasaporte del Hito 1")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        tcp_state = "verificado" if TCP_VERIFIED_ON_ROBOT else "NO verificado en el robot"
        subtitle = QLabel(
            f"Requisito (Guía PFI, Hito 1): la pose [x, y, z] de RViz debe coincidir con la "
            f"función analítica DH con ΔE < {DEFAULT_TOLERANCE_M:.0e} m.   "
            f"TCP tool0→gripper_tcp = {GRIPPER_TCP_Z_M * 1000:.0f} mm ({tcp_state}).   "
            "Simulación: no conecta con el controlador físico."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#555;")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._build_control_tab(), "Control y pasaporte")
        tabs.addTab(self._build_tests_tab(), "Batería de pruebas")
        self._tabs = tabs
        layout.addWidget(tabs)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Listo. Mueva un deslizador o elija una postura.")

        self._publish_timer = QTimer(self)
        self._publish_timer.setSingleShot(True)
        self._publish_timer.timeout.connect(self._publish_current)
        ros_timer = QTimer(self)
        ros_timer.timeout.connect(self._spin_ros)
        ros_timer.start(20)
        view_timer = QTimer(self)
        view_timer.timeout.connect(self._refresh_passport)
        view_timer.start(100)
        self._demo_timer = QTimer(self)
        self._demo_timer.timeout.connect(self._demo_step)
        self._live_timer = QTimer(self)
        self._live_timer.timeout.connect(self._live_step)
        QTimer.singleShot(400, self._publish_current)

    # ------------------------------------------------------------------ pestana 1
    def _build_control_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)

        joints_box = QGroupBox("Articulaciones (grados, límites oficiales IRB 120-3/0.6)")
        grid = QGridLayout(joints_box)
        for row, spec in enumerate(JOINT_SLIDERS):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(
                int(spec.lower_deg * SLIDER_STEPS_PER_DEG),
                int(spec.upper_deg * SLIDER_STEPS_PER_DEG),
            )
            slider.setMinimumWidth(260)
            spin = QDoubleSpinBox()
            spin.setRange(spec.lower_deg, spec.upper_deg)
            spin.setDecimals(1)
            spin.setSingleStep(1.0)
            spin.setSuffix(" °")
            spin.setMinimumWidth(95)
            slider.valueChanged.connect(lambda value, index=row: self._slider_moved(index, value))
            spin.valueChanged.connect(lambda value, index=row: self._spin_changed(index, value))
            self._sliders.append(slider)
            self._spins.append(spin)
            grid.addWidget(QLabel(f"<b>{spec.label}</b>"), row, 0)
            grid.addWidget(QLabel(f"{spec.lower_deg:.0f}°"), row, 1)
            grid.addWidget(slider, row, 2)
            grid.addWidget(QLabel(f"{spec.upper_deg:.0f}°"), row, 3)
            grid.addWidget(spin, row, 4)

        presets = QHBoxLayout()
        for name in PRESETS_DEG:
            button = QPushButton(name)
            button.clicked.connect(lambda _checked=False, preset=name: self._apply_preset(preset))
            presets.addWidget(button)
        random_button = QPushButton("Aleatoria")
        random_button.setToolTip("Postura uniforme dentro de los límites articulares.")
        random_button.clicked.connect(self._apply_random)
        presets.addWidget(random_button)
        grid.addLayout(presets, len(JOINT_SLIDERS), 0, 1, 5)

        self._demo_check = QCheckBox("Demostración automática (recorre Cero → A → B → … )")
        self._demo_check.toggled.connect(self._toggle_demo)
        grid.addWidget(self._demo_check, len(JOINT_SLIDERS) + 1, 0, 1, 5)
        grid.setRowStretch(len(JOINT_SLIDERS) + 2, 1)
        layout.addWidget(joints_box, 5)

        passport_box = QGroupBox("Pasaporte en vivo: RViz (TF) frente a la función analítica DH")
        passport = QVBoxLayout(passport_box)
        frame_row = QHBoxLayout()
        frame_row.addWidget(QLabel("Frame comparado:"))
        self._frame_combo = QComboBox()
        self._frame_combo.addItems(["gripper_tcp", "tool0"])
        frame_row.addWidget(self._frame_combo)
        frame_row.addStretch(1)
        passport.addLayout(frame_row)

        self._pose_table = QTableWidget(6, 3)
        self._pose_table.setHorizontalHeaderLabels(["DH analítica", "RViz (TF)", "|Δ|"])
        self._pose_table.setVerticalHeaderLabels(
            ["x [mm]", "y [mm]", "z [mm]", "roll [°]", "pitch [°]", "yaw [°]"]
        )
        self._pose_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._pose_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._pose_table.setFont(QFont("Monospace", 10))
        self._pose_table.setMinimumHeight(215)
        passport.addWidget(self._pose_table)

        self._delta_label = QLabel("ΔE = —")
        self._delta_label.setStyleSheet("font-size:20px; font-weight:bold;")
        self._passport_badge = QLabel()
        _badge(self._passport_badge, "ESPERANDO TF", COLOR_WAIT)
        delta_row = QHBoxLayout()
        delta_row.addWidget(self._delta_label)
        delta_row.addStretch(1)
        delta_row.addWidget(self._passport_badge)
        passport.addLayout(delta_row)
        self._rotation_label = QLabel("Error de orientación: —")
        passport.addWidget(self._rotation_label)

        self._validator_label = QLabel()
        self._validator_label.setWordWrap(True)
        self._validator_label.setStyleSheet("color:#555;")
        passport.addWidget(self._validator_label)
        passport.addStretch(1)
        layout.addWidget(passport_box, 4)
        return tab

    # ------------------------------------------------------------------ pestana 2
    def _build_tests_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        live_box = QGroupBox(
            "1 · Pasaporte contra RViz: mueve el gemelo a cada postura justificada y mide ΔE en el TF"
        )
        live_layout = QVBoxLayout(live_box)
        live_controls = QHBoxLayout()
        self._live_button = QPushButton("Verificar posturas en RViz")
        self._live_button.clicked.connect(self._start_live)
        live_controls.addWidget(self._live_button)
        self._live_summary = QLabel("Sin ejecutar.")
        live_controls.addWidget(self._live_summary, 1)
        live_layout.addLayout(live_controls)
        self._live_table = QTableWidget(0, 6)
        self._live_table.setHorizontalHeaderLabels(
            ["Postura", "q [°]", "p RViz gripper_tcp [mm]", "ΔE TF [m]", "e_R [rad]", "Resultado"]
        )
        self._live_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._live_table.horizontalHeader().setStretchLastSection(True)
        self._live_table.setMaximumHeight(150)
        live_layout.addWidget(self._live_table)
        layout.addWidget(live_box)

        suite_box = QGroupBox(
            "2 · Batería DH vs URDF (cadena del URDF evaluada sin ROS, igual que verify_model)"
        )
        suite_layout = QVBoxLayout(suite_box)
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Posturas aleatorias (semilla 342):"))
        self._random_count = QSpinBox()
        self._random_count.setRange(0, 2000)
        self._random_count.setValue(100)
        controls.addWidget(self._random_count)
        run_button = QPushButton("Ejecutar batería")
        run_button.clicked.connect(self._run_suite)
        controls.addWidget(run_button)
        show_button = QPushButton("Mostrar seleccionada en RViz")
        show_button.clicked.connect(self._show_selected)
        controls.addWidget(show_button)
        export_button = QPushButton("Exportar CSV…")
        export_button.clicked.connect(self._export_suite)
        controls.addWidget(export_button)
        controls.addStretch(1)
        suite_layout.addLayout(controls)
        self._suite_summary = QLabel("Sin ejecutar.")
        suite_layout.addWidget(self._suite_summary)
        self._suite_table = QTableWidget(0, 7)
        self._suite_table.setHorizontalHeaderLabels(
            ["Caso", "Frame", "q [°]", "p DH [mm]", "e_p [m]", "e_R [rad]", "Resultado"]
        )
        self._suite_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._suite_table.horizontalHeader().setStretchLastSection(True)
        self._suite_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._suite_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._suite_table.cellDoubleClicked.connect(lambda _row, _column: self._show_selected())
        suite_layout.addWidget(self._suite_table)
        layout.addWidget(suite_box, 1)
        return tab

    # ------------------------------------------------------------------ control articular
    def _values(self) -> list[float]:
        return [spin.value() for spin in self._spins]

    def _set_values(self, joints_deg, publish: bool) -> None:
        for slider, spin, value in zip(self._sliders, self._spins, joints_deg, strict=True):
            slider.blockSignals(True)
            spin.blockSignals(True)
            spin.setValue(float(value))
            slider.setValue(int(round(float(value) * SLIDER_STEPS_PER_DEG)))
            slider.blockSignals(False)
            spin.blockSignals(False)
        if publish:
            self._last_user_edit = time.monotonic()
            self._publish_current()

    def _slider_moved(self, index: int, value: int) -> None:
        spin = self._spins[index]
        spin.blockSignals(True)
        spin.setValue(value / SLIDER_STEPS_PER_DEG)
        spin.blockSignals(False)
        self._schedule_publish()

    def _spin_changed(self, index: int, value: float) -> None:
        slider = self._sliders[index]
        slider.blockSignals(True)
        slider.setValue(int(round(value * SLIDER_STEPS_PER_DEG)))
        slider.blockSignals(False)
        self._schedule_publish()

    def _schedule_publish(self) -> None:
        self._last_user_edit = time.monotonic()
        if not self._publish_timer.isActive():
            self._publish_timer.start(30)

    def _publish_current(self) -> None:
        joints = self._values()
        self._node.publish_command(joints)
        formatted = ", ".join(f"{value:.1f}" for value in joints)
        self.statusBar().showMessage(f"Comando enviado: q = [{formatted}] °")

    def _apply_preset(self, name: str) -> None:
        self._demo_check.setChecked(False)
        self._set_values(PRESETS_DEG[name], publish=True)

    def _apply_random(self) -> None:
        self._demo_check.setChecked(False)
        seed = int(time.time() * 1000) % 2**32
        self._set_values(random_poses(1, seed)[0].joints_deg, publish=True)

    def _toggle_demo(self, enabled: bool) -> None:
        for slider, spin in zip(self._sliders, self._spins, strict=True):
            slider.setEnabled(not enabled)
            spin.setEnabled(not enabled)
        if enabled:
            self._demo_start = time.monotonic()
            self._demo_timer.start(50)
        else:
            self._demo_timer.stop()
            self._demo_start = None

    def _demo_step(self) -> None:
        if self._demo_start is None:
            return
        command = interpolate_demo(time.monotonic() - self._demo_start, 3.0)
        self._set_values(command.tolist(), publish=True)

    # ------------------------------------------------------------------ ROS y pasaporte
    def _spin_ros(self) -> None:
        if not rclpy.ok():
            self.close()
            return
        for _ in range(50):
            self._executor.spin_once(timeout_sec=0.0)

    def _sync_from_joint_state(self, joints_deg: list[float]) -> None:
        """Refleja una fuente externa (motion_demo o ros2 topic pub) en los controles."""
        if self._demo_start is not None or self._live_timer.isActive():
            return
        if time.monotonic() - self._last_user_edit < USER_EDIT_HOLD_S:
            return
        if any(spin.hasFocus() for spin in self._spins):
            return
        if max(abs(a - b) for a, b in zip(joints_deg, self._values(), strict=True)) > 0.05:
            self._set_values(joints_deg, publish=False)

    def _refresh_passport(self) -> None:
        state = self._node.joint_state
        validator = (
            "Validador ROS (fk_validator): "
            f"DH vs URDF = {self._format_error(self._node.validator_urdf_error_m)}, "
            f"DH vs TF = {self._format_error(self._node.validator_tf_error_m)}."
        )
        self._validator_label.setText(validator)
        if state is None:
            _badge(self._passport_badge, "SIN /joint_states", COLOR_WAIT)
            return
        self._sync_from_joint_state(state[1])
        frame = self._frame_combo.currentText()
        matched = self._node.latest_with_tf(frame)
        # Sin TF todavia, se muestra la DH del ultimo estado; con TF, el par emparejado.
        joints_deg, measured = (state[1], None) if matched is None else matched
        analytic = analytic_transform(joints_deg, frame)
        analytic_values = [*(analytic[:3, 3] * 1000.0), *rpy_deg(analytic)]
        for row, value in enumerate(analytic_values):
            self._pose_table.setItem(row, 0, _item(f"{value:+.4f}", True))
        if measured is None:
            for row in range(6):
                self._pose_table.setItem(row, 1, _item("—", True))
                self._pose_table.setItem(row, 2, _item("—", True))
            _badge(self._passport_badge, "ESPERANDO TF", COLOR_WAIT)
            return
        measured_values = [*(measured[:3, 3] * 1000.0), *rpy_deg(measured)]
        for row, (a, m) in enumerate(zip(analytic_values, measured_values, strict=True)):
            self._pose_table.setItem(row, 1, _item(f"{m:+.4f}", True))
            self._pose_table.setItem(row, 2, _item(f"{abs(a - m):.2e}", True))
        error_m = position_error_m(analytic, measured)
        self._delta_label.setText(f"ΔE = {error_m:.3e} m   (límite {DEFAULT_TOLERANCE_M:.0e} m)")
        self._rotation_label.setText(
            f"Error de orientación: {rotation_error_rad(analytic, measured):.3e} rad"
        )
        if error_m < DEFAULT_TOLERANCE_M:
            _badge(self._passport_badge, "APROBADO", COLOR_OK)
        else:
            _badge(self._passport_badge, "FUERA DE TOLERANCIA", COLOR_FAIL)

    @staticmethod
    def _format_error(value: float | None) -> str:
        return "esperando" if value is None else f"{value:.3e} m"

    # ------------------------------------------------------------------ verificacion en RViz
    def _start_live(self) -> None:
        self._demo_check.setChecked(False)
        self._live_queue = list(VALIDATION_POSES)
        self._live_table.setRowCount(0)
        self._live_button.setEnabled(False)
        self._live_summary.setText("Ejecutando…")
        self._live_next_pose()
        self._live_timer.start(100)

    def _live_next_pose(self) -> None:
        pose = self._live_queue[0]
        self._set_values(pose.joints_deg, publish=True)
        self._live_deadline = time.monotonic() + LIVE_SETTLE_S

    def _live_step(self) -> None:
        if time.monotonic() < self._live_deadline:
            return
        pose = self._live_queue[0]
        state = self._node.joint_state
        measured = None
        if state is not None and np.allclose(state[1], pose.joints_deg, atol=1e-6):
            measured = self._node.lookup("gripper_tcp", state[0])
        if measured is None and time.monotonic() < self._live_deadline + 3.0:
            return  # el TF aun no refleja la postura; se espera un poco mas
        row = self._live_table.rowCount()
        self._live_table.insertRow(row)
        self._live_table.setItem(row, 0, _item(pose.name))
        self._live_table.setItem(row, 1, _item(", ".join(f"{v:g}" for v in pose.joints_deg)))
        if measured is None:
            self._live_table.setItem(row, 5, self._result_item(None))
        else:
            analytic = analytic_transform(pose.joints_deg, "gripper_tcp")
            error_m = position_error_m(analytic, measured)
            position = ", ".join(f"{v:.3f}" for v in measured[:3, 3] * 1000.0)
            self._live_table.setItem(row, 2, _item(position))
            self._live_table.setItem(row, 3, _item(f"{error_m:.3e}", True))
            self._live_table.setItem(
                row, 4, _item(f"{rotation_error_rad(analytic, measured):.3e}", True)
            )
            self._live_table.setItem(row, 5, self._result_item(error_m < DEFAULT_TOLERANCE_M))
        self._live_queue.pop(0)
        if self._live_queue:
            self._live_next_pose()
            return
        self._live_timer.stop()
        self._live_button.setEnabled(True)
        results = [
            self._live_table.item(index, 5).text() for index in range(self._live_table.rowCount())
        ]
        passed = results.count("APROBADO")
        self._live_summary.setText(
            f"{passed}/{len(results)} posturas con ΔE < {DEFAULT_TOLERANCE_M:.0e} m en el TF de RViz."
        )

    @staticmethod
    def _result_item(passed: bool | None) -> QTableWidgetItem:
        text = {True: "APROBADO", False: "FUERA", None: "SIN TF"}[passed]
        color = {True: COLOR_OK, False: COLOR_FAIL, None: COLOR_WAIT}[passed]
        item = _item(text)
        item.setForeground(QColor(color))
        item.setFont(QFont("Sans", 9, QFont.Bold))
        return item

    # ------------------------------------------------------------------ bateria DH vs URDF
    def _run_suite(self) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            started = time.monotonic()
            self._suite_results = run_suite(self._urdf_path, self._random_count.value())
            elapsed = time.monotonic() - started
        finally:
            QApplication.restoreOverrideCursor()
        table = self._suite_table
        table.setRowCount(len(self._suite_results))
        for row, result in enumerate(self._suite_results):
            table.setItem(row, 0, _item(result.case))
            table.setItem(row, 1, _item(result.frame))
            table.setItem(row, 2, _item(", ".join(f"{v:.1f}" for v in result.joints_deg)))
            table.setItem(
                row, 3, _item(", ".join(f"{v * 1000:.2f}" for v in result.position_dh_m))
            )
            table.setItem(row, 4, _item(f"{result.position_error_m:.3e}", True))
            table.setItem(row, 5, _item(f"{result.rotation_error_rad:.3e}", True))
            table.setItem(row, 6, self._result_item(result.passed))
        passed = sum(result.passed for result in self._suite_results)
        worst = max(result.position_error_m for result in self._suite_results)
        worst_rotation = max(result.rotation_error_rad for result in self._suite_results)
        verdict = "APROBADO" if passed == len(self._suite_results) else "NO APROBADO"
        self._suite_summary.setText(
            f"<b>{verdict}</b> · {passed}/{len(self._suite_results)} comparaciones "
            f"({len(VALIDATION_POSES)} justificadas + {self._random_count.value()} aleatorias, "
            f"×{len(FRAMES)} frames) · máx e_p = {worst:.3e} m · máx e_R = "
            f"{worst_rotation:.3e} rad · {elapsed:.2f} s"
        )

    def _show_selected(self) -> None:
        rows = self._suite_table.selectionModel().selectedRows()
        if not rows:
            self.statusBar().showMessage("Seleccione una fila de la batería.")
            return
        result = self._suite_results[rows[0].row()]
        self._demo_check.setChecked(False)
        self._frame_combo.setCurrentText(result.frame)
        self._set_values(result.joints_deg, publish=True)
        self._tabs.setCurrentIndex(0)

    def _export_suite(self) -> None:
        if not self._suite_results:
            self.statusBar().showMessage("Ejecute la batería antes de exportar.")
            return
        path, _filter = QFileDialog.getSaveFileName(
            self, "Exportar batería", str(Path.home() / "hito1_bateria.csv"), "CSV (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["case", "frame", "q_deg", "p_dh_m", "p_urdf_m", "position_error_m",
                 "rotation_error_rad", "passed"]
            )
            for result in self._suite_results:
                writer.writerow(
                    [
                        result.case,
                        result.frame,
                        " ".join(f"{v:g}" for v in result.joints_deg),
                        " ".join(f"{v:.12f}" for v in result.position_dh_m),
                        " ".join(f"{v:.12f}" for v in result.position_urdf_m),
                        f"{result.position_error_m:.6e}",
                        f"{result.rotation_error_rad:.6e}",
                        result.passed,
                    ]
                )
        self.statusBar().showMessage(f"Batería exportada a {path}")


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = PanelNode()
    executor = SingleThreadedExecutor()
    executor.add_node(node)
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    # Ctrl+C en la terminal cierra la ventana; el temporizador ROS deja correr Python.
    signal.signal(signal.SIGINT, lambda *_unused: app.quit())
    try:
        window = ControlPanel(node, executor)
        window.show()
        app.exec_()
    finally:
        executor.remove_node(node)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
