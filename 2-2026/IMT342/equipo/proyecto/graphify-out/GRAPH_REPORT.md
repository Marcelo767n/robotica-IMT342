# Graph Report - proyecto  (2026-10-22)

## Corpus Check
- Large corpus: 221 files · ~635,047 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 1171 nodes · 2118 edges · 74 communities (53 shown, 21 thin omitted)
- Extraction: 93% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 137 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Jacobiano y dinamica 1R (hito2)
- Documentacion y versiones Hito 2
- Dinamica Lagrangiana (ros2_ws)
- API RWS de ABB y driver
- Generador de deck y manual
- Diagnostico RWS offline y repos ABB
- Scripts de verificacion
- Verificacion con modelo ROS-Industrial
- Tabla DH y calibracion ABB
- Gate 3 y checklist de seguridad
- Chequeo de colisiones
- Pieper: codo y muneca
- Panel de deslizadores ROS 2
- IK Pieper en ros2_ws
- Ramas de IK y validacion FK
- Analisis de pose (CLI)
- Cinematica directa DH
- Constructor de manual corregido
- Hardware interface ABB ROS 2
- Errores de posicion e IK
- Guia Hito 1 y paquete irb120_hito1
- Transformadas y utilidades ROS
- Pruebas de lectura RWS
- Cadena URDF
- Singularidad y amplificacion
- Demo de movimiento interpolado
- Launch files ROS 2
- Validador FK en ROS 2
- Errores FK y nodos ROS
- Protocolo de validacion Gate
- LSPB y limites de velocidad
- Pruebas de 8 ramas
- Candidatos y reportes de pose
- Pruebas de singularidad
- Planificacion LSPB
- Proyecto final y homografia
- Seleccion de rama y LSPB
- Figuras LSPB y limites
- Clase LSPB
- Nodo IK de trayectoria
- Constructor de documento
- Calibracion y posturas de prueba
- Nodo de estados articulares
- Biseccion de tiempo LSPB
- Rubrica y modelo 1R
- Rubrica y defensa Hito 2
- Informe IEEE y Pieper
- Fotos del controlador
- Metodo de Pieper
- Pruebas LSPB
- Pruebas URDF vs DH
- Figuras de reduccion 1R
- Clase LSPB (ros2_ws)
- Empaquetado ROS 2
- LSPB y reduccion 1R
- Fotos del FlexPendant
- Ramas Pieper (figuras)
- Rubrica ECI
- Referencias de Pieper y IK
- Capturas RViz
- Script de chequeo del proyecto
- Driver ABB no verificado
- Referencias del proyecto
- Guia Hito 1 corregida
- Foto de etiqueta ABB
- Hipotesis IRC5 Compact

## God Nodes (most connected - your core abstractions)
1. `forward_kinematics_tcp()` - 26 edges
2. `geometric_jacobian()` - 23 edges
3. `analyze_pose()` - 23 edges
4. `forward_kinematics()` - 22 edges
5. `forward_kinematics()` - 21 edges
6. `inverse_kinematics()` - 19 edges
7. `fk_check()` - 18 edges
8. `enumerate_candidates()` - 16 edges
9. `plan_lspb()` - 15 edges
10. `Explicacion de modulos Hito 2 vigente (hito2/explicacion/README.md)` - 15 edges

## Surprising Connections (you probably didn't know these)
- `ROS-Industrial abb_irb120_support (modelo cinematico oficial, rama kinetic-devel)` --conceptually_related_to--> `Repositorio ROS-Industrial abb (CAD IRB 120 para visual y collision de base_link, link_1 a link_5, tool0)`  [AMBIGUOUS]
  docs/hito2/informe_ieee/informe_hito2_ieee.pdf → ros2_ws/src/irb120_hito1/meshes/NOTICE.md
- `gripper_link.stl parametrico propio (provisional hasta CAD SMC MHZ2-16D)` --conceptually_related_to--> `Pinza paralela modular y tcp_link provisional a 0.160 m desde tool0`  [INFERRED]
  ros2_ws/src/irb120_hito1/meshes/NOTICE.md → archivo/hito1/entregables_anteriores/Guia_Practica_Hito1_ROS2_ABB_IRB120.pdf
- `Quasi-physical modeling of robot IRB 120 using Simscape Multibody (TUBITAK 2020)` --semantically_similar_to--> `Metodo de Pieper (cinematica inversa analitica en Python, sin MoveIt)`  [AMBIGUOUS] [semantically similar]
  referencias/bibliografia/Quasi-physical_modeling_of_robot_IRB_120_using_Sim.pdf → referencias/bibliografia/Guia_PFI.pdf
