"""Estudio de trayectorias (CustomTkinter) y matemática del Hito 2 como bloques LaTeX.

Tk + método de entrada ibus (XIM): con ibus-daemon cargado, cada widget hace una consulta XIM y la ventana
tarda decenas de segundos en construirse (medido 20/11/2026: 30 botones 18,6 s → 0,26 s sin XIM). Se
desactiva XIM para este proceso antes de crear la ventana; IRB120_CON_XIM=1 lo deja como esté
(p. ej. si hiciera falta escribir con teclas muertas que solo compone ibus)."""
import os

if os.environ.get('IRB120_CON_XIM') != '1':
    os.environ['XMODIFIERS'] = '@im=none'
