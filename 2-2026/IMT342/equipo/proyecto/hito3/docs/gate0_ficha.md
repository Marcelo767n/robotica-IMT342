# Ficha Gate 0 · Inventario local y auditoría de compatibilidad ROS–ABB

Basada en la ficha oficial W12-S01 (`w12_s01_gate0_ficha.tex`) y la versión actualizable W12-S02 (`w12_s02_ficha_gate_0.tex`). Actualizada el **24/11/2026** con la evidencia disponible en el repositorio.

| Campo | Valor |
|---|---|
| Grupo | Dayana Andrade, Mirko Ayala, Marcelo Navarro (según `README.md` del proyecto) |
| Fecha de esta versión | 2026-11-24 (la auditoría original es del 2026-10-20) |
| Responsable de la ficha | por completar por el equipo |
| Supervisión (docente / laboratorio) | por completar por el equipo |

**Regla epistémica (oficial).** `confirmado` solo con evidencia observada o fuente identificable en el sistema concreto del laboratorio. `pendiente` no significa ausente, pero prohíbe asumir compatibilidad. `incompatible` exige contradicción demostrada entre un requisito documentado y un dato local; el desconocimiento nunca es `incompatible`. Esta ficha **no aprueba hardware ni activa control**.

Rutas relativas a `proyecto/` (esta carpeta del repositorio). Las fotos están en `fotos/`.

## 1. Los 15 ítems