- `Foto: panel interno del controlador IRC5 (X1 POWER, X2 service, LAN, panel unit, LEDs)` --conceptually_related_to--> `BOM autorizado: ABB IRB 120 (580 mm, 3 kg), IRC5, pinza neumatica, camara USB, Ubuntu 24.04, ROS, RobotStudio/RAPID`  [INFERRED]
  fotos/conexiones/850268306_1832902787824998_2294950866819187083_n.jpg → referencias/bibliografia/Guia_PFI.pdf
- `Foto: conector XP1 (etiqueta 3HAC032694-001) y puertos XS4, XS41, XS2 del IRC5` --conceptually_related_to--> `BOM autorizado: ABB IRB 120 (580 mm, 3 kg), IRC5, pinza neumatica, camara USB, Ubuntu 24.04, ROS, RobotStudio/RAPID`  [INFERRED]
  fotos/conexiones/855874124_2306012606912321_7497770149197177994_n.jpg → referencias/bibliografia/Guia_PFI.pdf

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Familia de drivers ABB para ROS (RAPID, EGM, RWS)** — docs_conexion_abb_fuentes_abb_driver_readme, docs_conexion_abb_fuentes_abb_libegm_readme, docs_conexion_abb_fuentes_abb_librws_readme, docs_conexion_abb_fuentes_abb_robot_driver_readme [INFERRED 0.75]
- **Pipeline Hito 2 anterior: Pieper, LSPB y singularidad q5** — archivo_hito2_ros_anterior_documentacion_metodo_y_resultados_pieper, archivo_hito2_ros_anterior_documentacion_metodo_y_resultados_lspb, archivo_hito2_ros_anterior_documentacion_metodo_y_resultados_singularidad_q5, archivo_hito2_ros_anterior_documentacion_guia_hito2_ik_trajectory_node, archivo_hito2_ros_anterior_documentacion_guia_hito2_dinamica [INFERRED 0.85]
- **Configuracion de red del controlador ABB para RWS y EGM** — docs_conexion_abb_fuentes_abb_ros2_networkingconfiguration_vcconf_whitelist, docs_conexion_abb_fuentes_abb_ros2_networkingconfiguration_ssh_port_forward, docs_conexion_abb_readme_red_servicio_192_168_125_1, docs_conexion_abb_fuentes_irb120_jazzy_readme_red_robot_192_168_125_208 [INFERRED 0.85]
- **G1 read-only verification path (GET only, no motion)** — docs_conexion_abb_fuentes_rws_ctrlstate, docs_conexion_abb_fuentes_rws_system, docs_conexion_abb_fuentes_rws_jointtarget, docs_conexion_abb_plan_semana_12_g1_read_test [INFERRED 0.75]
- **DH to URDF consistency chain (Hito 1 model reused in Hito 2 review)** — docs_hito1_modelo_cinematico_dh_to_urdf, docs_hito1_modelo_cinematico_error_criterion, docs_hito1_resultados, docs_hito2_verificacion_correcciones_hito2_2026_10_20_urdf_not_independent [INFERRED 0.75]
- **Hito 2 minimal delivery set** — docs_hito2_evaluacion_hito2_2026_10_20_packaging, docs_hito2_verificacion_correcciones_hito2_2026_10_20_datos_urdf, docs_hito2_informe_ieee_readme, docs_hito2_revision_2026_10_20_correcciones_notebook_verificado [INFERRED 0.75]
- **Pipeline Hito 2 (A a E)** — hito2_explicacion_01_modelo_dh_y_fk_forward_kinematics, hito2_explicacion_02_a_pieper_pieper_method, hito2_explicacion_04_c_lspb_lspb, hito2_explicacion_05_d_jacobiano_geometric_jacobian, hito2_explicacion_07_e_dinamica_1r_one_r_model [INFERRED 0.85]
- **Cascada de la singularidad de muneca** — hito2_explicacion_06_d_singularidades_wrist_singularity, hito2_explicacion_06_d_singularidades_rank_svd, hito2_explicacion_06_d_singularidades_velocity_amplification, hito2_explicacion_06_d_singularidades_null_joint_motion, hito2_explicacion_06_d_singularidades_no_infinite_torque [INFERRED 0.85]
- **Cadena de validacion por FK** — hito2_explicacion_01_modelo_dh_y_fk_forward_kinematics, hito2_explicacion_02_a_pieper_admissible_branch, hito2_explicacion_03_b_validacion_fk_acceptance_tolerance, hito2_explicacion_03_b_validacion_fk_round_trip, hito2_explicacion_03_b_validacion_fk_ros_industrial_check [INFERRED 0.85]
- **Pipeline del Hito 2: Pieper, LSPB, Jacobiano y dinamica 1R** — archivos_que_hay_que_presentar_hito_2_hito_2_guia_pipeline, archivos_que_hay_que_presentar_hito_2_hito_2_guia_pieper, archivos_que_hay_que_presentar_hito_2_hito_2_guia_lspb, archivos_que_hay_que_presentar_hito_2_hito_2_guia_jacobiano, archivos_que_hay_que_presentar_hito_2_hito_2_guia_dinamica_1r [EXTRACTED 1.00]
- **Singularidad frente a pico de torque** — docs_hito2_informe_ieee_informe_hito2_ieee_singularidad_muneca, docs_hito2_informe_ieee_informe_hito2_ieee_tau_estatico, docs_hito2_informe_ieee_informe_hito2_ieee_pico_torque, archivos_que_hay_que_presentar_hito_2_hito_2_slides_velocidad_no_torque_cero [INFERRED 0.85]
- **Gates y evidencia de ECI-3/4 (Hito 3)** — archivos_que_hay_que_presentar_actualizacion_semana_12_w12_s01_checklist_seguridad_estado_nogo, archivos_que_hay_que_presentar_actualizacion_semana_12_w12_s01_gate0_ficha_regla_epistemica, archivos_que_hay_que_presentar_actualizacion_semana_12_w12_s01_guia_autonoma_bitacora_calendario_gates, archivos_que_hay_que_presentar_actualizacion_semana_12_w12_s01_slides_escalera_gates, archivos_que_hay_que_presentar_actualizacion_semana_12_w12_s01_rubrica_hito_3_formula_ec_nf [INFERRED 0.75]
- **Flujo de la celda: camara -> Pieper -> LSPB -> IRC5** — referencias_bibliografia_guia_pfi_pipeline_architecture, referencias_bibliografia_guia_pfi_pieper_method, referencias_bibliografia_guia_pfi_dlt_svd_homography, hito2_figuras_d_twist_trayectoria_lspb_profile, referencias_bibliografia_guia_pfi_irb120_bom [EXTRACTED 1.00]
- **Validacion de la reduccion 1R del hombro** — hito2_figuras_e_1r_vs_completo, hito2_figuras_e_1r_vs_completo_1r_reduction, hito2_figuras_e_efecto_velocidad, hito2_figuras_e_efecto_velocidad_inertia_vs_gravity, hito2_figuras_e_torque_1r [INFERRED 0.85]
- **Singularidad de muneca y amplificacion de velocidad** — hito2_figuras_d_amplificacion, hito2_figuras_d_amplificacion_velocity_amplification, hito2_figuras_d_singularidad_rango, hito2_figuras_d_singularidad_rango_wrist_singularity, hito2_figuras_d_twist_trayectoria [INFERRED 0.85]
- **Pieper 8-branch inverse kinematics analysis** — hito2_figuras_a_conteo_ramas_branch_count, hito2_figuras_a_ocho_ramas_3d_eight_branches, hito2_figuras_a_ramas_brazo_arm_branches, hito2_figuras_b_errores_fk_fk_error [INFERRED 0.85]
- **1R reduction validation on LSPB trajectory** — hito2_figuras_e_1r_vs_completo_1r_validity, hito2_figuras_e_torque_1r_shoulder_torque, hito2_figuras_e_efecto_velocidad_speed_effect [INFERRED 0.85]

