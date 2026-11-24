"""Reparto de órdenes del puente ROS: 'trayectoria' y 'vista_previa' re-planifican (~1,5 s) y van a un hilo aparte
para no congelar la publicación de ejes; el resto se atiende en el hilo de spin. Sin ROS: se prueba solo."""
import json
import threading

LENTAS = ('trayectoria', 'vista_previa')
OCUPADO = 'ocupado planificando'


class Despachador:
    def __init__(self, ordenes, publicar, nuevo_hilo=threading.Thread):
        self.ordenes, self.publicar, self.nuevo_hilo = ordenes, publicar, nuevo_hilo
        self.cerrojo = threading.Lock()
        self.planificando = False

    def atender(self, texto):
        try:
            body = json.loads(texto)
            ident, accion = body.get('id'), body.get('accion')
        except (ValueError, AttributeError):
            ident = accion = None
        if accion not in LENTAS:
            self.ordenes.atender(texto)
            self.publicar()
            return
        with self.cerrojo:
            libre = not self.planificando
            self.planificando = True if libre else self.planificando
        if not libre:
            self.ordenes._fallo(ident, accion, OCUPADO)
            self.publicar()
            return
        self.nuevo_hilo(target=self._planificar, args=(texto,), daemon=True, name='panel-planificar').start()

    def _planificar(self, texto):
        try:
            self.ordenes.atender(texto)
        finally:
            with self.cerrojo:
                self.planificando = False
            self.publicar()