| # | Ítem | Dato observado | Estado | Fuente / evidencia (ruta) | Responsable | Próxima verificación |
|---|---|---|---|---|---|---|
| 1 | Manipulador / modelo exacto | ABB IRB 120-3/0.6, serie `120-101516`, fabricación 2018-01-10 (placa fotografiada). El mismo modelo aparece como opción `IRB 120-3/0.6` en la lista de opciones leída por RWS. | confirmado | `fotos/equipo/856105511_972111242619279_1826443544156678714_n.jpg`; `docs/conexion_abb/evidencias/g1_rws_2026-10-29_sanitizado.json` | por asignar | Conservar la evidencia. |
| 2 | Controlador / modelo / revisión | Hipótesis IRC5 Compact. La lista de opciones leída por RWS el 29/10 incluye `Drive System IRB 120/…/1600/1660ID IRC5 Compact`, coherente con esa hipótesis. La placa del gabinete, la revisión y el computador principal **no se han leído**. | pendiente | `docs/conexion_abb/gate0_inventario.csv` (fila Controlador); `model_manifest.yaml` (`controller_hypothesis_status: pending_nameplate_verification`); `g1_rws_2026-10-29_sanitizado.json` | por asignar | Leer placa del gabinete y System Info con el operador; no inferir el modelo DSQC a partir del puerto. |
| 3 | RobotWare versión / revisión | `6.12.01.00` (`rwversion` 6.12.1014, fecha de build 2021-05-12), respuesta HTTP 200 de `/rw/system`. Antes se había transcrito desde System properties el 22/10. | confirmado | `g1_rws_2026-10-29_sanitizado.json` (observado 2026-10-29T21:35Z); `evidencias/robotware_reportado_2026-10-22.json` (transcripción del usuario) | por asignar | Releer con `./brazo.sh estado` al inicio de cada sesión (la versión del RobotWare no se espera que cambie). |
| 4 | Opciones / licencias instaladas | 24 entradas devueltas por RWS, entre ellas `689-1 Externally Guided Motion (EGM)`, `616-1 PC Interface`, `623-1 Multitasking`, `UDPUC Driver`, `614-1 FTP SFTP and NFS client`, `RobotWare Base`. Coinciden con la foto del FlexPendant. | confirmado (presencia en la lista) | `g1_rws_2026-10-29_sanitizado.json`; `fotos/flexpendant/853082554_2593180977825989_6769481757691654016_n.jpg`; lista resumida en `model_manifest.yaml` | por asignar | Que una opción figure como instalada **no** prueba que esté configurada ni operativa (en particular EGM). Verificar con prueba, no con la lista. |
| 5 | Interfaz permitida (RWS / EGM / otra) | **RWS 1.0 (HTTP, Digest)**: lectura el 29/10 y 03–04/11; escritura de PERS y ejecución de `MoveAbsJ` por RAPID el 16–19/11. **EGM**: sin sesión ni configuración verificada. El permiso formal del laboratorio/docente para esta interfaz no consta por escrito. | confirmado (RWS + RAPID, funcional) · pendiente (EGM; autorización formal) | `evidencias/g1_rws_2026-10-29_sanitizado.json`; `docs/bitacora/2026-11-16_primer_movimiento_real.md`; `hito3/docs/evidencia_gate3_movimiento.md` | por asignar | Registrar quién autorizó el uso de RWS+RAPID (nombre, fecha); decidir con el docente si EGM es exigible. |
| 6 | Estado / método de conexión en laboratorio | Ethernet directo al puerto `X2 Service 10/100` con adaptador USB-Ethernet Realtek RTL8152; IP de la PC `192.168.125.203/24` por DHCP del controlador; `ping` a `192.168.125.1` 3/3, 0 % pérdida (RTT medio 0,826 ms). Repetido en 03/11, 04/11, 10/11 y 16–19/11. El 17/11 un hub USB cortó el enlace; se resolvió conectando el adaptador directo a la laptop. | confirmado | `evidencias/g1a_enlace_2026-10-29.json`; `salidas/prueba_comunicacion/comunicacion_20261103_204309_644590Z.csv`; `docs/bitacora/2026-11-16_primer_movimiento_real.md` | por asignar | Releer enlace y ruta al inicio de cada visita (`./iniciar.sh enlace --ping`). |
| 7 | PC disponible y sistema operativo | Linux Ubuntu 26.04.1 LTS, kernel `7.0.0-38-generic`, Python 3.14.4. Inventario del 20/10 y captura del 29/10. | confirmado (histórico, reinventariar si cambia) | `model_manifest.yaml` (`operating_system`); `evidencias/inventario_pc_2026-10-20.json`; `g1_rws_2026-10-29_sanitizado.json` (`local_inventory`) | por asignar | Actualizar el inventario si se cambia de máquina. |
| 8 | ROS distro (ROS 1 o ROS 2) | ROS 2 Jazzy (`/opt/ros/jazzy`). Usado en la prueba RWS→ROS→TF del 03/11 y en el panel de RViz de 17–19/11. | confirmado | `model_manifest.yaml` (`ros_distribution`); `evidencias/verificacion_rws_ros_tf_2026-11-03.json` | por asignar | Ninguna; anotar la versión exacta de los paquetes en cada manifiesto de experimento. |
| 9 | Driver candidato, versión / commit | `PickNikRobotics/abb_ros2`, rama `rolling`, commit `e6486f7409073cdb2a10d6878bb50191dd50172b`: **solo auditado documentalmente, no compilado ni usado**. En la práctica el proyecto usa clientes propios (`irb120_conexion` para lectura RWS, `irb120_control` para órdenes) y no adopta `abb_ros2`. | pendiente (`abb_ros2`) · confirmado (código propio, commit del repositorio) | `model_manifest.yaml` (`driver_candidate`); `docs/conexion_abb/README.md`; `docs/conexion_abb/fuentes/origenes.json` | por asignar | Si se quiere probar EGM: confirmar con el docente cuál es el repositorio de clase, fijar dependencias y compilar sin hardware. |
| 10 | Requisitos / versiones documentados | `abb_libegm` exige RobotWare ≥ 6.07.01 dentro de RW6 y la opción 689-1; el RW local (6.12.01.00) cumple ese mínimo **en el papel**. `abb_ros2` prueba Rolling en CI, no Jazzy; su ejemplo es IRB 1200, no IRB 120. | confirmado como requisito documental · pendiente como compatibilidad local | `docs/conexion_abb/fuentes/abb_libegm_README.md`; `docs/conexion_abb/fuentes/abb_ros2_setup.md`; `docs/conexion_abb/fuentes/abb_ros2_ci.yaml` | por asignar | No declarar compatibilidad completa sin prueba EGM. |
| 11 | Red / control de acceso institucional | Red punto a punto PC–puerto de servicio, sin conexión a la red de la universidad. Acceso RWS con una cuenta UAS (nombre de cuenta `Default User`); la contraseña se pide por `getpass` y no se guarda en ningún archivo del repositorio. No consta registro institucional de autorización de acceso. | confirmado (acceso técnico) · pendiente (autorización institucional documentada) | `docs/conexion_abb/COMO_FUNCIONA.md` (§8); `evidencias/g1a_enlace_2026-10-29.json` | por asignar | Pedir al laboratorio un registro de la autorización de acceso. |
| 12 | Manual / control de seguridad local | Se descargó el checklist docente. El procedimiento local del laboratorio (zona de exclusión, secuencia de E-stop, protocolo escrito) **no consta** en el repositorio. Se cita el manual ABB IRC5/FlexPendant (apartados 3.2.5 y 5.8.5) en el cierre del 10/11. | pendiente | `material_docente/actualizacion_semana_12/w12_s01_checklist_seguridad.pdf`; `docs/conexion_abb/CIERRE_PRUEBA_J6_2026-11-10.md` | por asignar | Obtener del laboratorio el procedimiento escrito y el manual de la versión; adjuntarlos a `hito3/docs/checklist_seguridad.md`. |
| 13 | URDF / SRDF / otros modelos y versión | URDF `hito2/datos/irb120.urdf` y DH `hito2/irb120/dh.py`, en el commit `19639122be7aeb98a6e96b8aea44530f94885c31`. TCP del modelo 0,150 m (convención, **no medido**; antes 0,100 m en ROS). No hay SRDF en el repositorio. Independencia geométrica del URDF respecto al DH: no verificada (`local_urdf_geometric_independence: false`). | confirmado (modelos y commit) · pendiente (TCP físico, SRDF) | `model_manifest.yaml`; `docs/conexion_abb/evidencias/fk_hito1_vs_rosi.csv` | por asignar | Leer el `tooldata` real por RWS; decidir si se necesita SRDF (MoveIt). |
| 14 | Código del ajedrez y modo real de operación | En el controlador existía `Module1/main` (RAPID con tabla `Squares`, objetivos `Target_*`, `A1…`), descrito en la bitácora como programa de ajedrez que abre un socket hacia la PC (puerto 5000) y mueve a `v200`; el 17/11 `Module1` apareció vacío y la versión anterior se respaldó. El código del lado PC/ROS de ese proyecto **no se ha localizado**. No se debe iniciar Start con el puntero en `main`. | pendiente (parcial) | `salidas/control_articular/rws_mover/respaldo_modulo_20261117_004843_058962Z/Module1.mod` (no versionado); `ros2_ws/src/irb120_control/rapid/respaldo_controlador/2026-11-16/`; `docs/bitacora/2026-11-16_primer_movimiento_real.md` | por asignar | Pedir al docente/laboratorio el antecedente completo; no atribuir ROS a ese proyecto sin ver su código. |
| 15 | Usuario / operador autorizado | Todas las sesiones con movimiento tuvieron un operador y un responsable según la bitácora, pero **sus nombres y la autorización por escrito no constan en el repositorio**. Para el 10/11 el manifiesto dice «autorización del responsable y del operador reportada por el usuario, solo para esa prueba». | pendiente | `model_manifest.yaml` (`rws_rapid_j6_trial.session_go`); `docs/bitacora/2026-11-16_primer_movimiento_real.md` | por asignar | Registrar nombre, cargo y fecha del operador/responsable de cada sesión; ver `checklist_seguridad.md`. |