## Communities (74 total, 21 thin omitted)

### Community 0 - "Jacobiano y dinamica 1R (hito2)"
Cohesion: 0.05
Nodes (34): Jacobiano geometrico 6x6 (columna = [z x (p-o); z]), Validacion del Jacobiano por diferencias finitas, Twist [v; omega] del TCP, Parametros CAD de Truc y Lam (2020), Pinza SMC MHZ2-16D (0.115 kg) fusionada con eslabon 6, shoulder_model(), cartesian_demand(), _com_jacobians() (+26 more)

### Community 1 - "Documentacion y versiones Hito 2"
Cohesion: 0.07
Nodes (48): Versiones anteriores Hito 1 (README), Guia del Hito 2 (obsoleta, TCP 0.100 m), Autocolision con meshes CAD (CollisionChecker), Dinamica Lagrangiana (dynamics.py, M q, c, g, torques), Nodo ik_trajectory_node (ROS 2, PoseStamped a LSPB), Pinza SMC MHZ2-16D (115 g) fusionada con eslabon 6, Metodo y resultados Hito 2 anterior, Perfil LSPB sincronizado entre juntas (+40 more)

### Community 2 - "Dinamica Lagrangiana (ros2_ws)"
Cohesion: 0.08
Nodes (23): cartesian_demand(), _com_jacobians(), coriolis_vector(), _diag(), gravity_vector(), inverse_dynamics(), LinkInertia, mass_matrix() (+15 more)

