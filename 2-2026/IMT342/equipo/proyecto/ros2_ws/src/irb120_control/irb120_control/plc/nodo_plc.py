"""Nodo ROS 2 `irb120_plc_s7`: transporte y traducción binaria PLC S7-1200 ↔ JSON. No decide nada.

Publica  /irb120/plc/entrada  (String JSON, §4) en cada TG_ORDEN recibido y a 1 Hz (enlace=false sin PLC)
Escucha  /irb120/plc/salida   (String JSON, §4); cada 100 ms envía TG_ESTADO con `vida` propia.
Sin salida reciente (> 2 s) envía enlace=0, error=1 y valor=3 para que el PLC lo sepa.
El bit 15 (`vida`) de cada TG_ESTADO alterna en cada envío.

    python -m irb120_control.plc.nodo_plc [--modo servidor|cliente] [--host H] [--puerto 2000]
                                          [--plc-ip IP] [--guardian 1.0] [--formato nucleo|completo]
                                          [--config celda.yaml]"""
import argparse
import json
import logging
import os
import sys
import time

from irb120_control.plc.telegrama import (COMPLETO, FORMATOS, estado_desde_dict, estado_sin_brazo, largo_orden,
                                         orden_a_dict)
from irb120_control.plc.transporte import Transporte

ENTRADA_TOPIC = '/irb120/plc/entrada'
SALIDA_TOPIC = '/irb120/plc/salida'
SALIDA_MAX_S = 2.
PERIODO_ESTADO_S = .1
CONFIG_DEFECTO = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                              'config', 'celda.yaml')


def leer_config(ruta):
    """Sección `plc:` del YAML (vacía si no existe o no hay PyYAML)."""
    if not ruta or not os.path.isfile(ruta):
        return {}
    try:
        import yaml
        with open(ruta, encoding='utf-8') as archivo:
            return (yaml.safe_load(archivo) or {}).get('plc') or {}
    except Exception as error:
        logging.getLogger('irb120_plc_s7').warning('No se pudo leer %s: %s', ruta, error)
        return {}


def parsear(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--config', help='YAML de la celda (por defecto config/celda.yaml)')
    parser.add_argument('--modo', choices=('servidor', 'cliente'))
    parser.add_argument('--host', help='interfaz de escucha (servidor)')
    parser.add_argument('--puerto', type=int)
    parser.add_argument('--plc-ip', help='IP del PLC (cliente)')
    parser.add_argument('--formato', choices=FORMATOS, help='nucleo (4 B) o completo (36 B / 68 B)')
    parser.add_argument('--guardian', type=float, help='segundos sin trama válida → enlace perdido')
    args = parser.parse_args(argv)
    cfg = leer_config(args.config or CONFIG_DEFECTO)
    def valor(cli, clave, defecto):
        return cli if cli is not None else cfg.get(clave, defecto)
    return {'modo': valor(args.modo, 'modo', 'servidor'), 'host': valor(args.host, 'host', '0.0.0.0'),
            'puerto': int(valor(args.puerto, 'puerto', 2000)), 'ip': valor(args.plc_ip, 'ip', ''),
            'guardian_s': float(valor(args.guardian, 'guardian_s', 1.)),
            'formato': valor(args.formato, 'formato', COMPLETO)}


class NodoPlc:
    def __init__(self, node, ajustes):
        from std_msgs.msg import String
        self.String, self.node = String, node
        self.formato = ajustes.pop('formato')
        if self.formato not in FORMATOS:
            raise ValueError(f'formato no válido: {self.formato}')
        self.vida = False
        self.salida = None
        self.t_salida = 0.
        self.entrada_pub = node.create_publisher(String, ENTRADA_TOPIC, 10)
        node.create_subscription(String, SALIDA_TOPIC, self.on_salida, 10)
        self.transporte = Transporte(self.on_orden, largo=largo_orden(self.formato), **ajustes)
        self.transporte.iniciar()
        node.create_timer(PERIODO_ESTADO_S, self.enviar_estado)
        node.create_timer(1., self.publicar_vacio)
        self.t_publicado = 0.

    def publicar(self, orden):
        mensaje = self.String()
        mensaje.data = json.dumps(orden_a_dict(orden, self.transporte.enlace, time.time(),
                                               self.transporte.errores_trama, self.formato))
        self.entrada_pub.publish(mensaje)
        self.t_publicado = time.monotonic()

    def on_orden(self, orden):
        self.publicar(orden)

    def publicar_vacio(self):
        """1 Hz aunque no haya tramas (enlace=false cuando el perro guardián vence)."""
        if time.monotonic() - self.t_publicado >= .9:
            self.publicar(None)

    def on_salida(self, mensaje):
        try:
            self.salida = json.loads(mensaje.data)
        except ValueError:
            self.node.get_logger().warning('JSON inválido en ' + SALIDA_TOPIC)
            return
        self.t_salida = time.monotonic()

    def enviar_estado(self):
        self.vida = not self.vida
        if self.salida is None or time.monotonic() - self.t_salida > SALIDA_MAX_S:
            estado = estado_sin_brazo(self.vida)
        else:
            estado = estado_desde_dict(self.salida, self.vida)
        self.transporte.enviar(estado.pack(self.formato == COMPLETO))

    def cerrar(self):
        self.transporte.cerrar()


def main(argv=None):
    ajustes = parsear(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(message)s')
    import rclpy
    from rclpy.executors import ExternalShutdownException
    rclpy.init()
    node = rclpy.create_node('irb120_plc_s7')
    nodo = NodoPlc(node, ajustes)
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        nodo.cerrar()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return 0


if __name__ == '__main__':
    sys.exit(main())
