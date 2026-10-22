# Preparación de la semana 12

Fecha: 2026-10-20. Actualizado con nuevas fotos del FlexPendant y de conexiones. Alcance actual: cerrar Gate 0 y preparar la lectura G1. Las fotos confirman opciones y red de servicio, pero no una conexión de Linux al controlador. La disponibilidad actual de cable/adaptador debe confirmarse. Este documento es un borrador del equipo, no una certificación del docente ni permiso para operar.

## Qué cambió respecto al Hito 2

La nueva documentación une III/IV en ECI-3/4. El modelo numérico del Hito 2 es una base para FK/IK/J, pero ahora se exige evidencia del sistema real, compatibilidad, integración, pruebas y defensa individual. No se asigna una nota nueva de integración porque todavía no hay evidencia de conexión física.

| Criterio de la rúbrica propuesta | Peso | Situación observada | Falta para acreditarlo |
|---|---:|---|---|
| Auditoría y compatibilidad | 20% | IRB120 y opciones EGM/PC Interface/Multitasking confirmados por fotos; servicio 192.168.125.1 y X2 Service identificados; candidatos documentados | RobotWare completo, placa/revisión del controlador y computador, permisos, configuración EGM/RWS y elección definitiva del driver |
| Modelos propios y validación | 25% | FK/IK/J existentes; casos numéricos disponibles | Referencia geométrica independiente, misma base/TCP/unidades, validación cruzada exigida |
| Integración ROS–ABB | 25% | Paquetes ROS de simulación y diagnóstico preparado | Lectura real registrada, puente/driver compilado y adaptado, control solo tras GO |
| Seguridad, reproducibilidad y fallos | 20% | Pruebas offline del diagnóstico y fuentes identificadas | Protocolo local, supervisor/operador, pruebas de fallos autorizadas y logs reales |
| Documentación y defensa individual | 10% | Investigación, manifiesto y borrador de bitácora | Responsables, aportes individuales, explicación de decisiones y defensa |

La rúbrica dice que sus pesos requieren formalización administrativa. Se mantiene ese carácter de propuesta. Fuente: `archivos que hay que presentar/actualizacion_semana_12/w12_s01_rubrica_hito_3.pdf`.

## Cinco hipótesis de compatibilidad

| Hipótesis | Fuente | Cómo verificarla | Qué impide concluir hoy |
|---|---|---|---|
| H1: el gabinete es IRC5 Compact | Fotos del gabinete, manual ABB correspondiente | Placa y System Info | Aspecto exterior no identifica revisión/computador |
| H2: permite lectura RWS 1.0 | Documentación ABB RWS y `abb_librws`; captura de servicio 192.168.125.1/24 | Versión RW, enlace, usuario; GET de identidad y articulaciones | RW y permisos desconocidos; enlace PC–ABB sin probar |
| H3: `abb_ros2`/EGM es viable | `abb_libegm`, driver auditado y foto Options con 689-1 EGM | RW6 ≥6.07.01, RAPID/configuración compatibles y driver adaptado | EGM está presente; versión completa de RW y configuración no verificadas |
| H4: se puede adaptar el soporte al IRB 120 | Modelo local y adaptación comunitaria IRB120/Jazzy | Compilar revisión fija, comprobar interfaces, geometría, juntas y TCP | Ejemplo upstream IRB1200; TCP local no coincide con ROS anterior; sin prueba de compilación |
| H5: RAPID/sockets es contingencia ante incompatibilidad EGM | Manuales de comunicación de la versión, `abb_driver`; fotos con 616-1 y 623-1 | Instrucciones de esa versión, módulos existentes y protocolo aceptado por docente | PC Interface y Multitasking presentes; RW, programa y backup real sin verificar; antecedente de ajedrez no encontrado |

Fuentes y requisitos ampliados en `README.md`. No verificado no significa ausente.

## Evidencia nueva que cambia la preparación