### Community 3 - "API RWS de ABB y driver"
Cohesion: 0.06
Nodes (45): Material publicado por el docente (README), RWS Get Controller State, Controller state values (init, motoron, motoroff, guardstop, emergencystop, sysfail), Robot Web Services Introduction, RWS API performance guideline (50 ms interval, max 20 requests per second), Digest authentication with ABBCX cookie session, RWS session and connection limits (70 sessions, 3 connections per session, 5 min inactivity), WebSocket subscriptions with priorities 0/1/2 (+37 more)

### Community 4 - "Generador de deck y manual"
Cohesion: 0.07
Nodes (29): addFooter(), addRect(), addText(), addTopBars(), baseSlide(), candidatePath, card(), FINAL_PPTX (+21 more)

### Community 5 - "Diagnostico RWS offline y repos ABB"
Cohesion: 0.07
Nodes (35): Salida de pruebas offline del diagnostico RWS (2026-10-20), 8 pruebas offline del diagnostico RWS de solo lectura, abb_driver (driver RAPID, ROS 1 Kinetic/Melodic), Driver RAPID: solo movimiento articular, sin IO ni cartesiano, abb_libegm (biblioteca C++ EGM), EGM incompatible con RobotWare menor a 6.07.01 y requiere opcion 689-1, StateMachine Add-In de RobotWare, abb_librws (biblioteca C++ RWS 1.0) (+27 more)

### Community 6 - "Scripts de verificacion"
Cohesion: 0.07
Nodes (14): local_inventory(), main(), probe(), read_resource(), robot_axes(), state_records(), walk(), main() (+6 more)

### Community 7 - "Verificacion con modelo ROS-Industrial"
Cohesion: 0.09
Nodes (15): Verificacion geometrica con modelo oficial ROS-Industrial, Verificacion de implementacion con URDF del Hito 1, _axis_rotation(), rosi_forward_kinematics(), _axis_angle(), chain_transform(), Joint, _joint_transform() (+7 more)

### Community 8 - "Tabla DH y calibracion ABB"
Cohesion: 0.09
Nodes (14): Matriz DH clasica Rz Tz Tx Rx, Tabla DH del IRB 120, Pose inicial de calibracion ABB (q=0), Limites y velocidades articulares del datasheet ABB, Error de orientacion con atan2 (distancia geodesica en SO3), Comprobacion de pose cero contra datasheet (0.374, 0, 0.630 m), Mapa de modulos del paquete irb120, dh_transform() (+6 more)

### Community 9 - "Gate 3 y checklist de seguridad"
Cohesion: 0.09
Nodes (26): Checklist operativo de seguridad y autorizacion (Gate 3), W12-S01, Niveles de prueba y evidencia (simulacion offline, conectividad sin movimiento, estado observado, movimiento supervisado), 11 puertas de seguridad previas a Gate 3 (E-stop, zona de exclusion, modo permitido, TCP, objetos), Registro de decision GO/NO-GO para una prueba especifica, Ficha Gate 0: inventario local y auditoria de compatibilidad ROS-ABB, Auditoria Gate 0 sin movimiento fisico (15 items: modelo, controlador, RobotWare, interfaz, ROS, driver), Hipotesis de arquitectura A y B con fuente y requisito critico no verificado, Guia de trabajo autonomo, actividades y bitacora (Hito 3) W12-S01 (+18 more)

### Community 10 - "Chequeo de colisiones"
Cohesion: 0.10
Nodes (7): CollisionChecker, default_package_dir(), _surface_points(), TestCollision, cylinder(), main(), write_stl()

### Community 11 - "Pieper: codo y muneca"
Cohesion: 0.12
Nodes (14): Euler ZYZ para la muneca (q4, q5, q6), Ley de cosenos para el codo (q3), Anillo de alcance 0.040 a 0.580 m, Centro de muneca W = p_tool0 - d6 z6, _arm_branches(), BranchDecision, enumerate_candidates(), _fit_to_limits() (+6 more)

### Community 12 - "Panel de deslizadores ROS 2"
Cohesion: 0.10
Nodes (7): main(), SliderCommandPublisher, SliderPanel, command_payload(), SliderSpec, test_command_payload_clamps_out_of_range_values(), test_command_payload_contains_exactly_six_joint_values()

### Community 13 - "IK Pieper en ros2_ws"
Cohesion: 0.14
Nodes (9): _arm_solutions(), _fit_to_limits(), IKSolution, inverse_kinematics(), inverse_kinematics_tcp(), _rotation_0_3(), _wrap_pi(), _wrist_solutions() (+1 more)