Resumen: 8 ítems `confirmado` o confirmados con matiz (1, 3, 4, 5, 6, 7, 8, 13), 7 `pendiente` en lo que importa para la autorización (2, 9, 10, 11, 12, 14, 15). Ninguno `incompatible`.

## 2. Hipótesis de arquitectura

> Nomenclatura. En esta ficha **A = RWS + RAPID `LabJointRws`** (la ruta elegida y operativa) y **B = EGM** (`abb_ros2`/`abb_libegm`). La plantilla oficial de la matriz A/B (W12-S02) nombra al revés: su «Ruta A» es el driver existente RWS/EGM y su «Ruta B» el puente propio con RAPID. El contenido es el mismo; solo cambian las letras. Ver `matriz_ab_gate1.md`.

### Hipótesis A · RWS + RAPID (`LabJointRws`)

- **Descripción.** La PC Linux (ROS 2 Jazzy, Python) habla con el IRC5 por RWS 1.0 (HTTP Digest). Escribe las variables PERS `pcTarget`, `pcSeq` (y en la v5 `pcPose`, `pcTipo`) y las lee de vuelta; el servidor RAPID `ServidorPC` valida límites y paso y ejecuta `MoveAbsJ` (en la v5 también `MoveL`), devolviendo `rbCodigo` y `rbSeq`. Una orden a la vez, con parada `fine`. No es control en tiempo real.
- **Fuente documental.** Documentación ABB de Robot Web Services, README de `abb_librws` (`docs/conexion_abb/fuentes/abb_librws_README.md`), `docs/conexion_abb/COMO_FUNCIONA.md`, `docs/conexion_abb/MOVER_DESDE_PC.md`.
- **Evidencia local.** Lectura RWS del 29/10 (S1), ROS/TF del 03/11 (S2), 24 órdenes con llegada el 16/11 y 265 órdenes registradas el 16–19/11 (S3 técnico, ver `evidencia_gate3_movimiento.md`).
- **Requisito crítico no verificado.** (i) Autorización GO firmada por el responsable del laboratorio para cada sesión (no consta en archivo); (ii) el módulo v5 (`pcTipo`, `MoveL`, `maxPasoDeg` 360°) **no se ha probado en el IRC5**, y su sintaxis no se compiló sin el controlador; (iii) el comportamiento ante fallos (pérdida de enlace, 403 tras detener RAPID) solo se observó parcialmente.

