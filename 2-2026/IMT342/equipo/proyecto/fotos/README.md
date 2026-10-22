# Evidencias fotográficas del equipo ABB

Catálogo revisado el **20 de octubre de 2026**. Se conservan los 14 archivos originales y sus nombres. Las fotos registran el equipo y las pantallas en el momento de la captura; no prueban el estado actual del controlador ni una conexión desde Linux.

| Carpeta | Contenido |
| --- | --- |
| `equipo/` | Robot, FlexPendant, gabinete, etiquetas y regulador de tensión. |
| `flexpendant/` | Opciones instaladas, configuración de red y pantallas del sistema. |
| `conexiones/` | Vista de conectores y detalle del puerto de servicio. |

## Datos confirmados por lectura de las fotos

- Robot **ABB IRB 120**, variante **IRB 120-3/0.6**, serie **120-101516**, fabricación **2018-01-10**, carga nominal **3 kg** y masa **25 kg**.
- FlexPendant **DSQC 679**, artículo **3HAC028357-001**, revisión **13**. Esta etiqueta corresponde al mando, no al computador principal del controlador.
- Opciones visibles: **689-1 Externally Guided Motion (EGM)**, **623-1 Multitasking** y **616-1 PC Interface**.
- Puerto de servicio configurado como **192.168.125.1**, máscara **255.255.255.0**, puerta de enlace **None**.
- WAN muestra configuración **DHCP** y máscara **255.255.255.0**; sus campos de IP y puerta de enlace aparecen vacíos en la foto.
- En el interior aparece el conector **X2, Service 10/100**, libre en la captura. La foto identifica su etiqueta, pero no sustituye el procedimiento de acceso del laboratorio.
- Las pantallas muestran sistema **120-101516**, unidad **ROB_1**, modo **Manual**, **Guard Stop** y **Stopped (Speed 100%)**. Son observaciones de la captura; el indicador de velocidad no significa que el robot se estuviera moviendo.

## Catálogo de archivos

| Foto | Qué documenta y límites |
| --- | --- |
| [Placa del robot](equipo/856105511_972111242619279_1826443544156678714_n.jpg) | Modelo, variante, serie, fecha, carga y masa. La etiqueta contigua contiene valores de calibración de resolvers; no son posiciones articulares para ROS. |
| [Etiqueta del FlexPendant](equipo/856870076_1787827082468806_3733552213891417058_n.png) | DSQC 679, artículo 3HAC028357-001 y revisión 13. |
| [Gabinete completo](equipo/850210285_1128959306485660_255701484691959323_n.jpg) | Gabinete ABB, selector, paro y cables. Su aspecto es compatible con IRC5 Compact; falta una placa legible para confirmar modelo y revisión. |
| [Etiqueta de conector](equipo/854925899_1629430838719154_5971042423311787851_n.jpg) | Artículo 3HAC032694-001 y revisión 02 del componente fotografiado; no identifica el computador principal. |
| [Regulador de tensión](equipo/856545192_1630674768443060_1267442518116769094_n.jpg) | OMEGA plus SVR-5000W, AC Automatic Voltage Regulator. |
| [Vista general del robot](equipo/858065911_1079221618446596_3013400657671404708_n.jpg) | Brazo, mando y mesa; brida sin herramienta montada visible en esa captura. No determina el TCP configurado. |
| [Lateral del gabinete](equipo/851841999_1307619194764630_6695385760372191744_n.jpg) | Advertencias y lateral; la placa de identificación queda cortada y no permite confirmar modelo/revisión. |
| [Opciones instaladas](flexpendant/853082554_2593180977825989_6769481757691654016_n.jpg) | Lista legible con EGM 689-1, Multitasking 623-1 y PC Interface 616-1. No muestra la versión de RobotWare. |
| [Red del puerto de servicio](flexpendant/855960479_2029194091093971_8662650587010659671_n.jpg) | IP 192.168.125.1, máscara 255.255.255.0 y gateway None. |
| [Backup and Restore](flexpendant/850334948_3064085187271613_2972342787603937018_n.jpg) | Menú para crear/restaurar respaldos. No demuestra que exista un respaldo ni que se haya generado uno. |
| [Sistemas instalados](flexpendant/855156643_1021735353659224_8600621675227135592_n.jpg) | Sistema instalado 120-101516 y unidad ROB_1; no muestra versión de RobotWare. |
| [Configuración WAN](flexpendant/850871225_3669278733235500_3305222871120947565_n.jpg) | DHCP, máscara 255.255.255.0, campos IP/gateway vacíos en la imagen. |
| [Conexiones del gabinete](conexiones/855874124_2306012606912321_7497770149197177994_n.jpg) | Vista de cableado y conectores; el detalle de red se lee mejor en la siguiente foto. |
| [Detalle de puertos](conexiones/850268306_1832902787824998_2294950866819187083_n.jpg) | X2 Service 10/100 identificable y libre; también se ven etiquetas de LAN/WAN. No permite leer una etiqueta DSQC del computador. |

## Datos que siguen pendientes

El usuario reportó **RobotWare 6.12.01.00** por transcripción el 22/10/2026; esa versión no aparece en las fotos de este catálogo. El **modelo y revisión exactos del controlador**, el **DSQC del computador principal**, la existencia de un **respaldo recuperable**, el **TCP/base activos** y las **credenciales autorizadas de lectura** siguen sin verificarse. Las opciones presentes favorecen investigar RWS/EGM, pero la compatibilidad final del driver depende también de RobotWare y de su configuración.

Registro estructurado: [evidencia del controlador](../docs/conexion_abb/evidencias/controlador_fotos_2026-10-20.json). Guía de conexión: [documentación ABB](../docs/conexion_abb/README.md).
