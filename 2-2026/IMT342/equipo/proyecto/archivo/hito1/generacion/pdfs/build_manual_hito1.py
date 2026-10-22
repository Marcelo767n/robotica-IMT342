from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ros2_ws").is_dir())
OUTPUT = ROOT / "archivo/hito1/entregables_anteriores/Guia_Practica_Hito1_ROS2_ABB_IRB120.pdf"
SCREENSHOT = ROOT / "docs/hito1/assets/rviz_irb120_demo_automatica.png"

NAVY = colors.HexColor("#17212B")
ORANGE = colors.HexColor("#F06C00")
PALE_ORANGE = colors.HexColor("#FFF1E6")
TEAL = colors.HexColor("#087E8B")
GREEN = colors.HexColor("#15803D")
PALE_GREEN = colors.HexColor("#EAF7EE")
RED = colors.HexColor("#B42318")
PALE_RED = colors.HexColor("#FDECEC")
GRAY = colors.HexColor("#5B6573")
LIGHT = colors.HexColor("#F4F6F8")
LINE = colors.HexColor("#D7DDE4")
WHITE = colors.white


def register_fonts() -> None:
    base = Path("/usr/share/fonts/truetype/liberation")
    pdfmetrics.registerFont(TTFont("LiberationSans", base / "LiberationSans-Regular.ttf"))
    pdfmetrics.registerFont(TTFont("LiberationSans-Bold", base / "LiberationSans-Bold.ttf"))
    pdfmetrics.registerFont(TTFont("LiberationSans-Italic", base / "LiberationSans-Italic.ttf"))
    pdfmetrics.registerFont(TTFont("LiberationMono", base / "LiberationMono-Regular.ttf"))


register_fonts()
styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="BodyX",
        parent=styles["BodyText"],
        fontName="LiberationSans",
        fontSize=10.2,
        leading=14.4,
        textColor=NAVY,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallX",
        parent=styles["BodyX"],
        fontSize=8.6,
        leading=11.5,
        textColor=GRAY,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletX",
        parent=styles["BodyX"],
        leftIndent=14,
        firstLineIndent=-8,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="H1X",
        parent=styles["Heading1"],
        fontName="LiberationSans-Bold",
        fontSize=21,
        leading=25,
        textColor=NAVY,
        spaceBefore=0,
        spaceAfter=10,
    )
)
styles.add(
    ParagraphStyle(
        name="H2X",
        parent=styles["Heading2"],
        fontName="LiberationSans-Bold",
        fontSize=13.5,
        leading=17,
        textColor=TEAL,
        spaceBefore=10,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="H3X",
        parent=styles["Heading3"],
        fontName="LiberationSans-Bold",
        fontSize=11,
        leading=14,
        textColor=NAVY,
        spaceBefore=7,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="CodeX",
        fontName="LiberationMono",
        fontSize=7.4,
        leading=9.6,
        textColor=colors.HexColor("#E6EDF3"),
        leftIndent=0,
        rightIndent=0,
        spaceBefore=0,
        spaceAfter=0,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName="LiberationSans-Bold",
        fontSize=30,
        leading=34,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        fontName="LiberationSans",
        fontSize=14,
        leading=20,
        textColor=colors.HexColor("#DDE5EC"),
    )
)
styles.add(
    ParagraphStyle(
        name="BigNumber",
        fontName="LiberationSans-Bold",
        fontSize=20,
        leading=22,
        textColor=GREEN,
        alignment=TA_CENTER,
    )
)


def p(text: str, style: str = "BodyX") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", styles["BulletX"])


def code(text: str) -> Table:
    content = Preformatted(text.strip("\n"), styles["CodeX"], maxLineLength=105)
    table = Table([[content]], colWidths=[16.7 * cm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#31404F")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    table.spaceBefore = 4
    table.spaceAfter = 8
    return table


def heading(title: str, number: str | None = None) -> list:
    if number is None:
        return [Paragraph(title, styles["H1X"]), Spacer(1, 2)]
    number_style = ParagraphStyle(
        name=f"SectionNumber{number}",
        parent=styles["H1X"],
        fontSize=15,
        leading=18,
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    title_style = ParagraphStyle(
        name=f"SectionTitle{number}",
        parent=styles["H1X"],
        fontSize=20,
        leading=23,
    )
    table = Table(
        [[Paragraph(number, number_style), Paragraph(title, title_style)]],
        colWidths=[1.15 * cm, 15.55 * cm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), ORANGE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (0, 0), 3),
                ("RIGHTPADDING", (0, 0), (0, 0), 3),
                ("TOPPADDING", (0, 0), (0, 0), 6),
                ("BOTTOMPADDING", (0, 0), (0, 0), 6),
                ("LEFTPADDING", (1, 0), (1, 0), 9),
                ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ("TOPPADDING", (1, 0), (1, 0), 0),
                ("BOTTOMPADDING", (1, 0), (1, 0), 0),
            ]
        )
    )
    return [table, Spacer(1, 8)]


