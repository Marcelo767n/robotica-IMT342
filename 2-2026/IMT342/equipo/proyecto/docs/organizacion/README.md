# Organización del proyecto

> **Histórico.** Historial de la reorganización del 20/10/2026. La organización vigente está en el [README del proyecto](../../README.md).

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
| Ocho PDF/TEX de Hito 2 en la carpeta docente | `material_docente/hito_2/` |
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

## Cambios del 17/11/2026

| Cambio | Detalle |
|---|---|
| `AVANCE_2026-11-10.md` | Movido a [`docs/bitacora/`](../bitacora/README.md) |
| `graphify-out/` | Fuera del repositorio: se conserva en disco pero está ignorada en `.gitignore` |
| `.claude/` | Ignorada por Git |
| READMEs nuevos | `docs/README.md`, `docs/bitacora/`, `docs/hito2/`, `ros2_ws/src/irb120_rviz_panel/` y `ros2_ws/src/irb120_hito2/` |
| Panel de RViz | Panel C++ «IRB 120» ([`irb120_rviz_panel`](../../ros2_ws/src/irb120_rviz_panel/README.md)), control 3D y paquete Python `irb120_control/panel/` |
| `ros2_ws/brazo.sh` | Script único de comandos para mover el robot; el [README de `ros2_ws`](../../ros2_ws/README.md) lo presenta como forma principal de uso |

Qué no debe moverse:

- `model_manifest.yaml` y `ros2_ws/` deben seguir juntos en la raíz del proyecto: `ros2_ws/src/irb120_conexion/irb120_conexion/rutas.py` los usa para encontrar la raíz.
- `hito2/` no se mueve: el control del robot importa su cinemática.