- **Opciones:** `fotos/flexpendant/853082554_2593180977825989_6769481757691654016_n.jpg` confirma 689-1 EGM, 616-1 PC Interface, 623-1 Multitasking y UDP UC Driver. Las demás opciones registradas están en `gate0_inventario.csv` y `model_manifest.yaml`.
- **Servicio:** `fotos/flexpendant/855960479_2029194091093971_8662650587010659671_n.jpg` muestra IP 192.168.125.1, máscara 255.255.255.0, gateway None. La etiqueta X2 Service 10/100 se identifica en `fotos/conexiones/850268306_1832902787824998_2294950866819187083_n.jpg`; corresponde verificar con el operador el acceso externo apropiado sin abrir ni alterar el gabinete.
- **WAN:** `fotos/flexpendant/850871225_3669278733235500_3305222871120947565_n.jpg` muestra DHCP con IP/gateway en blanco. Solo se registra que esos valores no son visibles.
- **Sistema y estado capturado:** el sistema instalado figura como 120-101516; las pantallas muestran ROB_1, Manual, Guard Stop y Stopped. Speed 100% es el indicador fotografiado, no una medición de velocidad articular. Estos datos describen el momento de captura y deben releerse antes de una prueba.
- **Backup:** la foto `fotos/flexpendant/850334948_3064085187271613_2972342787603937018_n.jpg` muestra el menú; no prueba una copia creada ni su fecha.

El dato que ahora decide la compatibilidad de versiones es **RobotWare completo**. Sigue pendiente junto con placa/revisión exacta del gabinete/computador, configuración EGM y permisos UAS. No hay evidencia nueva de ejecución de programas, conexión desde Linux ni autorización de movimiento.

## Dos pruebas Gate 1, ambas sin movimiento

**G1-A — enlace e identidad de red.** Requiere acceso supervisado, operador autorizado y confirmación del acceso externo al puerto de servicio identificado en foto. Medir: interfaz Ethernet, enlace, IP/máscara y ruta al controlador. La captura muestra 192.168.125.1/24; corroborar que siga vigente. Resultado esperado: destino por Ethernet directo y dirección confirmada en el equipo. Guardar inventario nuevo, captura de Network connections y condiciones de prueba; el inventario anterior de la PC solo es antecedente. Falla si la ruta usa Wi-Fi, la IP es supuesta o no se identifica el acceso; resolver antes de consultar RWS. Responsable y autorización: pendientes de asignación por equipo/laboratorio.

**G1-B — lectura y comparación de estado.** Tras G1-A, usar cuenta UAS autorizada y consulta RWS solo GET. Medir: RobotWare reportado, identidad, unidad mecánica, modo, estado de controlador y seis articulaciones. Comparar con FlexPendant al mismo tiempo, registrar grados, fecha y condición estacionaria. Repetir una captura estacionaria para comprobar consistencia temporal sin ordenar movimiento. Aceptación: respuestas válidas y valores concordantes dentro de resolución/tolerancia declarada **antes** de la prueba. El laboratorio debe acordar esa tolerancia; no está impuesta por este borrador. Identificar si el destino es físico o virtual. Un 401/403 se registra como permisos pendientes, no como comunicación completada.

No iniciar controladores de trayectoria, RAPID ni EGM para estas pruebas. La guía docente exige supervisión/protocolo incluso para conectar físicamente. Un GO de movimiento pertenece a G3 y no se deduce de G1.

## Casos Gate 2 preparados offline

`validation_cases.csv` propone dos configuraciones regulares y una cercana a singularidad de muñeca; no son órdenes para el robot. El Jacobiano local tiene rango 6 en las tres con umbral absoluto `1e-8`; en la tercera el menor valor singular disminuye a aproximadamente `2.61e-4`, frente a `8.66e-2` y `1.20e-1`. Cerca de singularidad no significa necesariamente rango perdido a un umbral dado. Evidencia: `evidencias/casos_offline.json`.