### Community 14 - "Ramas de IK y validacion FK"
Cohesion: 0.13
Nodes (10): Rama admisible = real + dentro de limites + verificada por FK, 8 ramas de IK (brazo x codo x muneca), Prueba de ida y vuelta FK-IK-FK (1000 configuraciones), Tabla de 8 ramas del ejemplo (rama 1 admisible), forward_kinematics_tcp(), fk_check(), FKCheck, round_trip_test() (+2 more)

### Community 15 - "Analisis de pose (CLI)"
Cohesion: 0.14
Nodes (10): main(), Validacion de entrada como pose rigida SE(3), select_solution(), assert_rigid_transform(), matrix_to_quaternion(), matrix_to_rpy_deg(), pose_from_xyz_rpy_deg(), pose_matrix() (+2 more)

### Community 16 - "Cinematica directa DH"
Cohesion: 0.13
Nodes (7): dh_transform(), DHParameter, forward_kinematics(), forward_kinematics_tcp(), _joint_vector(), tcp_transform(), TestDirectKinematics

### Community 17 - "Constructor de manual corregido"
Cohesion: 0.17
Nodes (8): bullet(), callout(), code_block(), P(), table(), draw_cover(), draw_later(), main()

### Community 18 - "Hardware interface ABB ROS 2"
Cohesion: 0.13
Nodes (6): ABBSystemHardware::export_command_interfaces(), ABBSystemHardware::export_state_interfaces(), ABBSystemHardware::on_activate(), ABBSystemHardware::on_init(), ABBSystemHardware::read(), ABBSystemHardware::write()

### Community 19 - "Errores de posicion e IK"
Cohesion: 0.18
Nodes (6): position_error_m(), IKSolution, inverse_kinematics(), inverse_kinematics_tcp(), tool0_from_tcp(), TestPieper

### Community 20 - "Guia Hito 1 y paquete irb120_hito1"
Cohesion: 0.16
Nodes (14): Guia practica Hito 1: ROS 2, URDF/Xacro y cinematica del ABB IRB 120, Parametros DH clasicos del IRB 120 (d1=0.290, a2=0.270, a3=0.070, d4=0.302, d6=0.072), Nodos ROS 2 del paquete irb120_hito1 (joint_state_source, robot_state_publisher, fk_validator, motion_demo), Pinza paralela modular y tcp_link provisional a 0.160 m desde tool0, ROS 2 Jazzy sobre Ubuntu 24.04, URDF y Xacro (modelo modular expandido a URDF), verify_model: prueba offline DH vs URDF (error 2.22e-16 m, 12 tests), Pose objetivo Td: TCP en (0.40, 0.10, 0.35) m con RPY (0, 180, 0) deg (+6 more)

### Community 21 - "Transformadas y utilidades ROS"
Cohesion: 0.19
Nodes (5): matrix_to_quaternion(), pose_matrix(), quaternion_to_matrix(), rpy_to_matrix(), main()

### Community 22 - "Pruebas de lectura RWS"
Cohesion: 0.18
Nodes (3): FakeSession, payload(), ReadOnlyDiagnosticTests

### Community 23 - "Cadena URDF"
Cohesion: 0.23
Nodes (7): _axis_angle(), chain_transform(), Joint, _joint_transform(), load_joints(), _rpy_rotation(), _vector()

### Community 24 - "Singularidad y amplificacion"
Cohesion: 0.16
Nodes (4): Amplificacion de velocidad 1/sigma_min, Torque gravitacional tau_g, Torque inercial tau_in, OneRModel

### Community 25 - "Demo de movimiento interpolado"
Cohesion: 0.16
Nodes (4): interpolate_demo(), main(), MotionDemo, TestMotionDemo

### Community 27 - "Validador FK en ROS 2"
Cohesion: 0.16
Nodes (3): ForwardKinematicsValidator, main(), _transform_to_matrix()

### Community 28 - "Errores FK y nodos ROS"
Cohesion: 0.22
Nodes (6): position_error_m(), rotation_error_rad(), default_urdf_path(), main(), ValidationPose, verify()

### Community 30 - "Protocolo de validacion Gate"
Cohesion: 0.20
Nodes (9): Protocolo de validacion cinematica Gate 2 (FK, IK y Jacobiano), Metricas Jacobiano: eJ (Frobenius), ev y verificacion por diferencias finitas centrales, Metricas FK: error de posicion ep y error angular eR por traza de Re, Validacion IK: cada rama se audita por FK y limites articulares (no exigir q_own = q_ref), Jacobiano geometrico y criterio de rango para singularidades, Modelo 1R del hombro (junta 2) con error RMS 4.5 por ciento frente al modelo de 6 GDL, Parametros CAD del 1R: m = 12.210 kg, lc = 0.2491 m, Ic = 0.4479 kg m2, J = 1.2053 kg m2, Pico de torque de -20.55 N m en la fase de frenado del LSPB (+1 more)

