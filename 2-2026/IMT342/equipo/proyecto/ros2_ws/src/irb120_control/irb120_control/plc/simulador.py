"""PLC S7-1200 simulado (sin ROS): para probar la pasarela sin hardware.

Por defecto es CLIENTE y conecta a la PC (127.0.0.1:2000); con --modo servidor escucha él.
Envía el telegrama de mando cada 100 ms (bit 15 `vida` alternando) y muestra el último estado.
Cada orden pone su bit, espera aceptada/rechazada (5 s) y lo baja (saludo de §3.1).

Órdenes (teclado o --guion "a; b; esperar 5"):
    habilitar on|off · ejecutar N [vel] [rep] · pausar · reanudar · cancelar · reposo · velocidad N
    punto X Y Z R P Y (solo formato completo) · acusar · estado · esperar S · salir

    python -m irb120_control.plc.simulador [--modo servidor] [--ip 127.0.0.1] [--puerto 2000]
                                           [--formato nucleo|completo] [--guion ...]"""
import argparse
import sys
import threading
import time

from irb120_control.plc import telegrama as tg
from irb120_control.plc.transporte import Transporte

PERIODO_S = .1
SALUDO_S = 5.


class PlcSimulado:
    def __init__(self, modo='cliente', ip='127.0.0.1', host='127.0.0.1', puerto=2000, guardian_s=1.,
                 formato=tg.COMPLETO, saludo_s=SALUDO_S):
        self.formato, self.saludo_s = formato, saludo_s
        self.completo = formato == tg.COMPLETO
        self.orden = tg.Orden(velocidad_pct=30, repeticiones=1, pose=[0.] * 6)
        self.ultimo_estado = None
        self._vida = False
        self._cerrojo = threading.Lock()
        self._parar = threading.Event()
        self.transporte = Transporte(self._on_estado, modo=modo, host=host, puerto=puerto, ip=ip,
                                     guardian_s=guardian_s, largo=tg.largo_estado(formato),
                                     decodificar=tg.Estado.unpack)
        self._hilo = threading.Thread(target=self._ciclo, name='plc-simulado', daemon=True)

    def iniciar(self):
        self.transporte.iniciar()
        self._hilo.start()
        return self

    def cerrar(self):
        self._parar.set()
        self._hilo.join(2.)
        self.transporte.cerrar()

    def _on_estado(self, estado):
        self.ultimo_estado = estado

    def _ciclo(self):
        while not self._parar.is_set():
            with self._cerrojo:
                self._vida = not self._vida
                self.orden.mando = (self.orden.mando & ~tg.BIT_VIDA) | (tg.BIT_VIDA if self._vida else 0)
                datos = self.orden.pack(self.completo)
            self.transporte.enviar(datos)
            self._parar.wait(PERIODO_S)

    def _mando(self, poner=0, quitar=0, **campos):
        with self._cerrojo:
            self.orden.mando = (self.orden.mando | poner) & ~quitar
            for clave, valor in campos.items():
                setattr(self.orden, clave, valor)

    def habilitar(self, activo):
        self._mando(poner=tg.MANDO_HABILITAR) if activo else self._mando(quitar=tg.MANDO_HABILITAR)

    def _esperar(self, condicion, limite):
        fin = time.monotonic() + limite
        while time.monotonic() < fin:
            if condicion():
                return True
            time.sleep(.02)
        return False

    def _saludo_libre(self):
        e = self.ultimo_estado
        return e is None or not (e.bit('aceptada') or e.bit('rechazada'))

    def orden_con_saludo(self, nombre, **campos):
        """Pone el bit de la orden, espera aceptada/rechazada, lo baja y espera a que la PC baje el saludo."""
        mascara = 1 << (tg.BITS_ORDEN.index(nombre) + 1)
        self._esperar(self._saludo_libre, 1.)
        self._mando(poner=mascara, **campos)
        respondido = self._esperar(lambda: not self._saludo_libre(), self.saludo_s)
        e = self.ultimo_estado
        self._mando(quitar=mascara)
        if not respondido:
            return f'{nombre}: sin respuesta de la PC en {self.saludo_s:.0f} s'
        resultado = f'{nombre}: ACEPTADA' if e.bit('aceptada') else f'{nombre}: RECHAZADA código {e.valor}'
        self._esperar(self._saludo_libre, 1.)
        return resultado

    def descripcion(self):
        e = self.ultimo_estado
        return 'Sin estado todavía.' if e is None else tg.describir_estado(e)

    def comando(self, linea):
        """Ejecuta una línea; devuelve texto a mostrar, '' o None para salir."""
        p = linea.split()
        if not p:
            return ''
        c, a = p[0].lower(), p[1:]
        try:
            if c == 'salir':
                return None
            if c == 'habilitar':
                self.habilitar(a[0].lower() in ('on', '1', 'si', 'sí'))
                return f'mando=16#{self.orden.mando & ~tg.BIT_VIDA:04X}'
            if c == 'ejecutar':
                campos = {'valor': int(a[0])}
                if self.completo:
                    campos.update(velocidad_pct=int(a[1]) if len(a) > 1 else self.orden.velocidad_pct,
                                  repeticiones=int(a[2]) if len(a) > 2 else 1)
                return self.orden_con_saludo('ejecutar', **campos)
            if c == 'velocidad':
                return self.orden_con_saludo('velocidad', **({'velocidad_pct': int(a[0])} if self.completo
                                                             else {'valor': int(a[0])}))
            if c == 'punto':
                if not self.completo:
                    return 'punto necesita --formato completo'
                if len(a) != 6:
                    return 'uso: punto X Y Z R P Y'
                return self.orden_con_saludo('punto', pose=[float(v) for v in a])
            if c in ('pausar', 'reanudar', 'cancelar', 'reposo', 'acusar'):
                return self.orden_con_saludo(c)
            if c == 'estado':
                return self.descripcion()
            if c == 'esperar':
                time.sleep(float(a[0]))
                return self.descripcion()
            return f'Orden desconocida: {c}'
        except (IndexError, ValueError) as error:
            return f'Argumentos no válidos ({error}): {linea}'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--modo', choices=('cliente', 'servidor'), default='cliente')
    parser.add_argument('--ip', default='127.0.0.1', help='IP de la PC (modo cliente)')
    parser.add_argument('--host', default='127.0.0.1', help='interfaz de escucha (modo servidor)')
    parser.add_argument('--puerto', type=int, default=2000)
    parser.add_argument('--formato', choices=tg.FORMATOS, default=tg.COMPLETO)
    parser.add_argument('--guion', help='órdenes separadas por «;» (no interactivo)')
    args = parser.parse_args(argv)
    plc = PlcSimulado(args.modo, args.ip, args.host, args.puerto, formato=args.formato).iniciar()
    try:
        if args.guion is not None:
            for linea in args.guion.split(';'):
                salida = plc.comando(linea)
                if salida is None:
                    break
                if salida:
                    print(salida, flush=True)
            print(plc.descripcion(), flush=True)
        else:
            print(__doc__.split('Órdenes')[1].split('python')[0].strip(), flush=True)
            while True:
                try:
                    salida = plc.comando(input('plc> '))
                except EOFError:
                    break
                if salida is None:
                    break
                if salida:
                    print(salida, flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        plc.cerrar()
    return 0


if __name__ == '__main__':
    sys.exit(main())
