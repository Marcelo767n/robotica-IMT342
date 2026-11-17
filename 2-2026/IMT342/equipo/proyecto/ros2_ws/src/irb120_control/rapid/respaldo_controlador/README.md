# Copias de los programas RAPID del controlador

Copias de los módulos que había en la tarea `T_ROB1` del IRC5 (`120-101516`, RobotWare 6.12.01.00).
Sirven para **recuperar el programa si alguien lo borra del FlexPendant**. Cómo restaurar:
[RESPALDO_Y_RESTAURACION.md](../../../../../docs/conexion_abb/RESPALDO_Y_RESTAURACION.md).

| Carpeta | Qué contiene |
|---|---|
| [`2026-11-16/`](2026-11-16/) | `Module1.mod`: programa principal del laboratorio (rutina `main`, ajedrez por socket con la PC .203:5000). Igual el 10/11 y el 16/11 (SHA-256 `3532846e…`). `LabJointRws_antes_de_v2.mod`: versión J6 que se reemplazó el 16/11. |
| `AAAA-MM-DD_HHMM/` | Lo que genere `./brazo.sh respaldar` (todos los módulos, con `respaldo.json` y sus huellas). |

Versiones propias del equipo que se cargan en el robot (no hace falta respaldarlas, están en git):

| Archivo | Uso |
|---|---|
| [`../rws_mover/LabJointRws.mod`](../rws_mover/LabJointRws.mod) | **Vigente**: servidor de objetivos `ServidorPC` (v2). |
| [`../rws_j6/LabJointRws.mod`](../rws_j6/LabJointRws.mod) | Prueba J6 de ±0,1° (10/11), histórica. |
| [`../../../../../docs/conexion_abb/evidencias/LabJointRws_original_2026-11-10.mod`](../../../../../docs/conexion_abb/evidencias/LabJointRws_original_2026-11-10.mod) | Primera versión cargada desde RobotStudio. |

`Module1.mod` no es código del equipo: se guarda solo para poder devolver el robot al estado en que se encontró.