### Community 31 - "LSPB y limites de velocidad"
Cohesion: 0.21
Nodes (3): check_trajectory(), default_limits(), LspbCheck

### Community 32 - "Pruebas de 8 ramas"
Cohesion: 0.26
Nodes (3): analyze_pose(), TestEightBranches, TestInputAndSelection

### Community 34 - "Pruebas de singularidad"
Cohesion: 0.21
Nodes (3): TestWristSingularity, inertial(), with_q5()

### Community 35 - "Planificacion LSPB"
Cohesion: 0.20
Nodes (4): plan_lspb(), blend_time(), feasible(), TestLspb

### Community 36 - "Proyecto final y homografia"
Cohesion: 0.25
Nodes (8): Foto: panel trasero del IRC5 con llave, paro de emergencia y conectores XP1/XS1/XS4/XS2, Guia oficial del estudiante: Proyecto Final Integrador (PFI), KPI-2: tiempo de ciclo < 8 s por pieza, KPI-4: paro de emergencia < 15 ms (ISO 10218-1/2), KPI-1: error de posicionamiento final < 1.5 mm, KPI-3: > 90 % de clasificaciones correctas en 10 ejecuciones, Celda de Manufactura Flexible Inteligente: clasificacion y paletizado por vision sobre ABB IRB 120, Arquitectura de software: camara -> nodo OpenCV/ROS -> resolvedor Pieper -> LSPB -> driver ROS-Industrial -> IRC5

### Community 37 - "Seleccion de rama y LSPB"
Cohesion: 0.18
Nodes (8): Singularidad de muneca en IK (q5=0, solo q4+q6 determinado), LSPB (Linear Segment with Parabolic Blends), Perfil triangular para movimientos cortos, Columnas 4 y 6 identicas en q=0, Jacobiano triangular por bloques con referencia en la muneca, Movimiento articular nulo q4 = -q6, Tres singularidades del IRB 120 (muneca, codo, hombro), Singularidad de muneca q5=0 (rango 6 a 5)

### Community 38 - "Figuras LSPB y limites"
Cohesion: 0.24
Nodes (10): LSPB joint position, velocity and acceleration profiles, 3D motion of the arm from initial to target pose with TCP trajectory, C_uso_limites (uso de limites por junta), Uso de limites por junta (|Vi|/vmax, |ai|/amax <= 1), D_amplificacion (amplificacion de velocidad y torque cerca de singularidad), D_singularidad_rango (valores singulares y perdida de rango), Singular values and rank loss 6 to 5 at q5=0, Singularidad de muneca en q5=0 (rank J 6 -> 5, sigma6 cae) (+2 more)

### Community 41 - "Constructor de documento"
Cohesion: 0.27
Nodes (8): build_story(), bullet(), callout(), chapter(), code(), data_table(), heading(), p()

### Community 43 - "Calibracion y posturas de prueba"
Cohesion: 0.20
Nodes (10): Pose inicial de calibracion q=0 (todos los ejes en 0 deg), singular por q5=0, ROS-Industrial abb_irb120_support (modelo cinematico oficial, rama kinetic-devel), Validacion FK por rama: ep < 1e-6 m y eR < 1e-6 rad; errores del orden de 1e-16, Posturas de prueba A (trabajo, todas las juntas no nulas) y B (plegada cerca de la base), Validacion DH vs URDF: error de posicion 1.12e-16 m y orientacion 4.2e-16 rad, APROBADO, Figura: error FK por rama real (ep, eR de 1e-16 frente a tolerancia 1e-6), NOTICE de atribucion de meshes, Licencia Apache-2.0 (+2 more)

### Community 44 - "Nodo de estados articulares"
Cohesion: 0.27
Nodes (3): _degrees(), JointStateSource, main()

### Community 45 - "Biseccion de tiempo LSPB"
Cohesion: 0.27
Nodes (6): Biseccion del tiempo minimo tf factible, Flujo de datos del notebook (variables globales), plan_lspb(), blend_time(), feasible(), TestLspbChecks

### Community 47 - "Rubrica y modelo 1R"
Cohesion: 0.31
Nodes (8): Guia oficial y rubrica de evaluacion del Hito 2 (Unidad II), Modelo dinamico reducido 1R: tau = J q_doble_punto + m g lc sin q, Trayectoria LSPB: q, q_punto, q_doble_punto con tiempos de mezcla y condiciones de reposo, Cinematica inversa de Pieper: hasta 8 ramas, atan2, verificacion T(q) aprox Td, Pipeline de ingenieria Hito 2: Td, Pieper, q, LSPB, J(q), singularidades, dinamica 1R, tau(t), Plantilla IEEE del informe Hito 2, LSPB sincronizado de tiempo minimo; vmax = 0.25 del datasheet y amax = vmax/0.25 s como supuesto, Pipeline T0,Td -> Pieper -> q -> FK -> LSPB -> J(q) -> 1R -> tau(t)

