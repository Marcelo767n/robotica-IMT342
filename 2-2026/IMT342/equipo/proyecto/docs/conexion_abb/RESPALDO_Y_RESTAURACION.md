# Respaldo y restauración del programa del robot

Qué hacer si alguien borra o cambia el programa del IRB 120 en el FlexPendant, y cómo dejarlo como estaba.

## 1. Qué hay en el controlador

Tarea `T_ROB1` del IRC5 (`120-101516`, RobotWare 6.12.01.00), según la lectura por RWS del 16/11/2026:

| Módulo | De quién | Para qué | Copia en git |
|---|---|---|---|
| `LabJointRws` | Equipo | Servidor de objetivos `ServidorPC` (v2) que mueve el robot desde la PC | [rapid/rws_mover/LabJointRws.mod](../../ros2_ws/src/irb120_control/rapid/rws_mover/LabJointRws.mod) |
| `Module1` | Laboratorio | Programa principal (`main`, ajedrez por socket) | [respaldo_controlador/2026-11-16/Module1.mod](../../ros2_ws/src/irb120_control/rapid/respaldo_controlador/2026-11-16/Module1.mod) |
| `EGM_ROS` | Laboratorio / otro grupo | Apareció entre el 10/11 y el 16/11; contenido aún no copiado | Pendiente: `./brazo.sh respaldar` |
| `user`, `BASE`, `CalibData` | Sistema ABB | Datos de sistema y calibración | Solo en la copia completa del FlexPendant (§2.1) |

## 2. Hacer una copia

### 2.1 Copia completa del sistema (recomendada antes de cada sesión)

Guarda programas, configuración, calibración y RobotWare. Es la única que permite devolver el controlador entero a su estado.

1. Conectar una memoria USB (FAT32) al puerto USB del controlador o del FlexPendant.
2. **Menú ABB → Copia de seguridad y restauración → Copia de seguridad del sistema actual…**
3. En la ruta, pulsar **…** y elegir la memoria USB. Dejar el nombre propuesto (incluye la fecha).
4. Pulsar **Copia de seguridad** y esperar a que termine. No necesita cambiar de modo ni encender motores.

### 2.2 Copia de los módulos RAPID desde la PC (solo lectura)

```bash
cd ros2_ws && ./brazo.sh respaldar
```

Guarda cada módulo de `T_ROB1` en `ros2_ws/src/irb120_control/rapid/respaldo_controlador/<fecha>/` con su huella SHA-256 en `respaldo.json`. Solo hace GET por RWS: no pide permisos ni cambia nada en el robot. Después, añadir la carpeta a git (`git add`, `git commit`). Herramienta: [`respaldo.py`](../../ros2_ws/src/irb120_control/irb120_control/respaldo.py).

## 3. Restaurar

### 3.1 Volver a cargar `LabJointRws` (para mover el robot desde la PC)

**Si el módulo existe pero cambió** (o es una versión anterior): llave en **AUTO**, motores apagados, RAPID detenido.

```bash
cd ros2_ws && ./brazo.sh instalar
```

El instalador respalda el módulo anterior en `salidas/`, sustituye solo `LabJointRws`, lo vuelve a leer y comprueba la huella. Se niega si el módulo no es una versión conocida o si falta `LabJointRws` o `Module1`; en ese caso usar 3.2.

**Si el módulo se borró**, cargarlo por USB:

1. En la PC, copiar [`LabJointRws.mod`](../../ros2_ws/src/irb120_control/rapid/rws_mover/LabJointRws.mod) a la raíz de una memoria USB (FAT32).
2. Llave en **Manual**. **Menú ABB → Editor de programas → Módulos**.
3. Si aparece un `LabJointRws` viejo: seleccionarlo → **Archivo → Eliminar módulo…** → **Aceptar** (sin guardar).
4. **Archivo → Cargar módulo…** → aceptar el aviso de que se pierde el puntero → elegir la USB → `LabJointRws.mod` → **Aceptar**.
5. **Depurar → Comprobar programa**: debe decir que no hay errores.
6. En la PC: `./brazo.sh estado` debe mostrar `módulo servidor_v2`.

### 3.2 Volver a cargar el programa del laboratorio (`Module1`)

Mismo procedimiento por USB con [`Module1.mod`](../../ros2_ws/src/irb120_control/rapid/respaldo_controlador/2026-11-16/Module1.mod). Después: **Depurar → PP a Main** para dejar el robot como se encontró. No pulsar Start sin la supervisión del responsable: `main` abre un socket hacia la PC y mueve a `v200`.

### 3.3 Restaurar el sistema completo

Solo si se perdió más que los módulos (configuración, calibración) y con la copia del §2.1:

1. **Menú ABB → Copia de seguridad y restauración → Restaurar sistema…**
2. Elegir la carpeta de la copia en la USB → **Restaurar**. El controlador se reinicia solo.
3. Comprobar con `./brazo.sh estado` y la posición de calibración antes de mover.

## 4. Comprobación rápida después de restaurar

| Comprobación | Esperado |
|---|---|
| `./brazo.sh enlace` | Ping y puerto 80 abiertos |
| `./brazo.sh estado` | Controlador `120-101516`, RobotWare `6.12.01.00`, módulo `servidor_v2` |
| FlexPendant → Comprobar programa | Sin errores |
| `./brazo.sh simulado` | Sigue funcionando (no depende del robot) |
