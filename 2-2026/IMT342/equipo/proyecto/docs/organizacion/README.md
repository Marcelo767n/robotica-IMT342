# Organización del proyecto

Reorganización del 20 de octubre de 2026, basada en la documentación W12 y en las 14 fotografías disponibles. Los nombres originales de las fotos se conservan. El registro completo de archivos trasladados, con tamaño y SHA-256 previo, está en [movimientos_2026-10-20.json](movimientos_2026-10-20.json).

## Dónde está cada cosa

| Antes | Ahora |
|---|---|
| `documentosGuia/` | `referencias/bibliografia/` |
| Dos TXT de repositorios en la raíz | `referencias/repositorios/` |
| `output/pdf/`, `output/presentation/` | `entregables/hito1/pdf/`, `entregables/hito1/presentation/` |
| `output/obsolete/` | `archivo/hito1/entregables_anteriores/` |
| `tmp/` | `archivo/hito1/generacion/` |
| `notebooks/` anterior | `archivo/hito2_ros_anterior/notebooks/` |
| `docs/hito2/guia_hito2.md`, `metodo_y_resultados.md` | `archivo/hito2_ros_anterior/documentacion/` |
| Ocho PDF/TEX de Hito 2 en la carpeta docente | `archivos que hay que presentar/hito_2/` |
| Fotos sueltas | `fotos/equipo/`, `fotos/flexpendant/`, `fotos/conexiones/` |

`hito2/`, `ros2_ws/src/` y las utilidades activas en `scripts/` mantienen su ubicación. El informe IEEE conserva sus rutas relativas a resultados y figuras. El manifiesto permanece en la raíz como solicita la guía docente.

## Qué se actualizó

- Entrada principal, índices por área y enlaces a archivos trasladados.
- Inventario y manifiesto con EGM, PC Interface y Multitasking confirmados por foto, IP de servicio y puerto X2 Service.
- Catálogo de fotos y registro estructurado de evidencias; no se dedujo RobotWare de la edad del equipo ni del nombre del sistema.
- Rutas de importación del notebook histórico y rutas de los generadores de documentos archivados, sin regenerar sus salidas.
- Exclusiones Git para renders y archivos temporales históricos; se conservan localmente y se dejan visibles las fuentes de generación.

## Criterio de uso

Las fuentes del docente se conservan intactas en su carpeta. `entregables/` permite encontrar el trabajo propio sin duplicar los notebooks ni los informes actuales. `archivo/` conserva antecedentes y no indica que sean entregables vigentes.

Para nuevas fotos, usar las subcarpetas por tipo y conservar el nombre original; actualizar [el catálogo](../../fotos/README.md). No guardar contraseñas en manifiestos o evidencias.

La [verificación de organización](verificacion_2026-10-20.json) registra preservación de fuentes y archivos trasladados, integridad de descargas y referencias locales. Esta verificación no es prueba de conexión al robot ni de funcionamiento de los generadores históricos.
