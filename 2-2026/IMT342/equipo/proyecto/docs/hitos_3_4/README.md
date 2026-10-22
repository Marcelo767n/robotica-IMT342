# Hitos 3 y 4 integrados · ECI-3/4

Prioridad: demostrar comunicación y lectura real del ABB IRB 120 de forma reproducible. La semana 12 se centra en investigación e inventario Gate 0. La nueva fecha exacta del Hito 2 no se ha confirmado en estos documentos.

## Documentos de trabajo

- [Investigación y procedimiento de conexión](../conexion_abb/README.md).
- [Plan semanal, hipótesis, rúbrica y pruebas](../conexion_abb/plan_semana_12.md).
- [Inventario Gate 0](../conexion_abb/gate0_inventario.csv).
- [Manifiesto](../../model_manifest.yaml) y [fotos](../../fotos/README.md).
- [Casos Gate 2 predefinidos](../conexion_abb/validation_cases.csv).
- [Material original W12-S01](<../../archivos que hay que presentar/actualizacion_semana_12/>).

## Estado de los gates

| Gate | Evidencia disponible | Pendiente |
|---|---|---|
| G0 · inventario | Robot, EGM/PC Interface/Multitasking y red de servicio fotografiados | RobotWare completo, revisión del controlador, operador/protocolo y compatibilidad del driver |
| G1 · lectura | Diagnóstico GET y pruebas offline documentadas | Cable/adaptador, ruta Ethernet, cuenta UAS y comparación con FlexPendant |
| G2 · modelos | FK/IK/J propios y tres casos numéricos preparados | Referencia independiente, base/TCP común, unidades y comparación reproducible |
| G3 · movimiento | Sin evidencia de ejecución desde el proyecto | G1/G2 y autorización expresa GO del laboratorio |
| G4 · tarea | Sin implementación demostrada | Tablero repetible después de G3; visión opcional |

La presencia de EGM confirma esa opción instalada. No confirma que la versión del protocolo sea compatible ni que se haya establecido una sesión.
