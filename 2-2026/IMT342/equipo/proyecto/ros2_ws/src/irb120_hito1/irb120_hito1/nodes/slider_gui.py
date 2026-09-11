"""Panel grafico de deslizadores para controlar el ABB IRB 120."""

import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

from irb120_hito1.slider_controls import JOINT_SLIDERS, PRESETS_DEG, command_payload


class SliderCommandPublisher(Node):
    """Publica comandos compatibles con ``joint_state_source``."""

    def __init__(self) -> None:
        super().__init__("irb120_slider_gui")
        self._publisher = self.create_publisher(
            Float64MultiArray, "/irb120/joint_commands_deg", 10
        )

    def publish_command(self, joints_deg: list[float]) -> None:
        message = Float64MultiArray()
        message.data = command_payload(joints_deg)
        self._publisher.publish(message)


class SliderPanel:
    """Interfaz Tk compacta para mover las seis juntas en tiempo real."""

    def __init__(self, root: tk.Tk, node: SliderCommandPublisher) -> None:
        self._root = root
        self._node = node
        self._pending_publish: str | None = None
        self._joint_values: list[tk.DoubleVar] = []
        self._status = tk.StringVar(value="Listo: mueva cualquier deslizador")

        root.title("ABB IRB 120 - Control de articulaciones")
        root.geometry("650x570")
        root.minsize(570, 520)

        container = ttk.Frame(root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Control manual ABB IRB 120",
            font=("Sans", 16, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            container,
            text="Seis juntas revolutas; ángulos expresados en grados.",
        ).pack(anchor="w", pady=(2, 12))

        for spec in JOINT_SLIDERS:
            value = tk.DoubleVar(value=0.0)
            self._joint_values.append(value)
            row = ttk.Frame(container)
            row.pack(fill="x", pady=3)
            ttk.Label(row, text=spec.label, width=25).pack(side="left")
            scale = tk.Scale(
                row,
                variable=value,
                from_=spec.lower_deg,
                to=spec.upper_deg,
                resolution=1.0,
                orient="horizontal",
                length=330,
                command=self._schedule_publish,
            )
            scale.pack(side="left", fill="x", expand=True)

        buttons = ttk.Frame(container)
        buttons.pack(fill="x", pady=(14, 8))
        for preset_name in PRESETS_DEG:
            ttk.Button(
                buttons,
                text=preset_name,
                command=lambda name=preset_name: self._apply_preset(name),
            ).pack(side="left", padx=(0, 8))

        ttk.Separator(container).pack(fill="x", pady=8)
        ttk.Label(container, textvariable=self._status).pack(anchor="w")
        ttk.Label(
            container,
            text="RViz debe permanecer abierto. Cierre esta ventana o use Ctrl+C para terminar.",
        ).pack(anchor="w", pady=(5, 0))

        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.after(350, self._publish)
        root.after(100, self._poll_ros)

    def _values(self) -> list[float]:
        return [float(value.get()) for value in self._joint_values]

    def _schedule_publish(self, _unused: str | None = None) -> None:
        if self._pending_publish is not None:
            self._root.after_cancel(self._pending_publish)
        self._pending_publish = self._root.after(25, self._publish)

    def _publish(self) -> None:
        self._pending_publish = None
        joints = self._values()
        self._node.publish_command(joints)
        formatted = ", ".join(f"{value:.0f}" for value in joints)
        self._status.set(f"Enviado: q=[{formatted}] grados")

    def _apply_preset(self, name: str) -> None:
        for variable, value in zip(self._joint_values, PRESETS_DEG[name], strict=True):
            variable.set(value)
        self._publish()

    def _poll_ros(self) -> None:
        if not rclpy.ok():
            self._root.destroy()
            return
        rclpy.spin_once(self._node, timeout_sec=0.0)
        self._root.after(100, self._poll_ros)


def main(args: list[str] | None = None) -> None:
    rclpy.init(args=args)
    node = SliderCommandPublisher()
    root: tk.Tk | None = None
    try:
        root = tk.Tk()
        SliderPanel(root, node)
        root.mainloop()
    except (KeyboardInterrupt, tk.TclError) as error:
        if isinstance(error, tk.TclError):
            node.get_logger().error(f"No se pudo abrir la interfaz grafica: {error}")
    finally:
        if root is not None:
            try:
                root.destroy()
            except tk.TclError:
                pass
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
