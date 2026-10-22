from pathlib import Path
from math import pi

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "ros2_ws").is_dir())
OUT = ROOT / "entregables" / "hito1" / "pdf" / "Guia_Practica_Hito1_IRB120_6_Juntas_CORREGIDA.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path("/usr/share/fonts/truetype/liberation")
pdfmetrics.registerFont(TTFont("LiberationSans", str(FONT_DIR / "LiberationSans-Regular.ttf")))
pdfmetrics.registerFont(TTFont("LiberationSans-Bold", str(FONT_DIR / "LiberationSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("LiberationMono", str(FONT_DIR / "LiberationMono-Regular.ttf")))

NAVY = colors.HexColor("#132238")
ORANGE = colors.HexColor("#F28C28")
TEAL = colors.HexColor("#167D8D")
GREEN = colors.HexColor("#2E8B57")
RED = colors.HexColor("#B43A3A")
INK = colors.HexColor("#202733")
MUTED = colors.HexColor("#5B6675")
PALE = colors.HexColor("#F4F6F8")
PALE_ORANGE = colors.HexColor("#FFF3E4")
PALE_TEAL = colors.HexColor("#EAF6F7")
WHITE = colors.white

PAGE_W, PAGE_H = A4
MARGIN_X = 1.65 * cm
MARGIN_TOP = 1.75 * cm
MARGIN_BOTTOM = 1.55 * cm


def P(text, style):
    return Paragraph(text, style)


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="BodyX", fontName="LiberationSans", fontSize=9.1, leading=12.2,
    textColor=INK, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="SmallX", fontName="LiberationSans", fontSize=7.8, leading=10.1,
    textColor=MUTED,
))
styles.add(ParagraphStyle(
    name="TitleX", fontName="LiberationSans-Bold", fontSize=28, leading=32,
    textColor=WHITE, alignment=TA_LEFT,
))
styles.add(ParagraphStyle(
    name="SubtitleX", fontName="LiberationSans", fontSize=13, leading=17,
    textColor=colors.HexColor("#DCE5EF"),
))
styles.add(ParagraphStyle(
    name="H1X", fontName="LiberationSans-Bold", fontSize=17, leading=21,
    textColor=NAVY, spaceAfter=10,
))
styles.add(ParagraphStyle(
    name="H2X", fontName="LiberationSans-Bold", fontSize=11.2, leading=14,
    textColor=TEAL, spaceBefore=4, spaceAfter=5,
))
styles.add(ParagraphStyle(
    name="CalloutX", fontName="LiberationSans-Bold", fontSize=9.3, leading=12.2,
    textColor=NAVY,
))
styles.add(ParagraphStyle(
    name="CodeX", fontName="LiberationMono", fontSize=7.7, leading=10.2,
    textColor=INK, leftIndent=6, rightIndent=6,
))
styles.add(ParagraphStyle(
    name="TableHeadX", fontName="LiberationSans-Bold", fontSize=7.5, leading=9,
    textColor=WHITE, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="TableCellX", fontName="LiberationSans", fontSize=7.2, leading=9,
    textColor=INK, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name="TableCellLeftX", fontName="LiberationSans", fontSize=7.2, leading=9,
    textColor=INK, alignment=TA_LEFT,
))


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 0.42 * cm, PAGE_W, 0.42 * cm, fill=1, stroke=0)
    canvas.setFillColor(ORANGE)
    canvas.rect(0, PAGE_H - 0.42 * cm, 3.0 * cm, 0.42 * cm, fill=1, stroke=0)
    if doc.page > 1:
        canvas.setFont("LiberationSans", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_X, 0.72 * cm, "IMT-342 - Hito 1 ABB IRB 120")
        canvas.drawRightString(PAGE_W - MARGIN_X, 0.72 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


frame = Frame(
    MARGIN_X,
    MARGIN_BOTTOM,
    PAGE_W - 2 * MARGIN_X,
    PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
    id="normal",
)
doc = BaseDocTemplate(
    str(OUT), pagesize=A4, leftMargin=MARGIN_X, rightMargin=MARGIN_X,
    topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
    title="Guia practica Hito 1 - ABB IRB 120 - 6 juntas",
    author="Proyecto IMT-342",
)
doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=header_footer)])


