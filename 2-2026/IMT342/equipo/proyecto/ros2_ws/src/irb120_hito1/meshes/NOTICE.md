# Atribución de los meshes

Los STL de `visual/` y `collision/` de `base_link`, `link_1`…`link_5` y `tool0` derivan del
modelo CAD del ABB IRB 120 publicado por ROS-Industrial en
<https://github.com/ros-industrial/abb> (`abb_irb120_support/meshes/irb120_3_58`, rama
`noetic-devel`), bajo licencia **Apache-2.0**. Se re-expresaron en los marcos del URDF de
este proyecto con `scripts/import_cad.py` (rotación y traslación rígidas; la forma no cambia).

`gripper_link.stl` es un modelo paramétrico propio (`scripts/generate_meshes.py`) mientras no
se disponga del CAD de la pinza real.

## Cómo reemplazar la pinza por el CAD de SMC (MHZ2-16D)

El sitio de SMC exige verificación anti-bots y una cuenta para descargar, por eso no se pudo
automatizar. Pasos: en <https://www.smcworld.com/cad3d> abrir la serie **MHZ2**, elegir
**MHZ2-16D**, descargar en formato **STL** y ejecutar

```bash
python3 scripts/import_gripper_cad.py MHZ2-16D.stl --scale 0.001 [--rpy-deg R P Y] [--offset X Y Z]
```

El script lo lleva al marco `tool0` (cara de montaje en z = 0, dedos hacia +Z) y reemplaza
`visual/gripper_link.stl` y `collision/gripper_link.stl`. Si el centro de agarre cambia,
ajustar solo `tool0_to_tcp_z_m` en `config/tcp.yaml` (fuente única que leen el xacro y
`kinematics/dh.py`), regenerar el URDF y correr `bash scripts/check_proyecto.sh`.
