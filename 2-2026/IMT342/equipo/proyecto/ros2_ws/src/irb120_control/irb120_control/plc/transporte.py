"""Transporte TCP de los telegramas (sin ROS): UNA conexión, en modo servidor o cliente.

Servidor: escucha en host:puerto y acepta un cliente; si llega otro, sustituye al anterior.
Cliente: conecta a ip:puerto reintentando cada REINTENTO_S.
Las tramas tienen longitud fija (4 B núcleo, 36 B orden completa, 68 B estado completo): se acumulan los bytes del flujo (TCP puede partir o juntar
tramas) y se entrega cada Orden completa. Un resto incompleto que no se completa en PARCIAL_S se descarta
y cuenta como error de trama."""
import logging
import select
import socket
import threading
import time

from irb120_control.plc.telegrama import COMPLETO, Orden, largo_orden

LOG = logging.getLogger('irb120_plc_s7')
REINTENTO_S = 2.
PARCIAL_S = .5       # un resto de trama que no se completa en este tiempo es una trama corrupta
TIEMPO_ENVIO_S = 1.
SONDEO_S = .1


class Transporte:
    def __init__(self, al_recibir, modo='servidor', host='0.0.0.0', puerto=2000, ip='', guardian_s=1.,
                 largo=None, decodificar=Orden.unpack):
        if modo not in ('servidor', 'cliente'):
            raise ValueError("modo debe ser 'servidor' o 'cliente'")
        if modo == 'cliente' and not ip:
            raise ValueError('el modo cliente necesita la IP del PLC')
        self.al_recibir, self.modo, self.host, self.puerto, self.ip = al_recibir, modo, host, puerto, ip
        self.guardian_s, self.decodificar = guardian_s, decodificar          # el simulador lee Estado
        self.largo = largo or largo_orden(COMPLETO)                  # bytes por trama (según el formato)
        self.errores_trama = 0
        self.tramas_recibidas = 0
        self._conexion = None
        self._escucha = None
        self._cerrojo = threading.Lock()
        self._parar = threading.Event()
        self._hilo = None
        self._ultima_valida = None
        self._buffer = b''
        self._t_parcial = 0.

    # --- API pública -------------------------------------------------------------------------------------
    @property
    def enlace(self):
        """Perro guardián: llegó una trama válida dentro de guardian_s."""
        ultima = self._ultima_valida
        return ultima is not None and time.monotonic() - ultima < self.guardian_s

    @property
    def conectado(self):
        return self._conexion is not None

    def iniciar(self):
        if self.modo == 'servidor':
            escucha = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            escucha.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            escucha.bind((self.host, self.puerto))
            escucha.listen(1)
            self.puerto = escucha.getsockname()[1]      # útil con puerto 0
            self._escucha = escucha
            LOG.info('Escuchando al PLC en %s:%d', self.host, self.puerto)
        self._hilo = threading.Thread(target=self._bucle, name='plc-transporte', daemon=True)
        self._hilo.start()
        return self

    def enviar(self, datos):
        """Envía bytes por la conexión actual (thread-safe). False si no hay conexión o falla."""
        with self._cerrojo:
            conexion = self._conexion
            if conexion is None:
                return False
            try:
                conexion.sendall(datos)
                return True
            except OSError as error:
                LOG.warning('Fallo al enviar: %s', error)
                self._cerrar_conexion(conexion)
                return False

    def cerrar(self):
        self._parar.set()
        if self._hilo is not None:
            self._hilo.join(3.)
        with self._cerrojo:
            self._cerrar_conexion(self._conexion)
        if self._escucha is not None:
            self._escucha.close()
            self._escucha = None

    # --- Hilo --------------------------------------------------------------------------------------------
    def _cerrar_conexion(self, conexion):
        if conexion is None:
            return
        try:
            conexion.close()
        except OSError:
            pass
        if conexion is self._conexion:
            self._conexion = None
        self._buffer = b''

    def _instalar(self, conexion, origen):
        conexion.settimeout(TIEMPO_ENVIO_S)
        conexion.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with self._cerrojo:
            if self._conexion is not None:
                LOG.warning('Nueva conexión de %s: sustituye a la anterior', origen)
                self._cerrar_conexion(self._conexion)
            self._conexion = conexion
            self._buffer = b''
        LOG.info('PLC conectado: %s', origen)

    def _bucle(self):
        while not self._parar.is_set():
            try:
                if self.modo == 'cliente' and self._conexion is None:
                    self._conectar()
                    continue
                lectores = [s for s in (self._escucha, self._conexion) if s is not None]
                listos, _, _ = select.select(lectores, [], [], SONDEO_S)
                for sock in listos:
                    if sock is self._escucha:
                        conexion, direccion = sock.accept()
                        self._instalar(conexion, '%s:%d' % direccion[:2])
                    elif sock is self._conexion:
                        self._leer(sock)
                self._revisar_parcial()
            except (OSError, ValueError) as error:       # socket cerrado bajo los pies: reintenta
                LOG.warning('Transporte: %s', error)
                with self._cerrojo:
                    self._cerrar_conexion(self._conexion)
                self._parar.wait(.2)

    def _conectar(self):
        try:
            conexion = socket.create_connection((self.ip, self.puerto), timeout=1.)
        except OSError as error:
            LOG.debug('Sin conexión con el PLC %s:%d (%s)', self.ip, self.puerto, error)
            self._parar.wait(REINTENTO_S)
            return
        self._instalar(conexion, f'{self.ip}:{self.puerto}')

    def _leer(self, conexion):
        try:
            datos = conexion.recv(4096)
        except (socket.timeout, BlockingIOError):
            return
        except OSError:
            datos = b''
        if not datos:
            LOG.info('PLC desconectado')
            with self._cerrojo:
                self._cerrar_conexion(conexion)
            return
        self._buffer += datos
        while len(self._buffer) >= self.largo:
            trama, self._buffer = self._buffer[:self.largo], self._buffer[self.largo:]
            self._entregar(trama)
        if self._buffer:
            self._t_parcial = time.monotonic()

    def _revisar_parcial(self):
        if self._buffer and time.monotonic() - self._t_parcial > PARCIAL_S:
            LOG.warning('Trama incompleta descartada (%d bytes de %d)', len(self._buffer), self.largo)
            self._buffer = b''
            self.errores_trama += 1

    def _entregar(self, trama):
        try:
            orden = self.decodificar(trama)
        except ValueError:
            self.errores_trama += 1
            return
        self._ultima_valida = time.monotonic()
        self.tramas_recibidas += 1
        try:
            self.al_recibir(orden)
        except Exception:                                # el callback nunca debe tumbar el transporte
            LOG.exception('Error en el callback de órdenes')
