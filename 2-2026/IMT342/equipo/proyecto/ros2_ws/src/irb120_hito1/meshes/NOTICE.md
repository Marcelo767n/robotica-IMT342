# Atribución de los meshes

Los STL de `visual/` y `collision/` de `base_link`, `link_1`…`link_5` y `tool0` derivan del
modelo CAD del ABB IRB 120 publicado por ROS-Industrial en
<https://github.com/ros-industrial/abb> (`abb_irb120_support/meshes/irb120_3_58`, rama
`noetic-devel`), bajo licencia **Apache-2.0**. Se re-expresaron en los marcos del URDF de
este proyecto con `scripts/import_cad.py` (rotación y traslación rígidas; la forma no cambia).

`gripper_link.stl` es un modelo paramétrico propio (`scripts/generate_meshes.py`) mientras no
se disponga del CAD de la pinza real.