def table(data, widths, header=True, font_size=7.2):
    rows = []
    for r, row in enumerate(data):
        st = styles["TableHeadX"] if r == 0 and header else styles["TableCellX"]
        rows.append([P(str(v), st) for v in row])
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    rules = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#AAB4C0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 1 if header else 0), (-1, -1), WHITE),
    ]
    if header:
        rules += [("BACKGROUND", (0, 0), (-1, 0), NAVY)]
    for r in range(1 if header else 0, len(rows)):
        if r % 2 == 0:
            rules.append(("BACKGROUND", (0, r), (-1, r), PALE))
    t.setStyle(TableStyle(rules))
    return t


def callout(title, text, color=PALE_TEAL):
    t = Table(
        [[P(title, styles["CalloutX"]), P(text, styles["BodyX"])]],
        colWidths=[3.7 * cm, 12.0 * cm],
    )
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("BOX", (0, 0), (-1, -1), 0.8, TEAL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def bullet(text):
    return P(f"<font color='#F28C28'>&#8226;</font> {text}", styles["BodyX"])


def code_block(lines):
    safe = lines.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = Table([[P(safe.replace("\n", "<br/>"), styles["CodeX"])]], colWidths=[15.7 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF1F4")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#BBC4CE")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


story = []

# Cover
cover = Table(
    [[P("HITO 1", ParagraphStyle("CoverTag", parent=styles["H2X"], textColor=ORANGE, fontSize=12)), ""],
     [P("ABB IRB 120 en ROS 2", styles["TitleX"]), ""],
     [P("Guia practica corregida: modelo de 6 juntas, conversion DH a URDF, validacion y demostracion en vivo", styles["SubtitleX"]), ""],
     [P("Version para examen - sin CAD, sin fisica y sin marcos auxiliares", ParagraphStyle("CoverFoot", parent=styles["BodyX"], textColor=WHITE, fontSize=10)), ""]],
    colWidths=[15.1 * cm, 0.6 * cm], rowHeights=[1.2 * cm, 3.0 * cm, 2.6 * cm, 1.2 * cm],
)
cover.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), NAVY),
    ("SPAN", (0, 0), (1, 0)), ("SPAN", (0, 1), (1, 1)),
    ("SPAN", (0, 2), (1, 2)), ("SPAN", (0, 3), (1, 3)),
    ("LEFTPADDING", (0, 0), (-1, -1), 18),
    ("RIGHTPADDING", (0, 0), (-1, -1), 18),
    ("TOPPADDING", (0, 0), (-1, -1), 12),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
]))
story += [Spacer(1, 2.2 * cm), cover, Spacer(1, 1.0 * cm)]
story.append(callout("Resultado final", "6 juntas rotacionales, 6 marcos moviles, 0 juntas fijas, 0 elementos inerciales y 0 geometrías de colision. La equivalencia DH-URDF fue aprobada en 12 pruebas automatizadas.", PALE_ORANGE))
story += [Spacer(1, 1.0 * cm), P("Documento preparado para estudiar, ejecutar la demostracion y responder preguntas de defensa.", styles["BodyX"]), PageBreak()]