def callout(title: str, text: str, tone: str = "info") -> Table:
    palette = {
        "info": (TEAL, colors.HexColor("#EAF7F8")),
        "ok": (GREEN, PALE_GREEN),
        "warn": (ORANGE, PALE_ORANGE),
        "danger": (RED, PALE_RED),
    }
    accent, fill = palette[tone]
    body = Paragraph(
        f'<font name="LiberationSans-Bold" color="{accent.hexval()}">{title}</font><br/>{text}',
        styles["BodyX"],
    )
    table = Table([["", body]], colWidths=[5, 16.7 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BACKGROUND", (0, 0), (0, 0), accent),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (1, 0), (1, 0), 10),
                ("RIGHTPADDING", (1, 0), (1, 0), 10),
                ("TOPPADDING", (1, 0), (1, 0), 8),
                ("BOTTOMPADDING", (1, 0), (1, 0), 8),
            ]
        )
    )
    return table


def data_table(rows, widths, header=True, font_size=8.5) -> Table:
    cooked = []
    for row_index, row in enumerate(rows):
        cooked.append(
            [
                Paragraph(
                    str(cell),
                    ParagraphStyle(
                        name=f"cell-{row_index}-{column_index}",
                        parent=styles["SmallX"],
                        fontName="LiberationSans-Bold" if header and row_index == 0 else "LiberationSans",
                        fontSize=font_size,
                        leading=font_size + 2.5,
                        textColor=WHITE if header and row_index == 0 else NAVY,
                    ),
                )
                for column_index, cell in enumerate(row)
            ]
        )
    table = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        commands.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    for index in range(1 if header else 0, len(rows)):
        if index % 2 == 0:
            commands.append(("BACKGROUND", (0, index), (-1, index), LIGHT))
    table.setStyle(TableStyle(commands))
    return table


def chapter(title: str, number: str) -> list:
    return [PageBreak(), *heading(title, number)]


