"""Interfaz de análisis (solo lectura): lo del Hito 2 aplicado en vivo a la pose del panel.

Módulos:
  modelo.py      importa el paquete hito2/irb120 (DH, Pieper, LSPB, Jacobiano, dinámica)
  fuente.py      lee el estado del panel por HTTP local (GET /estado) o usa datos de demostración
  calculos.py    todos los cálculos, puros y con caché (sin interfaz)
  vistas/        una pestaña por tema (cinemática, ramas IK, LSPB, Jacobiano, dinámica)
  app.py         ventana tkinter + matplotlib
Ejecutar: python3 -m irb120_control.analisis [--url URL] [--demo]
"""
