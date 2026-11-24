"""Nodo ROS 2 `irb120_celda`: traduce las órdenes del PLC a órdenes del brazo y el estado del brazo al PLC.

  python -m irb120_control.celda.nodo_celda [--config celda.yaml] [--carpeta salidas/trayectorias]

Escucha  /irb120/plc/entrada, /irb120/panel/estado   (std_msgs/String JSON)
Publica  /irb120/panel/orden, /irb120/plc/salida     (salida a 10 Hz y tras cada cambio)
Toda la lógica está en traductor.py; aquí solo hay transporte y el hilo que planifica (~1,5 s) sin bloquear.
"""
import argparse
import json
import threading
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from irb120_control.celda import config
from irb120_control.celda.traductor import Traductor

ENTRADA, SALIDA = '/irb120/plc/entrada', '/irb120/plc/salida'
ESTADO, ORDEN = '/irb120/panel/estado', '/irb120/panel/orden'


class NodoCelda(Node):
    def __init__(self, rutas, reposo):
        super().__init__('irb120_celda')
        self.traductor = Traductor(rutas, reposo=reposo)
        self.cerrojo = threading.Lock()
        self.vistos = 0
        self.ultima = None
        self.pub_orden = self.create_publisher(String, ORDEN, 10)
        self.pub_salida = self.create_publisher(String, SALIDA, 10)
        self.create_subscription(String, ENTRADA, lambda m: self._recibir(m, 'entrada_plc'), 10)
        self.create_subscription(String, ESTADO, lambda m: self._recibir(m, 'estado_brazo'), 10)
        self.create_timer(.1, self._tic)
        threading.Thread(target=self._planificador, daemon=True, name='celda-planificador').start()
        self.get_logger().info(f'Celda lista. Trayectorias: {sorted(rutas)}')

    def _recibir(self, msg, metodo):
        try:
            d = json.loads(msg.data)
        except ValueError:
            self.get_logger().warn(f'{metodo}: JSON no válido')
            return
        with self.cerrojo:
            getattr(self.traductor, metodo)(d)
        self._volcar()

    def _tic(self):
        with self.cerrojo:
            self.traductor.tic()
        self._volcar(forzar=True)

    def _volcar(self, forzar=False):
        """Publica las órdenes pendientes, lo nuevo del registro y la salida (si cambió o por el ciclo de 10 Hz)."""
        with self.cerrojo:
            ordenes = self.traductor.tomar_ordenes()
            registro, total = self.traductor.registro(), self.traductor.n_registro
            salida = self.traductor.salida()
        for o in ordenes:
            self.get_logger().info(f'Orden al brazo: {json.dumps(o)[:200]}')
            self.pub_orden.publish(String(data=json.dumps(o)))
        for linea in registro[max(0, len(registro) - (total - self.vistos)):]:
            self.get_logger().info(linea)
        self.vistos = total
        if forzar or salida != self.ultima:
            self.ultima = salida
            self.pub_salida.publish(String(data=json.dumps(salida)))

    def _planificador(self):
        while rclpy.ok():
            with self.cerrojo:
                trabajo = self.traductor.tomar_trabajo()
            if trabajo is None:
                time.sleep(.05)
                continue
            resultado = trabajo.calcular()                # ~1,5 s, fuera del cerrojo
            with self.cerrojo:
                self.traductor.completar(trabajo, resultado)
            self._volcar()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--config', default=None, help='celda.yaml (por defecto config/celda.yaml del paquete)')
    p.add_argument('--carpeta', default=None, help='carpeta de trayectorias (relativa a la raíz del proyecto)')
    args, resto = p.parse_known_args(argv)
    from irb120_conexion.rutas import PROJECT
    rutas, reposo = config.cargar(PROJECT, args.config, args.carpeta)
    rclpy.init(args=resto)
    nodo = NodoCelda(rutas, reposo)
    from rclpy.executors import ExternalShutdownException
    try:
        rclpy.spin(nodo)
    except (KeyboardInterrupt, ExternalShutdownException):   # Ctrl+C / SIGTERM: cierre limpio
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
