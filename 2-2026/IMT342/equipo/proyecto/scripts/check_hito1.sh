#!/usr/bin/env bash
set -eo pipefail

project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
workspace_dir="${project_dir}/ros2_ws"

if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
fi

set -u

if ! command -v colcon >/dev/null 2>&1; then
  echo "Falta colcon. Instala: sudo apt install python3-colcon-common-extensions"
  exit 2
fi

cd "${workspace_dir}"
colcon build --symlink-install --packages-select irb120_hito1
# shellcheck disable=SC1091
set +u
source "${workspace_dir}/install/setup.bash"
set -u
colcon test --packages-select irb120_hito1 --event-handlers console_direct+
colcon test-result --verbose
ros2 run irb120_hito1 verify_model

xacro_source="${workspace_dir}/src/irb120_hito1/urdf/irb120_with_gripper.urdf.xacro"
xacro_output="/tmp/imt342_irb120_from_xacro.urdf"
xacro "${xacro_source}" -o "${xacro_output}"
ros2 run irb120_hito1 verify_model --urdf "${xacro_output}"
