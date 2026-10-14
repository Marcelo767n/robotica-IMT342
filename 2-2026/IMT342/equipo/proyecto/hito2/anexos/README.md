# Anexos: material de la versión anterior del Hito 2

Estos notebooks y scripts se hicieron para la **Guía PFI anterior**: nodo ROS más un "pasaporte" de divergencia en
`q5 = 0`. Se conservan como referencia, pero **no son el entregable** de la guía oficial del Hito 2 (semana 10).

- Usan el TCP antiguo de 0.100 m. El paquete actual usa **0.150 m**, así que si se vuelven a ejecutar los números
  cambian.
- `03_singularidad_q5.ipynb` muestra que los torques divergen cerca de `q5 = 0` **cuando se obliga al robot a seguir
  una trayectoria cartesiana** ($\ddot q = J^{-1}(\ddot x - \dot J \dot q)$). Eso **no** significa que la singularidad
  produzca un torque infinito por sí misma. La interpretación correcta, alineada con la rúbrica, está en
  [`../explicacion/06_D_singularidades.md`](../explicacion/06_D_singularidades.md).
- `EXPLICACION_MATEMATICA.md` es la explicación de esa versión. La vigente es la carpeta [`../explicacion/`](../explicacion/).

Para regenerarlos (desde `hito2/anexos/`): `python build_notebooks.py`.
