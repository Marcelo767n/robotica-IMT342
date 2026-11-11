# irb120_conexion · nodos físicos de solo lectura

```text
irb120_conexion/
├── arranque/
│   ├── comunicacion.py            RWS + robot_state_publisher + RViz + monitor
│   └── validacion_fk.py           lo anterior + comparación FK/pose ABB
├── nodos/
│   ├── lectura_articular/
│   │   ├── puente_rws.py          consulta RWS y publica estados/muestras
│   │   └── escuchar.py            observador de JointState para diagnóstico
│   ├── monitor_comunicacion/
│   │   ├── monitor.py             recibe RWS, JointState y TF; guarda CSV
│   │   └── panel.html             panel de ángulos (puerto 8765)
│   └── validacion_fk/
│       ├── comparacion.py         FK propia, marcos, errores y criterios
│       ├── nodo.py                suscriptor, resultados y CSV/JSONL
│       └── panel.html             panel de pose/error (puerto 8766)
├── comunicacion/
│   ├── lectura_rws.py             cliente GET con lista de recursos permitidos
│   └── muestra_fk.py              adquisición q_antes → robtarget → q_después
├── modelo/preparar.py             recursos del gemelo, reutiliza Hito 1
├── diagnostico/enlace.py          adaptador, enlace, IP, ruta y ping opcional
└── rutas.py                       localización compartida de recursos
```

El árbol de arriba corresponde al subdirectorio Python `irb120_conexion/` dentro de este paquete. `package.xml`, `setup.py`, `setup.cfg` y `resource/` proporcionan la estructura `ament_python`. Las pruebas nuevas están en `test/`; las pruebas anteriores y de los comandos compatibles siguen en `../../../scripts/tests/`, relativas a la raíz del proyecto.

## Nodos y temas

| Nodo | Entradas | Salidas |
|---|---|---|
| `abb_rws_joint_bridge` | GET ABB `jointtarget`; opcionalmente `robtarget` y segunda lectura articular | `/irb120/real/joint_states`, `/rws` y `/fk_sample` como sufijos de ese tema |
| `robot_state_publisher` | JointState + URDF del Hito 1 | `/irb120/real/tf`, `/tf_static` y `/robot_description` bajo el mismo espacio |
| `irb120_monitor_comunicacion` | Estado RWS, JointState, TF | HTTP local 8765 y CSV |
| `irb120_validacion_fk` | `/irb120/real/joint_states/fk_sample` | Mismo tema con sufijo `/resultado`, HTTP local 8766 y CSV/JSONL |
| RViz | Descripción y TF del espacio `/irb120/real/` | Visualización |

El puente no tiene interfaces ROS de comando hacia el ABB. El nodo FK solo recibe las lecturas ya adquiridas; no guarda ni solicita credenciales. La FK se importa de `irb120_hito1.kinematics.dh`, sin copiar la matemática.

## Uso

Desde `proyecto/`:

```bash
bash ros2_ws/iniciar.sh validar_fk --host 192.168.125.1 --user "Default User" --ignore-joint-state
```

Frecuencia inicial FK: **5 Hz**; cada ciclo requiere tres GET secuenciales. La prueba de comunicación conserva 10 Hz por defecto y un GET por ciclo. Todos los procesos se cierran con Ctrl+C en la terminal.

El panel FK compara `tool0` en `Base`, con `wobj0`. No compara la pinza ni el TCP supuesto de 150 mm. Predeterminados estrictos, solicitados por el equipo: `--position-tol-mm 0.001 --orientation-tol-rad 1e-6`. Son configurables y no representan un límite oficial del docente ni exactitud física garantizada. En movimiento la comparación se marca no evaluable.

## Pruebas y alcance

```bash
python3 -m unittest discover -s scripts/tests -t scripts/tests
python3 -m unittest discover -s ros2_ws/src/irb120_conexion/test -t ros2_ws/src/irb120_conexion/test

# Prueba integrada opcional con ROS real y ABB simulado en loopback:
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=147 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST IRB120_RUN_ROS_TEST=1 \
  ~/ros_py312/bin/python -m unittest discover \
  -s ros2_ws/src/irb120_conexion/test -t ros2_ws/src/irb120_conexion/test -v
```

La prueba integrada usa geometría ROS-Industrial independiente para la pose del controlador simulado y comprueba tres estados: pose concordante, desplazamiento artificial de 0.02 mm y cambio articular entre lecturas. Verifica también GET exclusivamente y contexto Base/tool0/wobj0. No demuestra una nueva validación física ABB.

La estructura ament está preparada; no se afirma una compilación nueva con colcon en la instalación actual. El arranque fuente de `ros2_ws/iniciar.sh` es el camino comprobado en esta PC.