Las salidas de comparación con referencia y la aceptación se conservan vacías. Antes de ejecutarlas, fijar referencia, versión, base/TCP, signos/offsets, unidades y orden de juntas. No se han validado poses alcanzables libres de colisión del robot real ni sus límites configurados.

Métricas previstas: norma del error de posición en m; ángulo de `R_ref.T @ R_own` en rad con argumento acotado; Frobenius de diferencia de Jacobianos expresados en la misma base y punto; diferencia de twist para una misma velocidad articular. Verificar diferencias centrales con pasos `1e-4`, `1e-5`, `1e-6` rad. Definir tolerancias distintas para comparación numérica y medición física antes del ensayo. En IK validar pose y límites de cada solución, sin exigir igualdad entre ramas articulares. `J.T @ F` es torque externo por potencia virtual, no dinámica completa.

## Tres tareas verificables antes de W12-S02

| Tarea | Salida verificable | Dependencia | Principal / respaldo |
|---|---|---|---|
| Cerrar identificación del controlador | Versión completa de RW y placa/revisión; confirmar fecha de capturas y existencia/fecha de backup real; opciones y red ya registradas | Acceso supervisado al FlexPendant y operador; no necesita cable PC | Por asignar / por asignar |
| Selección documentada del driver | Confirmación del repositorio usado en clase; arquitectura A/B y revisión fija; plan de entorno ROS | RW completo y configuración para selección definitiva; opciones principales ya documentadas | Por asignar / por asignar |
| Preparación G1/G2 | Diagrama, protocolos de lectura, manifiesto y casos; cable/adaptador disponible para siguiente acceso | Equipo de laboratorio y autorización; resolver TCP para G2 | Por asignar / por asignar |

El antecedente de ajedrez debe solicitarse al docente/laboratorio: no apareció en el proyecto ni en el árbol docente consultado. No se afirma que no exista fuera de estas carpetas. Visión/webcam es opcional en la guía y no bloquea la primera conexión.

## Bitácora inicial

- **ID:** CON-2026-10-20-01.
- **Modo:** auditoría documental y local/offline.
- **Hipótesis:** el IRB120 puede integrarse con ROS 2 mediante RWS/EGM si su controlador cumple los requisitos.
- **Prueba inicial:** inspección de fotos de hardware, documentación W12, fuentes ABB y drivers; inventario de red local; ocho contratos de diagnóstico con respuestas simuladas.
- **Ampliación documental:** nuevas fotos del FlexPendant y de conexiones, sin consulta desde la PC al controlador.
- **Resultado observado:** manipulador identificado; gabinete IRC5 Compact solo inferido; EGM/PC Interface/Multitasking y demás opciones confirmadas; servicio 192.168.125.1/24 y etiqueta X2 Service 10/100 registrados; RobotWare completo pendiente. La red de la PC anterior se conserva como antecedente, no como estado actual; ocho pruebas offline ya registradas.
- **Estado funcional:** `partially_verified` para preparación; `not verified` para conexión física.
- **Evidencia:** fotos, `fuentes/origenes*.json`, inventario local y pruebas en `scripts/tests/`.
- **Limitaciones:** sin conexión PC–controlador verificada, sin driver compilado, sin programa RAPID/backup real comprobado del laboratorio, sin validación de TCP físico. Las fotos no indican RobotWare completo ni fecha/hora exacta del estado capturado.
- **Próxima acción:** leer versión completa de RobotWare y placa/revisión, confirmar repositorio del docente y preparar cable/adaptador para G1; responsables por asignar.
- **Revisión requerida:** docente/laboratorio para compatibilidad y acceso; GO específico antes de movimiento.

Para nuevas pruebas registrar hipótesis → prueba → resultado → interpretación → siguiente acción, con hora, responsables, software, condiciones y enlace de evidencia. No transformar este registro en una declaración de hardware funcional.
