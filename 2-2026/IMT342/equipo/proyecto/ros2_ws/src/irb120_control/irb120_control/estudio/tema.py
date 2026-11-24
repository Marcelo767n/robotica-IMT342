"""Colores y fuentes del Estudio. Los colores son (claro, oscuro) para que CustomTkinter los conmute solo."""
import customtkinter as ctk

BASE_PX = 16

COLORES = {
    'fondo': ('#f3f4f6', '#111827'), 'tarjeta': ('#ffffff', '#1f2937'), 'borde': ('#d1d5db', '#374151'),
    'texto': ('#111827', '#f3f4f6'), 'suave': ('#4b5563', '#9ca3af'),
    'ok': ('#15803d', '#22c55e'), 'aviso': ('#b45309', '#f59e0b'), 'falla': ('#b91c1c', '#ef4444'),
    'nada': ('#6b7280', '#6b7280'), 'acento': ('#1d4ed8', '#3b82f6'),
    'ok_fondo': ('#dcfce7', '#14532d'), 'aviso_fondo': ('#fef3c7', '#78350f'), 'falla_fondo': ('#fee2e2', '#7f1d1d'),
    'nada_fondo': ('#e5e7eb', '#374151'),
}
ESTADOS = ('ok', 'aviso', 'falla', 'nada')
_fuentes = {}


def color(nombre, oscuro=False):
    """Color concreto (hex) para matplotlib u otras bibliotecas sin tuplas."""
    return COLORES[nombre][1 if oscuro else 0]


def fuente(delta=0, negrita=False, mono=False):
    clave = (delta, negrita, mono)
    if clave not in _fuentes:
        _fuentes[clave] = ctk.CTkFont(family='DejaVu Sans Mono' if mono else 'DejaVu Sans',
                                      size=BASE_PX + delta, weight='bold' if negrita else 'normal')
    return _fuentes[clave]


def es_oscuro():
    return ctk.get_appearance_mode() == 'Dark'


def parchear_scrollbar():
    """CTkScrollbar._draw llama a update_idletasks, que vuelve a llamar a set(): con cierta geometría se
    encadena sin fin y la ventana se congela. Se evita la reentrada."""
    from customtkinter.windows.widgets.ctk_scrollbar import CTkScrollbar
    if getattr(CTkScrollbar, '_estudio_parche', False):
        return
    original = CTkScrollbar._draw

    def _draw(self, *a, **k):
        # Además del cerrojo por barra: el update_idletasks() final de CTkScrollbar._draw atiende los
        # set() de OTRAS barras (horizontal ↔ vertical de la misma tabla), que vuelven a dibujar y así sin
        # fin. Se anula ese update anidado; Tk repinta en su ciclo normal.
        if getattr(self, '_en_draw', False):
            return
        self._en_draw = True
        canvas = self._canvas
        canvas.update_idletasks = lambda: None
        try:
            original(self, *a, **k)
        finally:
            del canvas.update_idletasks
            self._en_draw = False
    CTkScrollbar._draw = _draw
    CTkScrollbar._estudio_parche = True