### Hipótesis B · EGM (`abb_ros2` + `abb_libegm`)

- **Descripción.** Control continuo con `ros2_control` sobre EGM (UDP/Protobuf, ciclo de 4 ms) más RWS para configuración, usando la opción 689-1.
- **Fuente documental.** `docs/conexion_abb/fuentes/abb_libegm_README.md`, `abb_ros2_README.md`, `abb_ros2_setup.md`; revisión `e6486f7409073cdb2a10d6878bb50191dd50172b` de `rolling`; adaptación comunitaria `hylander2126/irb120_ros2` (commit `d8673de4cbbba168e2c9b97fa8681c6a1bdcf717`).
- **Requisito crítico no verificado.** Configuración EGM en el controlador (dispositivo UDP, perfil de EGM y señales) y un intercambio EGM real con el robot. La opción está en la lista y la versión cumple el mínimo documental, pero **ninguna sesión EGM física se ha realizado**; `abb_ros2` no está compilado localmente para Jazzy/IRB 120. El prototipo `irb120_control` solo se probó con UDP simulado (`model_manifest.yaml`: `physical_motion_tested: false`).

## 3. Decisión actual del equipo

Marcar lo que corresponda cuando el equipo lo confirme; el estado propuesto por el repositorio es:

- [x] Investigar A (RWS + RAPID): ruta en uso desde el 16/11.
- [ ] Investigar B (EGM): no iniciado en hardware; opción futura si el docente la exige.
- [ ] Bloqueado
- [ ] Pendiente de acceso supervisado: aplica a cada sesión de laboratorio mientras no haya GO firmado (`checklist_seguridad.md`).

Decisión registrada por: por completar por el equipo. Fecha: por completar.

## 4. Dato de mayor poder discriminante (ficha W12-S02)

El dato que descartó o admitió la ruta fue la lectura autenticada de `/rw/system` y de las opciones por RWS: RobotWare 6.12.01.00 con las opciones 616-1, 623-1 y 689-1. Autoridad que lo dio: el propio controlador por RWS 1.0, con la cuenta UAS que dio el operador. Para EGM el dato discriminante que sigue pendiente es la configuración EGM del controlador, que la da el operador/docente.

## 5. Errores frecuentes (autocontrol)

- [x] Ningún dato se rotuló `incompatible` por desconocimiento.
- [x] No se asumió comunicación real por compilar un paquete: el enlace se probó con `ping`, RWS y lecturas.
- [x] No se atribuyó ROS al proyecto de ajedrez sin ver su código (ítem 14 pendiente).
- [x] Las opciones provienen de lectura RWS y foto, no de un manual genérico.