# 1
story += [P("1. Que se corrigio y cual es el alcance", styles["H1X"])]
story += [P("El modelo anterior habia separado cada transformacion DH en varios links y joints fijos. Eso producia muchos marcos TF y dificultaba defender el arbol. La version final conserva la misma cinematica, pero expresa cada fila DH mediante el origen de la siguiente junta. El resultado es un arbol serial minimo.", styles["BodyX"])]
story += [Spacer(1, 4), table([
    ["Elemento", "Cantidad final", "Interpretacion"],
    ["Juntas revolutas", "6", "joint_1 a joint_6"],
    ["Marcos moviles", "6", "link_1 a link_5 y tool0"],
    ["Link base", "1", "base_link, necesario como raiz"],
    ["Juntas fijas", "0", "No se crean marcos DH auxiliares"],
    ["inertial", "0", "No se modela dinamica en este hito"],
    ["collision", "0", "No se afirma deteccion formal de colisiones"],
], [3.6 * cm, 3.2 * cm, 8.9 * cm])]
story += [Spacer(1, 8), callout("Aclaracion importante", "Cuando se dice '6 marcos' se cuentan los seis marcos moviles del manipulador. ROS tambien necesita el marco raiz base_link; por eso el archivo contiene 7 links en total, pero solo 6 juntas y 6 transformaciones variables.")]
story += [Spacer(1, 8), P("Arbol jerarquico final", styles["H2X"]), code_block(
    "base_link\n  -> joint_1 -> link_1\n  -> joint_2 -> link_2\n  -> joint_3 -> link_3\n  -> joint_4 -> link_4\n  -> joint_5 -> link_5\n  -> joint_6 -> tool0"
)]
story += [Spacer(1, 8), bullet("El CAD no es obligatorio para demostrar la cinematica."), bullet("Los cilindros y esferas actuales son solo una representacion visual provisional."), bullet("El futuro CAD se agregara como mallas visuales sin cambiar las seis juntas."), PageBreak()]

# 2
story += [P("2. URDF: que es y como lo interpreta ROS", styles["H1X"])]
story += [P("URDF significa Unified Robot Description Format. Es un archivo XML que describe un robot como un arbol de links unidos por joints. robot_state_publisher lee ese arbol y, usando los valores de las juntas, publica las transformaciones TF. RViz dibuja el resultado.", styles["BodyX"])]
story += [table([
    ["Etiqueta", "Funcion", "En este proyecto"],
    ["link", "Representa un cuerpo o marco", "base_link, link_1...link_5, tool0"],
    ["joint", "Relacion padre-hijo", "6 joints revolute"],
    ["parent / child", "Define el arbol", "Cadena serial, sin ramas"],
    ["origin xyz rpy", "Transformacion fija antes del giro", "Contiene la geometria DH reordenada"],
    ["axis", "Eje de la junta en el marco local", "0 0 1 para las seis juntas"],
    ["limit", "Limites de posicion y velocidad", "Valores del IRB 120"],
    ["visual", "Solo apariencia", "Primitivas hasta disponer del CAD"],
], [3.0 * cm, 5.4 * cm, 7.3 * cm])]
story += [Spacer(1, 8), P("Por que aparecen numeros en visual/origin", styles["H2X"])]
story += [P("El origen dentro de visual mueve solamente el cilindro, la caja o la esfera para que quede centrado sobre el eslabon. No crea otro marco TF, no cambia el eje de la junta y no participa en la cinematica. Por ejemplo, si un cilindro mide 0.290 m, su centro puede colocarse en z = 0.145 m para que empiece en z = 0 y termine en z = 0.290 m.", styles["BodyX"])]
story += [callout("Tres origenes distintos", "joint/origin define cinematica. visual/origin acomoda el dibujo. inertial/origin ubicaria el centro de masa para dinamica; fue eliminado porque este hito no evalua fisica.", PALE_ORANGE)]
story += [Spacer(1, 8), P("Fragmento conceptual", styles["H2X"]), code_block(
    '<joint name="joint_2" type="revolute">\n  <parent link="link_1"/>\n  <child link="link_2"/>\n  <origin xyz="0 0 0.290" rpy="-pi/2 -pi/2 0"/>\n  <axis xyz="0 0 1"/>\n</joint>'
), PageBreak()]

