#!/usr/bin/env bash
# Entrada única para los nodos físicos, sin depender de colcon/ros2 launch.
set -eo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
py="${ROS_PY312:-$HOME/ros_py312/bin/python}"
mode="${1:-ayuda}"
case "$mode" in
  comunicacion) module="irb120_conexion.arranque.comunicacion" ;;
  validar_fk) module="irb120_conexion.arranque.validacion_fk" ;;
  enlace) module="irb120_conexion.diagnostico.enlace" ;;
  rws_j6) module="irb120_control.rws_j6" ;;
  rws_mover) module="irb120_control.rws_mover" ;;
  control_demo|control_vista|control_egm_lectura|control_robot) module="irb120_control.arranque" ;;
  *)
    echo 'Uso: ./iniciar.sh {enlace|comunicacion|validar_fk|rws_j6|rws_mover|control_demo|control_vista|control_egm_lectura|control_robot} [opciones]'
    echo 'Lectura: ./iniciar.sh comunicacion --host 192.168.125.1 --user "Default User" --ignore-joint-state'
    echo 'Sin robot: ./iniciar.sh control_demo'
    echo 'Mover desde la PC: ./iniciar.sh rws_mover estado | instalar | interactivo | mover j6 +5 | terminar'
    exit 2 ;;
esac
shift
if [[ "$mode" == rws_* ]]; then
  # Las herramientas RWS solo necesitan Python 3 y requests; no dependen de ROS.
  [[ -x "$py" ]] || py=python3
  export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
  exec "$py" -m "$module" "$@"
fi
if [[ ! -x "$py" || ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "Falta el entorno Python 3.12 ($py) o ROS 2 Jazzy."
  exit 2
fi
source /opt/ros/jazzy/setup.bash
set -u
export PYTHONPATH="$here/src/irb120_control:$here/src/irb120_conexion${PYTHONPATH:+:$PYTHONPATH}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
if [[ "$mode" == control_* ]]; then
  mkdir -p "$here/../salidas/control_articular/ros_logs"
  export ROS_LOG_DIR="$here/../salidas/control_articular/ros_logs"
  exec "$py" -m "$module" --modo "${mode#control_}" "$@"
fi
exec "$py" -m "$module" "$@"