### Community 48 - "Rubrica y defensa Hito 2"
Cohesion: 0.25
Nodes (6): Defensa individual y regla de desempeno individual minimo, Rubrica oficial de evaluacion Hito 2, Defensa individual G1 pipeline, G2 matematica, G3 validacion, G4 transferencia (5 por ciento cada una), Dimensiones A-F con pesos: IK/Pieper 15, FK 10, LSPB 15, Jacobiano 20, dinamica 15, integracion 5, Ponderacion: EC2 50 por ciento y Hito 2 50 por ciento; Hito 2 con 80 por ciento grupal y 20 por ciento defensa, Diapositivas del Hito 2 (Unidad II)

### Community 49 - "Informe IEEE y Pieper"
Cohesion: 0.28
Nodes (9): Informe IEEE del Hito 2: Integracion de modelos cinematicos, diferenciales y dinamicos del ABB IRB 120, Criterio de seleccion de 8 ramas a 1: admisible, sigma_min >= 0.01, margen 5 deg, ponderacion W, Pieper: 8 ramas (2x2x2), 8 reales y 1 admisible para la pose objetivo; rama 1 elegida, Pieper 1968: The kinematics of manipulators under computer control (Stanford), Siciliano et al. 2009: Robotics, Modelling, Planning and Control, Figura: conteo de ramas reales, en limites y admisibles por pose (P1 a P5), Figura: 8 ramas de Pieper en 3D para la pose objetivo (rama 1 elegida), Figura: ramas del brazo en el plano de W para pose inicial y objetivo (+1 more)

### Community 50 - "Fotos del controlador"
Cohesion: 0.22
Nodes (9): Foto: panel interno del controlador IRC5 (X1 POWER, X2 service, LAN, panel unit, LEDs), Foto: conector XP1 (etiqueta 3HAC032694-001) y puertos XS4, XS41, XS2 del IRC5, Foto: etiqueta de conector XP1 del controlador (3HAC032694-001, serie 963439), Foto: placa del IRB 120 (serie 120-101516, IRB 120-3/0.6, 3 kg) con tabla de resolver values por eje, Foto: regulador automatico de voltaje SVR-5000W (Omega Plus) junto al equipo, Foto: etiqueta del FlexPendant DSQC 679 (Art 3HAC028357-001, Rev 13), Foto: brazo ABB IRB 120 sobre mesa azul con FlexPendant, equipo de trabajo en el laboratorio, Foto: FlexPendant con pantalla Backup and Restore (modo Manual, Guard Stop, ROB_1) (+1 more)

### Community 51 - "Metodo de Pieper"
Cohesion: 0.25
Nodes (6): Metodo de Pieper: IK cerrada desacoplada, Muneca esferica (ejes 4-6 concurrentes), Modelo 1R de Euler-Lagrange (tau = J q'' + m g lc sin theta), Teorema de ejes paralelos (Steiner), Ejemplo resuelto a mano para T_d (0.40, 0.10, 0.35) m, Pipeline del Hito 2 en una frase (A a E)

### Community 54 - "Figuras de reduccion 1R"
Cohesion: 0.33
Nodes (4): E_1R_vs_completo (validez de la reduccion 1R), E_efecto_velocidad (inercia vs gravedad segun factor de velocidad), E_torque_1R (torque del hombro con modelo 1R sobre LSPB), Quasi-physical modeling of robot IRB 120 using Simscape Multibody (TUBITAK 2020)

### Community 57 - "LSPB y reduccion 1R"
Cohesion: 0.40
Nodes (6): LSPB (linear segments with parabolic blends) trajectory, Cartesian TCP velocity, angular rate and min singular value along LSPB, Validity of 1R reduction vs full 6-DOF torque, Inertia torque grows with velocity squared, gravity constant, 1R reduction model (single revolute joint on shoulder J2), Shoulder J2 torque with 1R model on LSPB trajectory (peak -20.55 N m)

### Community 59 - "Fotos del FlexPendant"
Cohesion: 0.40
Nodes (5): IRB 120 robot controller (ID 120-101516), FlexPendant WAN network screen (DHCP), FlexPendant Options list (RobotWare options), FlexPendant Installed systems screen, FlexPendant Service port screen (IP 192.168.125.1)