# 3
story += [P("3. Parametros Denavit-Hartenberg del ABB IRB 120", styles["H1X"])]
story += [P("Se usa la convencion DH clasica. Cada fila genera la matriz A_i = Rz(theta_i) Tz(d_i) Tx(a_i) Rx(alpha_i). Las longitudes estan en metros y los angulos en radianes.", styles["BodyX"])]
dh = [
    ["i", "theta_i", "d_i [m]", "a_i [m]", "alpha_i"],
    ["1", "q1", "0.290", "0", "-pi/2"],
    ["2", "q2 - pi/2", "0", "0.270", "0"],
    ["3", "q3", "0", "0.070", "-pi/2"],
    ["4", "q4", "0.302", "0", "+pi/2"],
    ["5", "q5", "0", "0", "-pi/2"],
    ["6", "q6 + pi", "0.072", "0", "0"],
]
story += [table(dh, [1.2 * cm, 4.0 * cm, 3.2 * cm, 3.2 * cm, 4.1 * cm])]
story += [Spacer(1, 10), P("Matriz DH clasica", styles["H2X"])]
story += [code_block(
    "A_i = [ cos(theta)  -sin(theta)cos(alpha)   sin(theta)sin(alpha)   a cos(theta) ]\n"
    "      [ sin(theta)   cos(theta)cos(alpha)  -cos(theta)sin(alpha)   a sin(theta) ]\n"
    "      [     0              sin(alpha)             cos(alpha)            d      ]\n"
    "      [     0                  0                      0                 1      ]"
)]
story += [Spacer(1, 10), P("La posicion y orientacion de la herramienta se obtienen multiplicando:", styles["BodyX"]), code_block("T_0_6(q) = A_1(q1) A_2(q2) A_3(q3) A_4(q4) A_5(q5) A_6(q6)")]
story += [Spacer(1, 10), callout("Regla de defensa", "DH no se copia literalmente en origin porque el orden de operaciones de URDF es distinto. Primero hay que reordenar las transformaciones fijas respetando la igualdad matricial."), PageBreak()]

# 4
story += [P("4. Como se convierte DH a coordenadas que entiende ROS", styles["H1X"])]
story += [P("En DH clasico, la rotacion variable aparece antes de la transformacion fija de la fila:", styles["BodyX"]), code_block("A_i(q_i) = Rz(q_i) B_i,   donde B_i = Tz(d_i) Tx(a_i) Rx(alpha_i)")]
story += [Spacer(1, 7), P("En una junta URDF, origin se aplica primero y luego ROS gira alrededor del eje de la junta:", styles["BodyX"]), code_block("T_joint_i(q_i) = O_i Rz(q_i)")]
story += [Spacer(1, 7), P("Para conservar exactamente el producto total sin agregar joints fijos, la transformacion B_i de una fila se coloca en el origin de la junta siguiente. Los offsets constantes de theta se combinan en esos origins. Este corrimiento es valido porque se verifica el producto matricial completo.", styles["BodyX"])]
origins = [
    ["Junta", "origin xyz [m]", "origin rpy [rad]", "Eje"],
    ["joint_1", "0 0 0", "0 0 0", "0 0 1"],
    ["joint_2", "0 0 0.290", "-pi/2 -pi/2 0", "0 0 1"],
    ["joint_3", "0.270 0 0", "0 0 0", "0 0 1"],
    ["joint_4", "0.070 0 0", "-pi/2 0 0", "0 0 1"],
    ["joint_5", "0 0 0.302", "+pi/2 0 0", "0 0 1"],
    ["joint_6", "0 0.072 0", "+pi/2 0 pi", "0 0 1"],
]
story += [Spacer(1, 9), table(origins, [2.6 * cm, 4.2 * cm, 5.2 * cm, 3.7 * cm])]
story += [Spacer(1, 9), callout("Caso especial joint_6", "El desplazamiento final de 0.072 m puede quedar antes del giro q6 porque Tz(0.072) y Rz(q6) conmutan: ambos actuan sobre el mismo eje Z.", PALE_ORANGE)]
story += [Spacer(1, 8), P("La prueba definitiva no es que las tablas 'se parezcan': es que T_DH(q) y T_URDF(q) coincidan para muchas configuraciones.", styles["BodyX"]), PageBreak()]

