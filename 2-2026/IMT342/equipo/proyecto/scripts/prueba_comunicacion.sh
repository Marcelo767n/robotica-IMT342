#!/usr/bin/env bash
# Arranque de la prueba de comunicación con el entorno disponible en esta PC.
set -eo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
py="${ROS_PY312:-$HOME/ros_py312/bin/python}"
if [[ ! -x "$py" || ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "Falta Python 3.12 ($py) o /opt/ros/jazzy/setup.bash."
  exit 2
fi
source /opt/ros/jazzy/setup.bash
set -u
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec "$py" "$here/prueba_comunicacion.py" "$@"