### Community 60 - "Ramas Pieper (figuras)"
Cohesion: 0.50
Nodes (5): Pieper branch classification by pose (real / in limits / admissible), 3D view of the 8 Pieper branches for target pose (branch 1 chosen), Pieper 8 inverse-kinematics branches, 2D arm branches for initial and target pose, Forward kinematics error per real branch

### Community 61 - "Rubrica ECI"
Cohesion: 0.67
Nodes (3): Rubrica propuesta del elemento integrado ECI-3/4 (Hito 3), Cinco dominios de evaluacion ECI-3/4 (20, 25, 25, 20 y 10 por ciento), Formulas EC = 0.25 E1 + 0.25 E2 + 0.50 ECI3/4 y NF = 0.50 EC + 0.50 EF

### Community 62 - "Referencias de Pieper y IK"
Cohesion: 0.67
Nodes (3): The Inverse Kinematics Evaluation of 6-DOF Robots in Cooperative Tasks (IJMERR 2023), Cinematica inversa con redes neuronales entrenadas con Levenberg-Marquardt (SimMechanics), Parametros de Denavit-Hartenberg para modelado cinematico

### Community 63 - "Capturas RViz"
Cohesion: 0.67
Nodes (3): Captura RViz: ABB IRB 120 + pinza con frames DH/TF (demo automatica), Captura RViz: IRB 120 + pinza en postura demo (brazo elevado), Hito 1: gemelo digital URDF y cinematica directa del IRB 120 en RViz

### Community 66 - "Referencias del proyecto"
Cohesion: 1.00
Nodes (3): Referencias y bibliografia del proyecto, Repositorio rama main (URL), Repositorio rama proyectoHito1 (URL)

## Ambiguous Edges - Review These
- `Repositorio ROS-Industrial abb (CAD IRB 120 para visual y collision de base_link, link_1 a link_5, tool0)` → `ROS-Industrial abb_irb120_support (modelo cinematico oficial, rama kinetic-devel)`  [AMBIGUOUS]
  docs/hito2/informe_ieee/informe_hito2_ieee.pdf · relation: conceptually_related_to
- `Pinza paralela modular y tcp_link provisional a 0.160 m desde tool0` → `TCP a 0.150 m de la brida sobre z6 (decision de diseno del equipo)`  [AMBIGUOUS]
  archivo/hito1/entregables_anteriores/Guia_Practica_Hito1_ROS2_ABB_IRB120.pdf · relation: conceptually_related_to
- `Pose inicial de calibracion q=0 (todos los ejes en 0 deg), singular por q5=0` → `Posturas de prueba A (trabajo, todas las juntas no nulas) y B (plegada cerca de la base)`  [AMBIGUOUS]
  docs/hito2/informe_ieee/informe_hito2_ieee.pdf · relation: conceptually_related_to
- `Metodo de Pieper (cinematica inversa analitica en Python, sin MoveIt)` → `Quasi-physical modeling of robot IRB 120 using Simscape Multibody (TUBITAK 2020)`  [AMBIGUOUS]
  referencias/bibliografia/Quasi-physical_modeling_of_robot_IRB_120_using_Sim.pdf · relation: semantically_similar_to

## Knowledge Gaps
- **113 isolated node(s):** `workspaceDir`, `TMP_DIR`, `FINAL_PPTX`, `pres`, `requirements` (+108 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 401 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Repositorio ROS-Industrial abb (CAD IRB 120 para visual y collision de base_link, link_1 a link_5, tool0)` and `ROS-Industrial abb_irb120_support (modelo cinematico oficial, rama kinetic-devel)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Pinza paralela modular y tcp_link provisional a 0.160 m desde tool0` and `TCP a 0.150 m de la brida sobre z6 (decision de diseno del equipo)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Pose inicial de calibracion q=0 (todos los ejes en 0 deg), singular por q5=0` and `Posturas de prueba A (trabajo, todas las juntas no nulas) y B (plegada cerca de la base)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Metodo de Pieper (cinematica inversa analitica en Python, sin MoveIt)` and `Quasi-physical modeling of robot IRB 120 using Simscape Multibody (TUBITAK 2020)`?**
  _Edge tagged AMBIGUOUS (relation: semantically_similar_to) - confidence is low._
- **Why does `README de la entrega Hito 2 (hito2/)` connect `Documentacion y versiones Hito 2` to `API RWS de ABB y driver`, `Verificacion con modelo ROS-Industrial`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `Material publicado por el docente (README)` connect `API RWS de ABB y driver` to `Documentacion y versiones Hito 2`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Why does `TCP a 0.150 m de la brida (decision de diseno)` connect `Documentacion y versiones Hito 2` to `Tabla DH y calibracion ABB`?**
  _High betweenness centrality (0.080) - this node is a cross-community bridge._