# 5
story += [P("5. Como se calcula el error", styles["H1X"])]
story += [P("Se calculan dos caminos independientes para la misma configuracion q. El primer camino usa las seis matrices DH. El segundo recorre los seis joint/origin del URDF y aplica el giro de cada junta. Luego se comparan posicion y orientacion.", styles["BodyX"])]
story += [P("Error de posicion", styles["H2X"]), code_block("e_p = || p_DH - p_URDF ||_2")]
story += [P("Es la norma euclidiana de la diferencia entre los vectores XYZ, medida en metros.", styles["BodyX"])]
story += [P("Error de orientacion", styles["H2X"]), code_block(
    "R_rel = transpose(R_DH) R_URDF\n"
    "e_R = atan2( ||vee(R_rel - transpose(R_rel))|| / 2, (trace(R_rel) - 1) / 2 )"
)]
story += [P("e_R es el angulo geodesico entre ambas orientaciones, medido en radianes. Se usa atan2 para mantener estabilidad numerica cerca de cero.", styles["BodyX"])]
story += [Spacer(1, 8), table([
    ["Criterio", "Valor"],
    ["Tolerancia de posicion", "1.0e-6 m"],
    ["Maximo observado", "1.118863022828e-16 m"],
    ["Maximo angular observado", "4.209341455425e-16 rad"],
    ["Conclusion", "APROBADO, error de redondeo numerico"],
], [7.2 * cm, 8.5 * cm])]
story += [Spacer(1, 8), callout("Por que el error no es exactamente cero", "Los computadores representan numeros reales con precision finita. Un resultado del orden de 1e-16 es ruido de redondeo, aproximadamente diez mil millones de veces menor que la tolerancia de 1e-6 m.")]
story += [PageBreak()]

# 6
story += [P("6. Dos posturas escogidas y por que", styles["H1X"])]
story += [P("Las posturas no son arbitrarias. Una representa una configuracion de trabajo bien condicionada y la otra una configuracion plegada, cercana a la base, util para descubrir errores de signos, offsets y posibles interferencias geometricas.", styles["BodyX"])]
story += [P("Prueba A - postura de trabajo", styles["H2X"])]
story += [table([
    ["q1", "q2", "q3", "q4", "q5", "q6"],
    ["30 deg", "-20 deg", "15 deg", "40 deg", "-35 deg", "60 deg"],
], [2.62 * cm] * 6)]
story += [Spacer(1, 6), bullet("Todas las juntas tienen valores distintos de cero."), bullet("Evita la simetria de la postura cero y ejercita signos y offsets."), bullet("Representa una postura elevada de aproximacion o trabajo.")]
story += [table([
    ["Resultado", "Valor"],
    ["p_DH = p_URDF", "[0.237055, 0.106212, 0.676427] m"],
    ["Distancia radial a la base", "0.259762 m"],
    ["Error de posicion", "1.118863022828e-16 m"],
    ["Error de orientacion", "4.209341455425e-16 rad"],
], [6.0 * cm, 9.7 * cm])]
story += [Spacer(1, 10), P("Prueba B - postura plegada critica", styles["H2X"])]
story += [table([
    ["q1", "q2", "q3", "q4", "q5", "q6"],
    ["90 deg", "-60 deg", "60 deg", "90 deg", "60 deg", "180 deg"],
], [2.62 * cm] * 6)]
story += [Spacer(1, 6), bullet("Pliega el brazo cerca de la base: distancia radial de solo 0.121409 m."), bullet("Exige offsets de theta y orientaciones no triviales en las seis juntas."), bullet("Es una postura de riesgo geometrico y sirve para discutir colision sin afirmar una deteccion formal.")]
story += [table([
    ["Resultado", "Valor"],
    ["p_DH = p_URDF", "[-0.062354, 0.104173, 0.495000] m"],
    ["Distancia radial a la base", "0.121409 m"],
    ["Error de posicion", "1.022162900339e-16 m"],
    ["Error de orientacion", "1.605582592555e-16 rad"],
], [6.0 * cm, 9.7 * cm]), PageBreak()]

