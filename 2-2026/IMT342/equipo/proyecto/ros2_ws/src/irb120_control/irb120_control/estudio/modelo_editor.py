"""Lista de puntos del editor de trayectorias: lógica pura (sin Tk) para poder probarla."""
from irb120_control.trayectorias import Punto, Trayectoria
from irb120_control.trayectorias.modelo import ORIGENES


class Editor:
    def __init__(self, puntos=None):
        self.puntos = list(puntos or [])

    def __len__(self):
        return len(self.puntos)

    def nombres(self):
        return [p.nombre for p in self.puntos]

    def nombre_nuevo(self, base=None):
        """A, B, C… (o «base», «base 2»…) sin repetir los existentes."""
        usados = set(self.nombres())
        if base:
            if base not in usados:
                return base
            k = 2
            while f'{base} {k}' in usados:
                k += 1
            return f'{base} {k}'
        for n in range(1, 1000):
            c, k = '', n
            while k:
                k, r = divmod(k - 1, 26)
                c = chr(65 + r) + c
            if c not in usados:
                return c
        raise ValueError('Demasiados puntos.')

    def agregar(self, punto):
        punto.nombre = self.nombre_nuevo(punto.nombre)
        self.puntos.append(punto)
        return len(self.puntos) - 1

    def insertar(self, i, punto):
        """Inserta después del índice i (i = None o -1: al final); devuelve el índice nuevo."""
        punto.nombre = self.nombre_nuevo(punto.nombre)
        pos = len(self.puntos) if i is None or i < 0 else min(i + 1, len(self.puntos))
        self.puntos.insert(pos, punto)
        return pos

    def duplicar(self, i):
        p = self.puntos[i]
        return self.insertar(i, Punto(p.nombre, pose=p.pose and list(p.pose), q=p.q and list(p.q),
                                      origen=p.origen, tipo=p.tipo))

    def editar(self, i, punto):
        otros = [p.nombre for k, p in enumerate(self.puntos) if k != i]
        if punto.nombre in otros:
            raise ValueError(f'Ya existe un punto «{punto.nombre}».')
        self.puntos[i] = punto

    def subir(self, i):
        if 0 < i < len(self.puntos):
            self.puntos[i - 1], self.puntos[i] = self.puntos[i], self.puntos[i - 1]
            return i - 1
        return i

    def bajar(self, i):
        if 0 <= i < len(self.puntos) - 1:
            self.puntos[i + 1], self.puntos[i] = self.puntos[i], self.puntos[i + 1]
            return i + 1
        return i

    def borrar(self, i):
        if 0 <= i < len(self.puntos):
            del self.puntos[i]
        return min(i, len(self.puntos) - 1)

    def a_trayectoria(self, nombre, cerrar=True, repeticiones=1, herramienta='tcp'):
        return Trayectoria(nombre=(nombre or '').strip(), puntos=list(self.puntos), cerrar=cerrar,
                           repeticiones=repeticiones, herramienta=herramienta)

    def cargar(self, tray):
        self.puntos = list(tray.puntos)

    def desde_buzon(self, entradas, despues=None):
        """Añade las entradas del buzón {id, origen, nombre, pose, q, instante}; devuelve cuántas y el último id."""
        n, ultimo, pos = 0, 0, despues
        for e in sorted(entradas, key=lambda e: e.get('id', 0)):
            origen = e.get('origen') if e.get('origen') in ORIGENES else 'manual'
            nombre = str(e.get('nombre') or origen)
            try:
                pos = self.insertar(pos, Punto(nombre, pose=e.get('pose'), q=e.get('q'), origen=origen))
                n += 1
            except ValueError:
                pass
            ultimo = max(ultimo, int(e.get('id', 0)))
        return n, ultimo


def fmt_lista(v, dec=1):
    return '—' if v is None else ' '.join(f'{x:.{dec}f}'.replace('.', ',') for x in v)