def draw_cover(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.rect(0, height - 1.2 * cm, width, 1.2 * cm, fill=1, stroke=0)
    canvas.setFillColor(TEAL)
    canvas.circle(width - 2.0 * cm, 2.0 * cm, 0.8 * cm, fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.circle(width - 3.4 * cm, 3.1 * cm, 0.55 * cm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#31404F"))
    canvas.setLineWidth(8)
    canvas.line(width - 7.0 * cm, 2.2 * cm, width - 4.0 * cm, 4.0 * cm)
    canvas.line(width - 4.0 * cm, 4.0 * cm, width - 2.2 * cm, 5.0 * cm)
    canvas.restoreState()


def draw_later(canvas, doc) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.line(2.0 * cm, height - 1.35 * cm, width - 2.0 * cm, height - 1.35 * cm)
    canvas.setFont("LiberationSans", 7.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(2.0 * cm, height - 1.05 * cm, "IMT-342  |  Hito 1  |  ABB IRB 120")
    canvas.drawRightString(width - 2.0 * cm, 1.1 * cm, f"Página {doc.page}")
    canvas.setFillColor(ORANGE)
    canvas.rect(2.0 * cm, 0.92 * cm, 1.0 * cm, 0.08 * cm, fill=1, stroke=0)
    canvas.restoreState()


def build_story() -> list:
    story = []

    story += [Spacer(1, 4.6 * cm)]
    story.append(p("PROYECTO FINAL IMT-342", "CoverSub"))
    story.append(Spacer(1, 0.35 * cm))
    story.append(p("Guía práctica del Hito 1", "CoverTitle"))
    story.append(p("ROS 2, URDF/Xacro y cinemática del ABB IRB 120", "CoverTitle"))
    story.append(Spacer(1, 0.8 * cm))
    story.append(
        p(
            "Manual desde cero para compilar, ejecutar, mover y defender el gemelo digital con pinza paralela.",
            "CoverSub",
        )
    )
    story.append(Spacer(1, 2.0 * cm))
    cover_metrics = Table(
        [
            [p("RESULTADO VERIFICADO", "SmallX"), p("PRECISIÓN", "SmallX")],
            [p("9 pruebas aprobadas", "BigNumber"), p("2.22 x 10<super>-16</super> m", "BigNumber")],
        ],
        colWidths=[8.0 * cm, 8.0 * cm],
    )
    cover_metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#22303D")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#40505F")),
                ("INNERGRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#40505F")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(cover_metrics)
    story.append(Spacer(1, 1.0 * cm))
    story.append(p("Versión comprobada el 10 de septiembre de 2026  ·  Ubuntu 24.04  ·  ROS 2 Jazzy", "CoverSub"))

    story += chapter("Cómo usar este manual", "0")
    story.append(
        callout(
            "Resultado actual",
            "El Hito 1 está completo en su parte cinemática y funcional. El CAD real queda pendiente, pero hoy el robot se puede compilar, visualizar, mover y validar con geometría provisional.",
            "ok",
        )
    )
    story.append(Spacer(1, 8))
    story.append(p("Lee primero los capítulos 1 a 4 para entender las ideas. Para la demostración en vivo usa los capítulos 8 a 11. El capítulo 15 contiene respuestas cortas para la defensa."))
    story.append(p("No necesitas memorizar todos los comandos. Comprende qué prepara cada uno y usa la hoja rápida del final como apoyo."))
    story.append(p("Contenido", "H2X"))
    toc = [
        ["1", "Qué exigía el Hito 1"],
        ["2", "Conceptos mínimos de ROS 2"],
        ["3", "Qué son URDF y Xacro"],
        ["4", "Cómo se construyó el robot"],
        ["5", "Modelo Denavit-Hartenberg"],
        ["6", "Arquitectura del paquete"],
        ["7", "Qué se creó, modificó y eliminó"],
        ["8", "Entrar a ROS 2 y compilar manualmente"],
        ["9", "Abrir RViz y mover automáticamente"],
        ["10", "Mover el robot manualmente"],
        ["11", "Inspeccionar nodos, tópicos, TF y error"],
        ["12", "Pruebas y evidencia"],
        ["13", "Errores comunes"],
        ["14", "Formato CAD que debes conseguir"],
        ["15", "Preguntas probables de defensa"],
        ["16", "Guion de demostración de 7 minutos"],
        ["17", "Hoja rápida de comandos"],
    ]
    story.append(data_table([["Cap.", "Tema"], *toc], [1.3 * cm, 15.0 * cm], font_size=9))

    story += chapter("Qué exigía el Hito 1", "1")
    story.append(p("La Guía PFI solicita un paquete ROS del ABB IRB 120 con pinza, un modelo URDF modular y una demostración de que la pose cartesiana coincide con una cinemática directa implementada por el equipo. El error posicional debe ser menor a 1 x 10<super>-6</super> m. No se debe delegar la solución cinemática a MoveIt."))
    story.append(p("Traducción a tareas concretas", "H2X"))
    for text in [
        "Crear un paquete ROS 2 que pueda compilarse con colcon.",
        "Describir base, seis eslabones, seis articulaciones y pinza en URDF/Xacro.",
        "Publicar estados articulares y transformaciones para que RViz dibuje el robot.",
        "Programar la cinemática directa DH explícitamente en Python y NumPy.",
        "Comparar DH contra una evaluación independiente de la cadena URDF.",
        "Mostrar evidencia repetible: pruebas, error numérico y demostración visual.",
    ]:
        story.append(bullet(text))
    story.append(Spacer(1, 6))
    story.append(callout("Criterio de aprobación", "Error máximo medido: 2.220446049250e-16 m. Límite: 1.0e-6 m. El resultado es APROBADO.", "ok"))
    story.append(p("Qué no está incluido todavía", "H2X"))
    story.append(p("La geometría exterior exacta del fabricante no está disponible. Por eso los cuerpos naranjas son cilindros, cajas y esferas provisionales. Esto cambia la apariencia, pero no modifica los frames, los ejes, las longitudes DH ni la posición de tool0."))

    story += chapter("Conceptos mínimos de ROS 2", "2")
    glossary = [
        ["Concepto", "Explicación sencilla", "Ejemplo del proyecto"],
        ["ROS 2", "Infraestructura que permite comunicar programas robóticos.", "ROS 2 Jazzy"],
        ["Workspace", "Carpeta de trabajo que agrupa paquetes fuente y resultados de compilación.", "ros2_ws"],
        ["Paquete", "Unidad organizada de código, recursos y metadatos.", "irb120_hito1"],
        ["Nodo", "Programa que realiza una función concreta.", "motion_demo"],
        ["Tópico", "Canal por el que los nodos publican y reciben mensajes.", "/joint_states"],
        ["Mensaje", "Estructura de datos que viaja por un tópico.", "JointState"],
        ["Frame", "Sistema de coordenadas unido a una parte del robot.", "base_link, tool0"],
        ["TF", "Sistema que mantiene transformaciones entre frames a lo largo del tiempo.", "base_link a tool0"],
        ["RViz", "Visualizador 3D de datos ROS. No es un simulador dinámico.", "Ventana del robot"],
        ["Launch", "Archivo que inicia varios nodos con una sola orden.", "display.launch.py"],
    ]
    story.append(data_table(glossary, [2.4 * cm, 8.7 * cm, 5.3 * cm], font_size=8.2))
    story.append(p("La idea completa en una cadena", "H2X"))
    flow = data_table(
        [
            ["1. Comando", "2. Estado", "3. Transformaciones", "4. Visualización"],
            ["motion_demo o usuario", "joint_state_source publica /joint_states", "robot_state_publisher calcula TF desde URDF", "RViz dibuja links y frames"],
        ],
        [4.1 * cm] * 4,
        font_size=8.1,
    )
    story.append(flow)
    story.append(Spacer(1, 8))
    story.append(callout("Idea clave", "ROS 2 no es el robot ni la matemática. Es la infraestructura que conecta la fuente de posiciones, el modelo, el validador y el visualizador.", "info"))

    story += chapter("Qué son URDF y Xacro", "3")
    story.append(p("URDF significa Unified Robot Description Format. Es un documento XML que representa el robot como un árbol. Los nodos del árbol son links y las conexiones son joints."))
    story.append(p("Elementos de un link", "H2X"))
    for text in [
        "visual: forma y material que se ve en RViz.",
        "collision: forma simplificada que se usaría para detectar colisiones.",
        "inertial: masa, centro de masa y matriz de inercia.",
    ]:
        story.append(bullet(text))
    story.append(p("Elementos de un joint", "H2X"))
    for text in [
        "parent y child: indican qué dos links conecta.",
        "origin: posición y orientación fija del joint respecto al padre.",
        "axis: eje alrededor del cual rota o se desplaza.",
        "limit: rango, velocidad y esfuerzo permitidos.",
        "type: fixed, revolute, continuous o prismatic, entre otros.",
    ]:
        story.append(bullet(text))
    story.append(p("Xacro no reemplaza URDF: lo genera", "H2X"))
    story.append(p("URDF puro puede ser largo y repetitivo. Xacro agrega variables, propiedades y macros. En este proyecto un macro crea el IRB 120 y otro crea la pinza. El archivo principal llama a ambos. Luego Xacro se expande a un URDF normal que ROS puede leer."))
    story.append(code("xacro irb120_with_gripper.urdf.xacro -o irb120_with_gripper.urdf"))
    story.append(callout("Defensa", "Si preguntan por qué se entregan Xacro y URDF: Xacro demuestra modularidad; el URDF expandido permite inspección y validación reproducible.", "info"))

    story += chapter("Cómo se construyó el robot", "4")
    story.append(p("La construcción se hizo por capas para que cada parte tenga una responsabilidad clara."))
    steps = [
        ["Paso", "Qué se hizo", "Archivo principal"],
        ["1", "Se transcribió la tabla DH y se implementaron matrices homogéneas.", "kinematics/dh.py"],
        ["2", "Cada fila DH se descompuso en un joint móvil y frames fijos URDF.", "urdf/irb120.macro.xacro"],
        ["3", "Se añadieron visuales provisionales, colisiones, límites e inercias.", "urdf/irb120.macro.xacro"],
        ["4", "Se creó una pinza paralela modular con dos dedos prismáticos y TCP.", "urdf/gripper.macro.xacro"],
        ["5", "El archivo principal unió materiales, robot y pinza.", "urdf/irb120_with_gripper.urdf.xacro"],
        ["6", "Se expandió Xacro y se creó un evaluador URDF independiente.", "kinematics/urdf_chain.py"],
        ["7", "Se añadieron nodos de estados, movimiento y validación.", "nodes/"],
        ["8", "Se creó un launch integral y una vista RViz preparada.", "launch/ y rviz/"],
        ["9", "Se escribieron pruebas para DH, URDF y movimiento.", "test/"],
    ]
    story.append(data_table(steps, [1.1 * cm, 10.3 * cm, 5.0 * cm], font_size=8.1))
    story.append(p("Cómo se unió la pinza", "H2X"))
    story.append(p("El último frame del robot es tool0. Se añadió un joint fijo gripper_mount que conecta tool0 con gripper_base_link. Dos joints prismáticos desplazan los dedos en sentidos opuestos. Finalmente, tcp_link se fija a 0.160 m desde tool0 como valor provisional."))
    story.append(callout("Modularidad", "Cuando llegue el CAD, se reemplazan las etiquetas visual y collision. No se cambian los joints ni la matemática validada.", "ok"))

    story += chapter("Modelo Denavit-Hartenberg", "5")
    story.append(p("Se usa DH clásico. La transformación de un frame al siguiente es:"))
    story.append(code("T(i-1,i) = Rz(theta_i) · Tz(d_i) · Tx(a_i) · Rx(alpha_i)"))
    dh_rows = [
        ["Eje", "theta efectivo", "d [m]", "a [m]", "alpha [rad]"],
        ["1", "q1", "0.290", "0.000", "-pi/2"],
        ["2", "q2 - pi/2", "0.000", "0.270", "0"],
        ["3", "q3", "0.000", "0.070", "-pi/2"],
        ["4", "q4", "0.302", "0.000", "pi/2"],
        ["5", "q5", "0.000", "0.000", "-pi/2"],
        ["6", "q6 + pi", "0.072", "0.000", "0"],
    ]
    story.append(data_table(dh_rows, [1.4 * cm, 4.4 * cm, 3.2 * cm, 3.2 * cm, 4.0 * cm], font_size=8.7))
    story.append(p("Qué significa cada parámetro", "H2X"))
    for text in [
        "theta: rotación alrededor del eje Z anterior. En un robot revoluto contiene q.",
        "d: desplazamiento a lo largo del eje Z anterior.",
        "a: longitud común normal entre dos ejes, medida sobre X.",
        "alpha: giro entre los ejes Z, medido alrededor de X.",
    ]:
        story.append(bullet(text))
    story.append(p("La cinemática directa multiplica seis matrices. El resultado es una matriz homogénea 4 x 4. Su bloque superior izquierdo 3 x 3 representa orientación y la última columna representa la posición [x, y, z]."))
    story.append(p("Por qué URDF y DH pueden coincidir exactamente", "H2X"))
    story.append(p("URDF aplica primero el origin fijo y después el movimiento del joint. Para respetar el orden DH, cada fila se representa como Rz(q) en el joint móvil, luego un frame fijo con el offset angular y otro frame fijo con Tz(d), Tx(a) y Rx(alpha)."))

    story += chapter("Arquitectura del paquete", "6")
    tree = """
irb120_hito1/
├── package.xml                 dependencias ROS
├── setup.py                    instalación y ejecutables
├── launch/display.launch.py    inicia todo el sistema
├── config/                     parámetros articulares
├── rviz/hito1.rviz             vista 3D preparada
├── urdf/
│   ├── materials.xacro
│   ├── irb120.macro.xacro
│   ├── gripper.macro.xacro
│   ├── irb120_with_gripper.urdf.xacro
│   └── irb120_with_gripper.urdf
├── irb120_hito1/
│   ├── kinematics/dh.py
│   ├── kinematics/urdf_chain.py
│   ├── motion.py
│   ├── nodes/joint_state_source.py
│   ├── nodes/motion_demo.py
│   ├── nodes/fk_validator.py
│   └── verify_model.py
└── test/
    ├── test_dh.py
    ├── test_motion.py
    └── test_urdf_matches_dh.py
"""
    story.append(code(tree))
    roles = [
        ["Ejecutable", "Entrada", "Salida / función"],
        ["joint_state_source", "Comandos en grados", "Publica /joint_states y aplica límites"],
        ["motion_demo", "Tiempo", "Publica una secuencia suave y cíclica"],
        ["robot_state_publisher", "URDF + /joint_states", "Publica TF"],
        ["fk_validator", "/joint_states", "Compara DH contra URDF y publica error"],
        ["verify_model", "URDF + posturas fijas", "Pasaporte offline reproducible"],
        ["rviz2", "URDF + TF", "Muestra robot, grilla y frames"],
    ]
    story.append(data_table(roles, [4.0 * cm, 5.0 * cm, 7.4 * cm], font_size=8.4))

    story += chapter("Qué se creó, modificó y eliminó", "7")
    story.append(p("Creado para el Hito 1", "H2X"))
    for text in [
        "Paquete ROS 2 irb120_hito1 con recursos instalables.",
        "Modelo Xacro modular y URDF expandido.",
        "Implementación DH y evaluador de cadena URDF independientes.",
        "Nodos para estados articulares, validación y movimiento automático.",
        "Configuración RViz, archivo launch y nueve pruebas.",
        "Documentos de modelo, trazabilidad, resultados, guion, manual y presentación.",
        "Capturas reales del robot funcionando en RViz.",
    ]:
        story.append(bullet(text))
    story.append(p("Modificado o mejorado", "H2X"))
    for text in [
        "README principal y README del paquete con comandos reales.",
        "Parámetros DH, límites oficiales, masas e inercias aproximadas documentadas.",
        "Validador en vivo ajustado para comparar la misma muestra por DH y URDF durante movimiento continuo.",
        "Launch ampliado con el argumento demo_motion.",
        ".gitignore ampliado para evitar resultados de compilación en la raíz.",
    ]:
        story.append(bullet(text))
    story.append(p("Eliminado", "H2X"))
    story.append(p("Se movieron a la papelera las carpetas build, install y log de la raíz. Eran resultados regenerables creados por compilar desde la carpeta equivocada. No se eliminó código fuente ni la compilación correcta de ros2_ws."))
    story.append(callout("Qué falta", "Solo falta integrar el CAD real y confirmar datos finales de la pinza. Para la entrega de hoy, la función y la precisión del Hito 1 están completas.", "warn"))

    story += chapter("Entrar a ROS 2 y compilar manualmente", "8")
    story.append(callout("Regla de oro", "Cada terminal nueva empieza sin conocer ROS ni tu workspace. Debes cargar ambos entornos con source.", "warn"))
    story.append(p("Paso 1. Abrir una terminal", "H2X"))
    story.append(p("Presiona Ctrl+Alt+T. El símbolo $ indica que la terminal está esperando una orden. Escribe una línea y presiona Enter."))
    story.append(p("Paso 2. Entrar al proyecto", "H2X"))
    story.append(code("cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto\npwd\nls"))
    story.append(p("pwd debe terminar en /proyecto. ls debe mostrar ros2_ws, docs, referencias y otros archivos."))
    story.append(p("Paso 3. Cargar ROS 2 Jazzy", "H2X"))
    story.append(code("source /opt/ros/jazzy/setup.bash\nros2 --help"))
    story.append(p("source modifica solo la terminal actual. No instala nada y no cambia archivos."))
    story.append(p("Paso 4. Entrar al workspace y compilar", "H2X"))
    story.append(code("cd ros2_ws\ncolcon build --symlink-install --packages-select irb120_hito1"))
    story.append(p("src contiene el código. build guarda trabajo temporal. install contiene lo ejecutable. log guarda reportes. Debes compilar desde ros2_ws, no desde proyecto."))
    story.append(p("Paso 5. Cargar lo recién compilado", "H2X"))
    story.append(code("source install/setup.bash\nros2 pkg prefix irb120_hito1"))
    story.append(p("El último comando debe mostrar una ruta dentro de ros2_ws/install/irb120_hito1. Si dice que no existe, faltó compilar o cargar install/setup.bash."))
    story.append(callout("Miniconda", "En esta computadora no ejecutes nodos ROS con el Python de Miniconda. Usa ros2 después de los dos source. Para diagnósticos directos usa /usr/bin/python3.", "danger"))

    story += chapter("Abrir RViz y mover automáticamente", "9")
    story.append(p("Con ROS y el workspace cargados, ejecuta:"))
    story.append(code("ros2 launch irb120_hito1 display.launch.py demo_motion:=true"))
    story.append(p("Este único comando inicia cinco procesos: robot_state_publisher, joint_state_source, fk_validator, motion_demo y rviz2."))
    story.append(p("Qué debes observar", "H2X"))
    for text in [
        "Se abre una ventana 3D de RViz.",
        "El brazo naranja cambia de postura suavemente.",
        "Los dos dedos de la pinza se abren y cierran.",
        "Los ejes de colores muestran los frames DH y TF.",
        "La terminal imprime APROBADO | DH vs URDF aproximadamente una vez por segundo.",
    ]:
        story.append(bullet(text))
    if SCREENSHOT.exists():
        story.append(Spacer(1, 5))
        story.append(Image(str(SCREENSHOT), width=16.8 * cm, height=11.2 * cm))
        story.append(p("Captura real de la demostración automática en esta computadora. La forma exterior es provisional; la cadena cinemática es la validada.", "SmallX"))
    story.append(callout("Para terminar", "Vuelve a la terminal donde ejecutaste launch y presiona Ctrl+C una sola vez. ROS cerrará todos los procesos.", "info"))

    story += chapter("Mover el robot manualmente", "10")
    story.append(p("Usa dos terminales. La primera mantiene el sistema encendido. La segunda envía comandos."))
    story.append(p("Terminal 1", "H2X"))
    story.append(code("source /opt/ros/jazzy/setup.bash\ncd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws\nsource install/setup.bash\nros2 launch irb120_hito1 display.launch.py"))
    story.append(p("Terminal 2", "H2X"))
    story.append(code("source /opt/ros/jazzy/setup.bash\ncd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws\nsource install/setup.bash\nros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \\\n+  \"{data: [30.0, -20.0, 15.0, 40.0, -35.0, 60.0, 0.010]}\""))
    story.append(p("Interpretación del mensaje", "H2X"))
    manual_rows = [
        ["Posición", "Significado", "Unidad"],
        ["1 a 6", "Ángulos q1 a q6", "grados"],
        ["7 opcional", "Apertura de cada dedo", "metros, 0 a 0.015"],
    ]
    story.append(data_table(manual_rows, [3.0 * cm, 8.4 * cm, 5.0 * cm], font_size=9))
    story.append(p("Prueba otras posturas seguras", "H2X"))
    story.append(code("# Postura cero\nros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \\\n+  \"{data: [0, 0, 0, 0, 0, 0, 0.0]}\"\n\n# Postura alternativa\nros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \\\n+  \"{data: [-45, 25, -30, 50, 20, -90, 0.015]}\""))
    story.append(callout("Límites", "El nodo limita automáticamente valores fuera del rango oficial y muestra una advertencia. Esta protección es para el gemelo, no sustituye la seguridad de un robot físico.", "warn"))

    story += chapter("Inspeccionar nodos, tópicos, TF y error", "11")
    commands = [
        ["Qué quieres ver", "Comando"],
        ["Nodos activos", "ros2 node list"],
        ["Tópicos activos", "ros2 topic list"],
        ["Estados articulares", "ros2 topic echo /joint_states --once"],
        ["Error cinemático", "ros2 topic echo /irb120/fk_position_error_m"],
        ["Frecuencia de estados", "ros2 topic hz /joint_states"],
        ["Información del tópico", "ros2 topic info /joint_states -v"],
        ["Transformación base-herramienta", "ros2 run tf2_ros tf2_echo base_link tool0"],
        ["Argumentos del launch", "ros2 launch irb120_hito1 display.launch.py --show-args"],
    ]
    story.append(data_table(commands, [6.2 * cm, 10.2 * cm], font_size=8.3))
    story.append(p("Cómo leer una transformación", "H2X"))
    story.append(p("tf2_echo muestra Translation [x, y, z] en metros y Rotation como cuaternión y RPY. base_link es el origen fijo; tool0 es la brida del eje 6; tcp_link es el punto de trabajo de la pinza."))
    story.append(p("Para validar el TCP directamente:", "BodyX"))
    story.append(code("ros2 launch irb120_hito1 display.launch.py target_frame:=tcp_link"))
    story.append(callout("Ctrl+C", "Los comandos que escuchan continuamente, como topic echo y tf2_echo, se detienen con Ctrl+C.", "info"))

    story += chapter("Pruebas y evidencia", "12")
    story.append(p("Pruebas automatizadas", "H2X"))
    story.append(code("colcon test --packages-select irb120_hito1 --event-handlers console_direct+\ncolcon test-result --verbose"))
    story.append(p("Resultado esperado: 9 tests, 0 errors, 0 failures, 0 skipped."))
    story.append(p("Pasaporte offline", "H2X"))
    story.append(code("ros2 run irb120_hito1 verify_model"))
    result_rows = [
        ["Métrica", "Resultado", "Criterio"],
        ["Error posicional máximo", "2.220446049250e-16 m", "menor a 1.0e-6 m"],
        ["Error de orientación máximo", "1.004007835075e-15 rad", "informativo"],
        ["Posturas documentadas", "4 x 2 frames", "tool0 y tcp_link"],
        ["Posturas aleatorias en tests", "100 reproducibles", "dentro de límites"],
    ]
    story.append(data_table(result_rows, [5.3 * cm, 5.8 * cm, 5.3 * cm], font_size=8.6))
    story.append(Spacer(1, 8))
    story.append(callout("Por qué hay un número pequeño y no cero", "Los cálculos usan punto flotante. Diferencias alrededor de 1e-16 son redondeo numérico de la computadora, no un desplazamiento físico medible.", "info"))
    story.append(p("Dos caminos independientes", "H2X"))
    story.append(p("Camino A multiplica las matrices DH escritas en Python. Camino B recorre los joints del URDF expandido, interpreta origin, axis y tipo de joint, y multiplica sus transformaciones. Si ambos llegan a la misma pose en muchas posturas, los parámetros y su traducción a URDF son coherentes."))

    story += chapter("Errores comunes", "13")
    troubleshooting = [
        ["Síntoma", "Causa probable", "Solución"],
        ["ros2: command not found", "No se cargó ROS.", "source /opt/ros/jazzy/setup.bash"],
        ["Package irb120_hito1 not found", "No se cargó el workspace o no se compiló.", "Compila desde ros2_ws y ejecuta source install/setup.bash"],
        ["No aparece RViz", "Launch se ejecutó con use_rviz:=false o falló el entorno gráfico.", "Usa el comando normal y revisa la terminal"],
        ["El robot no se mueve", "No está activo motion_demo y no llegó un comando.", "Usa demo_motion:=true o publica la postura manual"],
        ["El comando manual no funciona", "La segunda terminal no tiene los source.", "Carga ROS y ros2_ws/install en esa terminal"],
        ["Error de rclpy o libstdc++", "Se mezcló Miniconda con ROS Jazzy.", "Abre una terminal normal; evita python de Conda"],
        ["Se crearon build/install/log en proyecto", "colcon se ejecutó una carpeta arriba.", "Elimina esos generados y compila dentro de ros2_ws"],
        ["RViz muestra geometría simple", "Aún no se integró el CAD.", "Es el estado provisional previsto; la cinemática sí es final"],
    ]
    story.append(data_table(troubleshooting, [4.2 * cm, 5.3 * cm, 6.9 * cm], font_size=7.8))
    story.append(p("Diagnóstico mínimo", "H2X"))
    story.append(code("pwd\nwhich ros2\nros2 pkg prefix irb120_hito1\nros2 node list\nros2 topic list"))
    story.append(callout("Contraseñas", "Nunca escribas una contraseña dentro de un script, README, historial compartido o presentación. sudo solo debe pedirla de forma interactiva si realmente falta instalar algo.", "danger"))

    story += chapter("Formato CAD que debes conseguir", "14")
    story.append(p("Opción ideal", "H2X"))
    story.append(p("Un paquete URDF/Xacro oficial o confiable con un mesh separado para base_link y cada link_1 a link_6. Para visual conviene Collada .dae porque conserva colores y materiales. Para colisión conviene .stl simplificado porque es compatible y ligero."))
    story.append(p("Opción aceptable", "H2X"))
    story.append(p("Un ensamble STEP .step o .stp con cada eslabón como componente independiente. Debe incluir unidades, postura cero, nombres de piezas y ubicación de los ejes. Después se exportará cada eslabón por separado."))
    cad_rows = [
        ["Formato", "Uso", "Recomendación"],
        [".dae", "Visual en RViz", "Preferido si conserva colores"],
        [".stl", "Visual o colisión", "Usar uno simplificado para colisión"],
        [".step / .stp", "Fuente CAD editable", "Aceptar si el ensamble separa los eslabones"],
        [".obj", "Visual", "Posible, pero menos común en paquetes ROS"],
        ["Una sola malla fusionada", "Ningún uso cinemático", "No sirve para mover eslabones por separado"],
    ]
    story.append(data_table(cad_rows, [3.1 * cm, 4.7 * cm, 8.6 * cm], font_size=8.4))
    story.append(p("Información adicional necesaria", "H2X"))
    for text in [
        "Unidades exactas del archivo, preferentemente metros o milímetros claramente indicados.",
        "Postura de calibración q = [0,0,0,0,0,0].",
        "Origen y eje de giro de cada articulación.",
        "Para la pinza: carrera, distancia tool0-TCP, masa, centro de masa y orientación de montaje.",
    ]:
        story.append(bullet(text))
    story.append(callout("No descargues una sola pieza", "Para un gemelo articulado, cada eslabón debe poder transformarse de forma independiente.", "warn"))

    story += chapter("Preguntas probables de defensa", "15")
    qa = [
        ["Pregunta", "Respuesta breve"],
        ["¿Qué es ROS 2?", "Infraestructura para que procesos robóticos intercambien datos y coordinen funciones."],
        ["¿Qué es URDF?", "XML que describe links, joints, geometría, límites y propiedades físicas de un robot."],
        ["¿Qué aporta Xacro?", "Macros, propiedades y reutilización; genera el URDF final sin duplicar XML."],
        ["¿Qué diferencia hay entre link y joint?", "Un link es un cuerpo rígido; un joint define cómo se conecta y mueve respecto a otro."],
        ["¿Qué es TF?", "Sistema de ROS que mantiene la relación espacial entre frames a lo largo del tiempo."],
        ["¿RViz simula física?", "No. Visualiza datos y transformaciones; no calcula contacto, fuerza ni dinámica."],
        ["¿Qué es DH?", "Convención de cuatro parámetros para encadenar transformaciones entre eslabones."],
        ["¿Cómo se validó?", "Se comparó el producto DH con un recorrido independiente de la cadena URDF."],
        ["¿Por qué usar varias posturas?", "Una sola postura puede ocultar errores de signo, offset o eje."],
        ["¿Se usó MoveIt?", "No. La cinemática y la evaluación URDF fueron programadas explícitamente."],
        ["¿Qué significa 1e-6 m?", "Un micrómetro: una millonésima de metro."],
        ["¿Por qué falta el CAD?", "El CAD solo sustituirá visuales y colisiones; la cadena matemática ya está cerrada."],
        ["¿Controla un ABB real?", "No todavía. Este hito valida el gemelo cinemático, no la integración segura con hardware."],
    ]
    story.append(data_table(qa, [6.2 * cm, 10.2 * cm], font_size=8.0))

    story += chapter("Guion de demostración de 7 minutos", "16")
    agenda = [
        ["Tiempo", "Qué muestras", "Qué dices"],
        ["0:00-1:00", "Diapositiva de objetivo", "Paquete ROS, URDF modular, pinza y error menor a 1e-6 m."],
        ["1:00-2:00", "Estructura del paquete", "Separé matemática, URDF, nodos, launch, configuración y pruebas."],
        ["2:00-3:00", "Tabla DH y Xacro", "Cada fila DH se descompuso sin cambiar el orden de transformaciones."],
        ["3:00-4:00", "Flujo ROS", "Comando, JointState, TF, RViz y validación."],
        ["4:00-5:30", "RViz en movimiento", "Seis ejes y pinza; la terminal permanece en APROBADO."],
        ["5:30-6:20", "verify_model", "Muestro 2.22e-16 m frente al límite 1e-6 m."],
        ["6:20-7:00", "Pendiente CAD", "La apariencia es provisional; los frames y la cinemática son finales."],
    ]
    story.append(data_table(agenda, [2.6 * cm, 5.0 * cm, 8.8 * cm], font_size=8.2))
    story.append(p("Comandos que conviene dejar listos", "H2X"))
    story.append(code("# Primero, evidencia numérica\nros2 run irb120_hito1 verify_model\n\n# Después, demostración visual\nros2 launch irb120_hito1 display.launch.py demo_motion:=true"))
    story.append(callout("Si RViz demora", "No repitas el comando. Espera unos segundos y mira si la terminal informa que rviz2 inició. Si falla, muestra la captura incluida en la presentación y ejecuta verify_model.", "warn"))

    story += chapter("Hoja rápida de comandos", "17")
    story.append(p("Inicio completo desde una terminal nueva", "H2X"))
    story.append(code("cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto\nsource /opt/ros/jazzy/setup.bash\ncd ros2_ws\ncolcon build --symlink-install --packages-select irb120_hito1\nsource install/setup.bash"))
    story.append(p("Validar", "H2X"))
    story.append(code("colcon test --packages-select irb120_hito1 --event-handlers console_direct+\ncolcon test-result --verbose\nros2 run irb120_hito1 verify_model"))
    story.append(p("Demostrar", "H2X"))
    story.append(code("ros2 launch irb120_hito1 display.launch.py demo_motion:=true"))
    story.append(p("Mover manualmente", "H2X"))
    story.append(code("ros2 topic pub --once /irb120/joint_commands_deg std_msgs/msg/Float64MultiArray \\\n+  \"{data: [30, -20, 15, 40, -35, 60, 0.010]}\""))
    story.append(p("Inspeccionar", "H2X"))
    story.append(code("ros2 node list\nros2 topic list\nros2 topic echo /irb120/fk_position_error_m\nros2 run tf2_ros tf2_echo base_link tool0"))
    story.append(Spacer(1, 10))
    story.append(callout("Secuencia mental", "Entrar al proyecto. Cargar ROS. Entrar a ros2_ws. Compilar. Cargar install. Ejecutar. Ctrl+C para terminar.", "ok"))

    story += chapter("Fuentes y archivos de referencia", "18")
    source_rows = [
        ["Fuente", "Uso en el proyecto"],
        ["Guia_PFI.pdf, sección 4", "Requisitos y pasaporte del Hito 1"],
        ["Bahani et al., IJMERR 2023", "Tabla DH del ABB IRB 120"],
        ["Truc y Lam, 2020", "Masas, centros de masa e inercias CAD aproximadas"],
        ["ABB Product specification IRB 120, 3HAC035960-001 Rev. S", "Rangos articulares y velocidades máximas"],
        ["docs/hito1/modelo_cinematico.md", "Convención, tabla y decisiones técnicas"],
        ["docs/hito1/resultados.md", "Registro de pruebas y mediciones reales"],
        ["docs/hito1/trazabilidad.md", "Relación requisito-implementación-verificación"],
    ]
    story.append(data_table(source_rows, [7.0 * cm, 9.4 * cm], font_size=8.2))
    story.append(Spacer(1, 12))
    story.append(p("Ruta del proyecto", "H2X"))
    story.append(code("/home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto"))
    story.append(p("Este manual fue generado a partir de la versión realmente compilada y probada en esa ruta el 10 de septiembre de 2026."))
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=2.0 * cm,
        leftMargin=2.0 * cm,
        topMargin=1.75 * cm,
        bottomMargin=1.65 * cm,
        title="Guía práctica Hito 1 - ROS 2 y ABB IRB 120",
        author="Equipo IMT-342",
        subject="Manual de uso, aprendizaje y defensa del Hito 1",
    )
    doc.build(build_story(), onFirstPage=draw_cover, onLaterPages=draw_later)
    print(OUTPUT)


if __name__ == "__main__":
    main()