# 7
story += [P("7. Colisiones y fisica: que se puede afirmar", styles["H1X"])]
story += [P("La postura B fue elegida porque acerca la cadena al eje de la base y aumenta la posibilidad de interferencia entre eslabones. Sin embargo, una postura 'visualmente peligrosa' no equivale a una prueba formal de colision.", styles["BodyX"])]
story += [table([
    ["Pregunta", "Respuesta correcta para la defensa"],
    ["Hay deteccion de colision?", "No. El URDF final no contiene collision y RViz no es un motor de colisiones."],
    ["Por que se elimino collision?", "No se dispone aun del CAD/mesh validado y el Hito 1 evalua principalmente cinematica y estructura."],
    ["Por que se elimino inertial?", "No se ejecuta una simulacion dinamica. Masa e inercia sin respaldo CAD agregaban datos no defendibles."],
    ["Que hace falta para detectar?", "Mallas o primitivas collision, modelo propio y entorno; luego usar MoveIt 2 o un simulador con motor fisico."],
    ["Que si demuestra la postura B?", "Que la cinematica DH y URDF coinciden tambien en una configuracion plegada y numericamente exigente."],
], [5.2 * cm, 10.5 * cm])]
story += [Spacer(1, 10), callout("Frase segura", "'Seleccionamos una postura plegada como caso critico geometrico. No reportamos colision certificada porque aun no existe geometria collision validada. La prueba actual valida la cinematica en esa region.'", PALE_ORANGE)]
story += [Spacer(1, 10), P("Cuando llegue el CAD", styles["H2X"]), bullet("Preferir STEP o IGES como fuente mecanica para revisar y separar piezas."), bullet("Exportar una malla por eslabon a STL o DAE, con unidades en metros y origen coherente con su joint."), bullet("Usar mallas simplificadas para collision y mallas visuales para RViz."), bullet("No unir las seis piezas en una sola malla: cada link debe moverse por separado."), PageBreak()]

# 8
story += [P("8. Como funciona el proyecto ROS 2", styles["H1X"])]
story += [P("ROS 2 conecta programas pequenos llamados nodos. Los nodos intercambian mensajes por topics. En esta demostracion, la interfaz de deslizadores publica posiciones articulares, el publicador de estado entrega JointState, robot_state_publisher calcula TF y RViz muestra el robot.", styles["BodyX"])]
story += [code_block(
    "Deslizadores / movimiento automatico\n"
    "              |\n"
    "              v\n"
    "      joint_state_source  ---> /joint_states\n"
    "                                      |\n"
    "                                      v\n"
    "                         robot_state_publisher ---> /tf ---> RViz\n"
    "                                      |\n"
    "                                      +----> fk_validator (compara DH y URDF)"
)]
story += [Spacer(1, 10), table([
    ["Componente", "Responsabilidad"],
    ["joint_state_source", "Mantiene y publica q1...q6"],
    ["slider_gui", "Ofrece una barra para cada junta"],
    ["robot_state_publisher", "Convierte q + URDF en transformaciones TF"],
    ["RViz", "Visualiza RobotModel y marcos TF"],
    ["fk_validator", "Calcula error DH frente a TF/URDF"],
    ["verify_model", "Prueba estatica sin abrir RViz"],
], [5.3 * cm, 10.4 * cm])]
story += [Spacer(1, 10), P("Carpetas principales", styles["H2X"]), code_block(
    "ros2_ws/src/irb120_hito1/\n"
    "  urdf/        modelo xacro y URDF generado\n"
    "  launch/      arranque coordinado\n"
    "  config/      parametros y RViz\n"
    "  irb120_hito1/ nodos Python y cinematica\n"
    "  test/        pruebas automatizadas\n"
    "docs/hito1/    explicacion y guion de defensa"
), PageBreak()]

# 9
story += [P("9. Preparacion manual desde una terminal nueva", styles["H1X"])]
story += [P("Estos pasos no usan el script auxiliar. Debes repetir source en cada terminal nueva porque source modifica solo la sesion actual.", styles["BodyX"])]
story += [P("Paso 1 - entrar al proyecto", styles["H2X"]), code_block(
    "cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto"
)]
story += [P("Paso 2 - cargar ROS 2", styles["H2X"]), code_block("source /opt/ros/jazzy/setup.bash")]
story += [P("Paso 3 - compilar", styles["H2X"]), code_block(
    "cd ros2_ws\ncolcon build --symlink-install --packages-select irb120_hito1"
)]
story += [P("Paso 4 - cargar el paquete compilado", styles["H2X"]), code_block("source install/setup.bash")]
story += [P("Paso 5 - verificacion rapida", styles["H2X"]), code_block("ros2 run irb120_hito1 verify_model")]
story += [P("La ultima linea debe indicar APROBADO y un error maximo mucho menor que 1e-6 m.", styles["BodyX"])]
story += [P("Paso 6 - ejecutar pruebas", styles["H2X"]), code_block(
    "colcon test --packages-select irb120_hito1\ncolcon test-result --verbose"
)]
story += [P("El resultado esperado es 12 tests, 0 errores y 0 fallos.", styles["BodyX"])]
story += [callout("Si ROS no reconoce el paquete", "Comprueba que estas dentro de ros2_ws y que ejecutaste source /opt/ros/jazzy/setup.bash antes de compilar, y source install/setup.bash despues de compilar.", PALE_ORANGE), PageBreak()]

# 10
story += [P("10. Demostracion grafica para el docente", styles["H1X"])]
story += [P("Primero cierra cualquier demostracion antigua con Ctrl+C. Si dejas una instancia vieja, podrias ver el modelo anterior aunque los archivos nuevos esten correctos.", styles["BodyX"])]
story += [P("Terminal unica - abrir RViz y deslizadores", styles["H2X"]), code_block(
    "cd /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws\n"
    "source /opt/ros/jazzy/setup.bash\n"
    "source install/setup.bash\n"
    "ros2 launch irb120_hito1 display.launch.py"
)]
story += [Spacer(1, 7), bullet("Se abre RViz con el modelo y una ventana con 6 barras."), bullet("Mueve una barra lentamente y observa el eslabon correspondiente."), bullet("Activa TF en RViz para enseñar los seis marcos moviles y base_link."), bullet("El validador imprime APROBADO mientras cambian las juntas.")]
story += [P("Demostracion automatica, opcional", styles["H2X"]), code_block(
    "ros2 launch irb120_hito1 display.launch.py demo_motion:=true use_slider_gui:=false"
)]
story += [P("Inspecciones utiles en otra terminal", styles["H2X"]), code_block(
    "source /opt/ros/jazzy/setup.bash\n"
    "source /home/marcelo767/Documentos/robotica/robotica-IMT342/2-2026/IMT342/equipo/proyecto/ros2_ws/install/setup.bash\n"
    "ros2 node list\n"
    "ros2 topic list\n"
    "ros2 topic echo /joint_states --once\n"
    "ros2 run tf2_tools view_frames"
)]
story += [Spacer(1, 7), callout("Orden recomendado ante el docente", "1) verify_model, 2) colcon test-result, 3) abrir RViz, 4) mover cada slider, 5) mostrar TF, 6) explicar una postura de trabajo y la postura plegada."), PageBreak()]

# 11
story += [P("11. Lista para rellenar la validacion del examen", styles["H1X"])]
joint_rows = [["Junta", "Padre", "Hijo", "Tipo", "Eje"]]
parents = ["base_link", "link_1", "link_2", "link_3", "link_4", "link_5"]
children = ["link_1", "link_2", "link_3", "link_4", "link_5", "tool0"]
for i in range(6):
    joint_rows.append([f"joint_{i+1}", parents[i], children[i], "revolute", "0 0 1"])
story += [table(joint_rows, [2.5 * cm, 3.5 * cm, 3.5 * cm, 3.1 * cm, 3.1 * cm])]
story += [Spacer(1, 10), table([
    ["Comprobacion", "Resultado esperado", "Como demostrarlo"],
    ["URDF valido", "Sin errores de parser", "check_urdf sobre el URDF generado"],
    ["Arbol", "Serial, 6 joints", "RobotModel/TF o salida check_urdf"],
    ["Movimiento", "6 GDL independientes", "Una barra por junta"],
    ["DH frente a ROS", "e_p < 1e-6 m", "verify_model y fk_validator"],
    ["Pruebas", "12 aprobadas", "colcon test-result --verbose"],
    ["Fisica", "Fuera de alcance", "0 inertial y 0 collision"],
], [3.8 * cm, 4.4 * cm, 7.5 * cm])]
story += [Spacer(1, 10), P("Comando para ver la estructura del URDF", styles["H2X"]), code_block(
    "xacro ros2_ws/src/irb120_hito1/urdf/irb120.urdf.xacro > /tmp/irb120.urdf\n"
    "check_urdf /tmp/irb120.urdf"
)]
story += [Spacer(1, 8), P("Que debe observar el docente", styles["H2X"]), bullet("No aparecen theta_frame ni dh_frame."), bullet("No existe una junta de pinza."), bullet("tool0 es el sexto marco movil y extremo de la cadena."), bullet("Cada movimiento conserva continuidad y el error sigue aprobado."), PageBreak()]

# 12
story += [P("12. Preguntas probables de defensa", styles["H1X"])]
qa = [
    ("Por que hay 7 links si se pidieron 6 marcos?", "Porque base_link es la raiz fija. Los seis marcos moviles corresponden a las seis articulaciones: link_1...link_5 y tool0."),
    ("Por que todos los ejes son Z?", "La convencion DH define cada articulacion rotacional alrededor de su eje z local. Los origin orientan ese eje local en el espacio."),
    ("Como ingresaron DH en ROS?", "Se factoriza cada fila A_i = Rz(q_i)B_i y se desplaza B_i al origin de la junta siguiente, combinando los offsets constantes. Luego se valida el producto completo."),
    ("Que significa rpy?", "Roll, pitch, yaw: rotaciones fijas usadas por origin para orientar el marco hijo antes del giro variable."),
    ("Que representa el error?", "La distancia entre posiciones DH y URDF; y el angulo relativo entre sus orientaciones."),
    ("Por que eligieron esas dos poses?", "La A ejercita las seis juntas en trabajo normal; la B pliega el brazo cerca de la base y es sensible a errores de signos, offsets y riesgo geometrico."),
    ("RViz simula fisica?", "No. RViz visualiza mensajes y transformaciones. La fisica requiere Gazebo u otro simulador y parametros dinamicos confiables."),
    ("Que falta para el gemelo digital completo?", "CAD separado por eslabon, mallas visuales y de colision, masas/inercia verificadas, controladores y validacion contra el robot real."),
]
for q, a in qa:
    story.append(KeepTogether([P(q, styles["H2X"]), P(a, styles["BodyX"]), Spacer(1, 3)]))
story += [Spacer(1, 6), callout("Idea central", "El Hito 1 queda cerrado como modelo cinematico defendible: seis juntas, conversion matematica explicita y equivalencia numerica demostrada."), PageBreak()]

# 13
story += [P("13. Archivos clave y cierre", styles["H1X"])]
story += [table([
    ["Archivo", "Que contiene"],
    ["urdf/irb120.macro.xacro", "Links, seis joints, limites y visuales provisionales"],
    ["urdf/irb120.urdf.xacro", "Punto de entrada Xacro"],
    ["urdf/irb120.urdf", "URDF expandido para inspeccion"],
    ["kinematics/dh.py", "Cinematica directa DH"],
    ["kinematics/urdf_chain.py", "Cinematica calculada desde origins URDF"],
    ["verify_model.py", "Dos posturas justificadas y reporte de error"],
    ["fk_validator.py", "Validacion continua durante la demostracion"],
    ["slider_gui.py", "Seis barras de control"],
    ["test/", "Doce verificaciones automaticas"],
], [6.2 * cm, 9.5 * cm])]
story += [Spacer(1, 12), P("Estado final del Hito 1", styles["H2X"])]
story += [bullet("Modelo serial minimo de 6 GDL: completado."), bullet("Parametros DH y conversion a URDF: documentados."), bullet("Error de posicion y orientacion: calculado y por debajo de tolerancia."), bullet("Dos posturas justificadas: documentadas."), bullet("Interfaz grafica de seis barras: implementada."), bullet("Pruebas y lanzamiento ROS 2: aprobados.")]
story += [Spacer(1, 12), callout("Pendiente futuro, no bloquea el examen", "Recibir el CAD del ABB IRB 120, separar una malla por eslabon y validar escalas/origenes. Despues podran añadirse colisiones, dinamica y control para avanzar hacia un gemelo digital completo.", PALE_ORANGE)]
story += [Spacer(1, 14), P("Referencias de trabajo", styles["H2X"]), P("Guia PFI y worksheet de validacion proporcionados por el estudiante; documentacion tecnica ABB IRB 120 y articulos de referencia incluidos en el proyecto; implementacion y pruebas locales del paquete irb120_hito1.", styles["SmallX"])]

doc.build(story)
print(OUT)
