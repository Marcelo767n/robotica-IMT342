import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

process.on("uncaughtException", (error) => {
  const stack = String(error?.stack ?? "").split("\n").slice(0, 12).join("\n");
  console.error("DECK_BUILD_ERROR", error?.name, error?.message, stack);
  process.exit(1);
});
process.on("unhandledRejection", (error) => {
  const stack = String(error?.stack ?? "").split("\n").slice(0, 12).join("\n");
  console.error("DECK_BUILD_REJECTION", error?.name, error?.message, stack);
  process.exit(1);
});

const workspaceDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const SKILL_DIR = "/home/marcelo767/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const TMP_DIR = path.join(workspaceDir, "archivo", "hito1", "generacion", "presentation_corrected");
const FINAL_PPTX = path.join(workspaceDir, "entregables", "hito1", "presentation", "Defensa_Hito1_IRB120_6_Juntas_FINAL.pptx");
const RUNTIME_PYTHON = "/home/marcelo767/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3.12";

const { finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href,
);

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const W = 1280;
const H = 720;
const FONT = "Liberation Sans";
const MONO = "Liberation Mono";
const NAVY = "#132238";
const ORANGE = "#F28C28";
const TEAL = "#167D8D";
const GREEN = "#2E8B57";
const RED = "#B43A3A";
const INK = "#202733";
const MUTED = "#5B6675";
const PAPER = "#F7F5F0";
const WHITE = "#FFFFFF";
const PALE = "#EEF1F4";
const PALE_BLUE = "#EAF6F7";
const PALE_ORANGE = "#FFF1DF";
const GRID = "#B4BEC8";

const pres = Presentation.create({ slideSize: { width: W, height: H } });

function addText(slide, text, x, y, w, h, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: opts.fill ?? "none",
    line: opts.line ?? { fill: "none", width: 0 },
    borderRadius: opts.borderRadius,
  });
  shape.text = text;
  shape.text.style = {
    typeface: opts.typeface ?? FONT,
    fontSize: opts.size ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? INK,
    alignment: opts.align ?? "left",
    verticalAlignment: opts.valign ?? "top",
    autoFit: opts.autoFit ?? "shrinkText",
    wrap: "square",
    insets: opts.insets ?? { top: 5, right: 7, bottom: 5, left: 7 },
    lineSpacing: opts.lineSpacing ?? 1.0,
  };
  return shape;
}

function addRect(slide, x, y, w, h, fill, opts = {}) {
  const geometry = opts.geometry ?? "rect";
  const config = {
    geometry,
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: opts.line ?? { fill: "none", width: 0 },
    shadow: opts.shadow,
  };
  if (opts.radius !== undefined && ["rect", "textbox", "roundRect"].includes(geometry)) {
    config.borderRadius = opts.radius;
  }
  return slide.shapes.add(config);
}

function addCircle(slide, x, y, d, fill, lineFill = NAVY) {
  return slide.shapes.add({
    geometry: "ellipse",
    position: { left: x, top: y, width: d, height: d },
    fill,
    line: { style: "solid", fill: lineFill, width: 2 },
  });
}

function addTopBars(slide) {
  addRect(slide, 0, 0, 205, 14, ORANGE);
  addRect(slide, 205, 0, W - 205, 14, NAVY);
}

function addFooter(slide, number, label = "IMT-342 | Hito 1 | ABB IRB 120") {
  addText(slide, label, 56, 681, 520, 20, { size: 12, color: MUTED, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, String(number).padStart(2, "0"), 1170, 680, 54, 22, { size: 12, bold: true, color: ORANGE, align: "right", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
}

function baseSlide(number, title, kicker = "MODELO CORREGIDO") {
  const slide = pres.slides.add();
  slide.background.fill = PAPER;
  addTopBars(slide);
  addText(slide, kicker, 55, 32, 350, 26, { size: 13, bold: true, color: ORANGE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, title, 55, 62, 1160, 55, { size: 33, bold: true, color: NAVY, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addRect(slide, 55, 123, 1168, 2, "#D4DAE0");
  addFooter(slide, number);
  return slide;
}

function card(slide, x, y, w, h, title, body, accent = TEAL) {
  addRect(slide, x, y, w, h, WHITE, { radius: 14, line: { style: "solid", fill: "#D1D8DF", width: 1 }, shadow: "shadow-sm" });
  addRect(slide, x, y, 8, h, accent, { radius: 8 });
  addText(slide, title, x + 22, y + 15, w - 36, 36, { size: 21, bold: true, color: NAVY, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, body, x + 22, y + 57, w - 36, h - 68, { size: 16, color: INK, lineSpacing: 1.08, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
}

function addNote(slide, text) {
  slide.speakerNotes.textFrame.setText(text);
}

function addNativeTable(slide, data, x, y, w, h, widths = null, bodySize = 15) {
  const table = slide.tables.add({
    rows: data.length,
    columns: data[0].length,
    left: x,
    top: y,
    width: w,
    height: h,
    values: data,
    ...(widths ? { columnWidths: widths } : {}),
  });
  table.borders.assign({ style: "solid", fill: GRID, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: data[0].length }).assign({
    fill: NAVY,
    textStyle: { typeface: FONT, fontSize: bodySize, bold: true, color: WHITE, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText" },
    margins: { top: 5, right: 5, bottom: 5, left: 5 },
    anchor: "middle",
  });
  if (data.length > 1) {
    table.cells.block({ row: 1, column: 0, rowCount: data.length - 1, columnCount: data[0].length }).assign({
      fill: WHITE,
      textStyle: { typeface: FONT, fontSize: bodySize, color: INK, alignment: "center", verticalAlignment: "middle", autoFit: "shrinkText" },
      margins: { top: 4, right: 5, bottom: 4, left: 5 },
      anchor: "middle",
    });
  }
  for (let r = 2; r < data.length; r += 2) {
    table.cells.block({ row: r, column: 0, rowCount: 1, columnCount: data[0].length }).fill = PALE;
  }
  return table;
}

// 1. Cover
{
  const slide = pres.slides.add();
  slide.background.fill = NAVY;
  addRect(slide, 0, 0, W, 18, ORANGE);
  addRect(slide, 0, 18, 18, H - 18, ORANGE);
  addText(slide, "IMT-342 | PROYECTO FINAL", 76, 70, 530, 30, { size: 17, bold: true, color: ORANGE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "ABB IRB 120\nen ROS 2", 75, 135, 720, 180, { size: 56, bold: true, color: WHITE, lineSpacing: 0.92, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "Hito 1 corregido: seis juntas, conversion DH a URDF y validacion numerica", 78, 335, 730, 78, { size: 23, color: "#DCE5EF", lineSpacing: 1.1, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addRect(slide, 850, 115, 340, 390, "#1B304B", { radius: 22, line: { style: "solid", fill: "#2B4666", width: 1 } });
  addText(slide, "6", 900, 155, 240, 95, { size: 76, bold: true, color: ORANGE, align: "center", valign: "middle" });
  addText(slide, "juntas revolutas\n6 marcos moviles\n0 juntas fijas", 890, 260, 260, 145, { size: 24, bold: true, color: WHITE, align: "center", valign: "middle", lineSpacing: 1.18 });
  addText(slide, "12 pruebas aprobadas\nerror max. 1.12e-16 m", 890, 420, 260, 60, { size: 17, color: "#BFE9DD", align: "center", valign: "middle" });
  addText(slide, "Modelo cinematico defendible | Version para examen", 77, 636, 720, 30, { size: 16, color: "#AFC0D4", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addNote(slide, "Fuente: implementacion local del paquete irb120_hito1 y resultados de sus pruebas automatizadas.");
}

// 2. Scope
{
  const slide = baseSlide(2, "Que se corrigio y que entrega el Hito 1");
  card(slide, 55, 155, 555, 205, "Arbol minimo", "base_link como raiz y seis transformaciones variables. No existen theta_frame, dh_frame ni joints fijos.", TEAL);
  card(slide, 640, 155, 583, 205, "Cinematica demostrada", "La tabla DH clasica y la cadena URDF producen la misma posicion y orientacion para las configuraciones probadas.", GREEN);
  card(slide, 55, 390, 555, 205, "Sin fisica inventada", "Se eliminaron inertial y collision porque aun no existe CAD validado ni simulacion dinamica en el alcance.", ORANGE);
  card(slide, 640, 390, 583, 205, "Demostracion sencilla", "RViz muestra el brazo y una interfaz ofrece una barra por cada una de las seis juntas.", NAVY);
  addText(slide, "CAD pendiente: no bloquea la evaluacion cinematica del Hito 1.", 55, 620, 1168, 34, { size: 18, bold: true, color: TEAL, align: "center", valign: "middle", fill: PALE_BLUE, line: { style: "solid", fill: "#B9DDE2", width: 1 }, borderRadius: 8 });
  addNote(slide, "Alcance basado en la Guia PFI y el worksheet de validacion entregados por el estudiante.");
}

// 3. ROS architecture
{
  const slide = baseSlide(3, "Como fluye la informacion en ROS 2", "ARQUITECTURA");
  const boxes = [];
  const labels = [
    ["6 deslizadores", "q1 ... q6"],
    ["joint_state_source", "/joint_states"],
    ["robot_state_publisher", "URDF + q"],
    ["TF", "transformaciones"],
    ["RViz", "RobotModel"],
  ];
  const xs = [50, 292, 535, 786, 1025];
  const widths = [190, 205, 205, 185, 190];
  for (let i = 0; i < labels.length; i++) {
    const b = addRect(slide, xs[i], 238, widths[i], 135, i === 4 ? PALE_BLUE : WHITE, { radius: 15, line: { style: "solid", fill: i === 4 ? TEAL : "#C7D0D9", width: 1.5 }, shadow: "shadow-sm" });
    boxes.push(b);
    addText(slide, labels[i][0], xs[i] + 12, 256, widths[i] - 24, 48, { size: i === 2 ? 17 : 20, bold: true, color: NAVY, align: "center", valign: "middle" });
    addText(slide, labels[i][1], xs[i] + 12, 310, widths[i] - 24, 36, { size: 16, color: MUTED, align: "center", valign: "middle" });
    if (i < labels.length - 1) addRect(slide, xs[i] + widths[i] + 10, 285, 34, 28, ORANGE, { geometry: "rightArrow" });
  }
  addRect(slide, 535, 430, 205, 112, PALE_ORANGE, { radius: 14, line: { style: "solid", fill: ORANGE, width: 1.5 } });
  addText(slide, "fk_validator", 550, 445, 175, 32, { size: 20, bold: true, color: NAVY, align: "center", valign: "middle" });
  addText(slide, "compara DH vs URDF", 550, 481, 175, 34, { size: 15, color: INK, align: "center", valign: "middle" });
  addText(slide, "El validador observa la misma cadena que ve RViz y publica APROBADO mientras el brazo se mueve.", 315, 575, 650, 55, { size: 20, bold: true, color: TEAL, align: "center", valign: "middle" });
  addNote(slide, "Arquitectura derivada de launch/display.launch.py y de los nodos del paquete irb120_hito1.");
}

// 4. Files
{
  const slide = baseSlide(4, "Paquete modular y archivos que quedaron", "ORGANIZACION");
  addRect(slide, 55, 155, 580, 470, NAVY, { radius: 18 });
  addText(slide,
    "irb120_hito1/\n\n  urdf/\n    irb120.macro.xacro\n    irb120.urdf.xacro\n    irb120.urdf\n\n  launch/\n    display.launch.py\n\n  config/\n    irb120.rviz\n\n  irb120_hito1/\n    kinematics/\n    slider_gui.py\n    joint_state_source.py\n    fk_validator.py\n    verify_model.py\n\n  test/",
    85, 185, 510, 410,
    { typeface: MONO, size: 16, color: "#E8EEF5", lineSpacing: 0.96, insets: { top: 0, left: 0, right: 0, bottom: 0 } },
  );
  card(slide, 675, 155, 548, 130, "Eliminado", "gripper.macro.xacro y la junta de pinza", RED);
  card(slide, 675, 305, 548, 130, "Eliminado", "theta_*_frame, dh_*_frame y joints fijos", RED);
  card(slide, 675, 455, 548, 170, "Separacion clara", "URDF describe la cadena; kinematics calcula; los nodos ROS publican y validan; test comprueba la estructura.", TEAL);
  addNote(slide, "Fuente: estructura actual del repositorio, carpeta ros2_ws/src/irb120_hito1.");
}

// 5. DH table
{
  const slide = baseSlide(5, "Tabla Denavit-Hartenberg clasica", "MODELO MATEMATICO");
  addText(slide, "A_i = Rz(theta_i) Tz(d_i) Tx(a_i) Rx(alpha_i)", 55, 142, 1168, 50, { typeface: MONO, size: 24, bold: true, color: TEAL, align: "center", valign: "middle", fill: PALE_BLUE, line: { style: "solid", fill: "#B9DDE2", width: 1 }, borderRadius: 8 });
  addNativeTable(slide, [
    ["i", "theta_i", "d_i [m]", "a_i [m]", "alpha_i"],
    ["1", "q1", "0.290", "0", "-pi/2"],
    ["2", "q2 - pi/2", "0", "0.270", "0"],
    ["3", "q3", "0", "0.070", "-pi/2"],
    ["4", "q4", "0.302", "0", "+pi/2"],
    ["5", "q5", "0", "0", "-pi/2"],
    ["6", "q6 + pi", "0.072", "0", "0"],
  ], 110, 220, 1060, 330, [110, 290, 210, 210, 240], 18);
  addText(slide, "Unidades: metros y radianes. Cada q_i es el angulo variable de una junta.", 110, 575, 1060, 48, { size: 19, color: INK, align: "center", valign: "middle" });
  addNote(slide, "Fuente: tabla DH usada por kinematics/dh.py y documentada en docs/hito1/modelo_cinematico.md.");
}

// 6. DH to URDF
{
  const slide = pres.slides.add();
  slide.background.fill = NAVY;
  addRect(slide, 0, 0, 215, 14, ORANGE);
  addRect(slide, 215, 0, W - 215, 14, "#263B55");
  addText(slide, "CONVERSION CLAVE", 58, 40, 400, 28, { size: 14, bold: true, color: ORANGE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "DH no se copia fila por fila en origin", 58, 76, 1120, 58, { size: 38, bold: true, color: WHITE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "En DH clasico", 78, 180, 330, 40, { size: 21, bold: true, color: ORANGE, align: "center" });
  addText(slide, "A_i(q_i) = Rz(q_i) B_i", 62, 230, 365, 80, { typeface: MONO, size: 25, bold: true, color: WHITE, align: "center", valign: "middle", fill: "#1B304B", line: { style: "solid", fill: "#38516F", width: 1 }, borderRadius: 12 });
  addRect(slide, 448, 250, 100, 42, ORANGE, { geometry: "rightArrow" });
  addText(slide, "En URDF", 575, 180, 330, 40, { size: 21, bold: true, color: ORANGE, align: "center" });
  addText(slide, "T_i(q_i) = O_i Rz(q_i)", 555, 230, 375, 80, { typeface: MONO, size: 25, bold: true, color: WHITE, align: "center", valign: "middle", fill: "#1B304B", line: { style: "solid", fill: "#38516F", width: 1 }, borderRadius: 12 });
  addRect(slide, 950, 250, 100, 42, ORANGE, { geometry: "rightArrow" });
  addText(slide, "Mover B_i al\norigin siguiente", 1064, 222, 155, 96, { size: 20, bold: true, color: WHITE, align: "center", valign: "middle", fill: TEAL, borderRadius: 12 });
  addText(slide, "B_i = Tz(d_i) Tx(a_i) Rx(alpha_i)", 240, 355, 800, 54, { typeface: MONO, size: 25, color: "#C9D6E5", align: "center", valign: "middle" });
  addText(slide, "Resultado: la misma matriz T_0_6 con solo seis joints", 150, 447, 980, 72, { size: 30, bold: true, color: WHITE, align: "center", valign: "middle", fill: "#223B59", line: { style: "solid", fill: "#365777", width: 1.5 }, borderRadius: 16 });
  addText(slide, "Los offsets -pi/2 y +pi se combinan en los RPY de los origin. La igualdad se verifica numericamente.", 155, 550, 970, 70, { size: 20, color: "#DCE5EF", align: "center", valign: "middle" });
  addText(slide, "06", 1164, 674, 60, 22, { size: 12, bold: true, color: ORANGE, align: "right", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addNote(slide, "Derivacion completa: docs/hito1/modelo_cinematico.md. La equivalencia se comprueba contra la cadena URDF real.");
}

// 7. Origin table
{
  const slide = baseSlide(7, "Coordenadas joint/origin usadas por ROS", "DH A URDF");
  addNativeTable(slide, [
    ["Junta", "origin xyz [m]", "origin rpy [rad]", "axis"],
    ["joint_1", "0  0  0", "0  0  0", "0 0 1"],
    ["joint_2", "0  0  0.290", "-pi/2  -pi/2  0", "0 0 1"],
    ["joint_3", "0.270  0  0", "0  0  0", "0 0 1"],
    ["joint_4", "0.070  0  0", "-pi/2  0  0", "0 0 1"],
    ["joint_5", "0  0  0.302", "+pi/2  0  0", "0 0 1"],
    ["joint_6", "0  0.072  0", "+pi/2  0  pi", "0 0 1"],
  ], 80, 170, 1120, 355, [200, 310, 420, 190], 17);
  addText(slide, "Por que axis = 0 0 1 en todas", 80, 555, 440, 38, { size: 22, bold: true, color: TEAL, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "DH define cada giro alrededor del eje z local; los RPY orientan ese z local en el espacio.", 80, 598, 850, 55, { size: 18, color: INK, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "joint_6: Tz(0.072) y Rz(q6) conmutan", 945, 552, 255, 84, { size: 16, bold: true, color: NAVY, align: "center", valign: "middle", fill: PALE_ORANGE, line: { style: "solid", fill: ORANGE, width: 1 }, borderRadius: 10 });
  addNote(slide, "Fuente: origins definidos en urdf/irb120.macro.xacro y validados en test/test_kinematics.py.");
}

// 8. Tree
{
  const slide = baseSlide(8, "Arbol jerarquico: seis marcos moviles", "TF / URDF");
  const labels = ["base_link", "link_1", "link_2", "link_3", "link_4", "link_5", "tool0"];
  const colors = [NAVY, "#E4EEF4", "#E4EEF4", "#E4EEF4", "#E4EEF4", "#E4EEF4", PALE_ORANGE];
  const xs = [48, 221, 394, 567, 740, 913, 1086];
  for (let i = 0; i < labels.length; i++) {
    addCircle(slide, xs[i], 245, 125, colors[i], i === 6 ? ORANGE : NAVY);
    addText(slide, labels[i], xs[i] + 8, 283, 109, 48, { size: 18, bold: true, color: i === 0 ? WHITE : NAVY, align: "center", valign: "middle", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
    if (i < labels.length - 1) {
      addRect(slide, xs[i] + 128, 288, 39, 26, ORANGE, { geometry: "rightArrow" });
      addText(slide, `joint_${i + 1}`, xs[i] + 118, 327, 62, 28, { size: 12, bold: true, color: MUTED, align: "center", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
    }
  }
  addText(slide, "7 links totales", 180, 450, 245, 72, { size: 31, bold: true, color: NAVY, align: "center", valign: "middle", fill: WHITE, line: { style: "solid", fill: "#D1D8DF", width: 1 }, borderRadius: 14 });
  addText(slide, "6 joints revolute", 515, 450, 245, 72, { size: 31, bold: true, color: TEAL, align: "center", valign: "middle", fill: PALE_BLUE, line: { style: "solid", fill: "#B9DDE2", width: 1 }, borderRadius: 14 });
  addText(slide, "0 joints fixed", 850, 450, 245, 72, { size: 31, bold: true, color: GREEN, align: "center", valign: "middle", fill: "#EAF6EF", line: { style: "solid", fill: "#B8DCC6", width: 1 }, borderRadius: 14 });
  addText(slide, "base_link no es una septima articulacion: es la raiz fija que ROS necesita.", 170, 565, 940, 55, { size: 21, bold: true, color: NAVY, align: "center", valign: "middle" });
  addNote(slide, "Estructura comprobada con check_urdf y con test_model_has_exact_six_joint_serial_tree.");
}

// 9. Origins and physics
{
  const slide = baseSlide(9, "Tres conceptos que no deben confundirse", "URDF");
  card(slide, 55, 175, 360, 350, "joint/origin", "Define la transformacion cinematica padre-hijo. Sus xyz y rpy si afectan la posicion y orientacion de los marcos TF.", TEAL);
  card(slide, 460, 175, 360, 350, "visual/origin", "Mueve solamente el cilindro, la caja o la esfera para centrar el dibujo. No crea marcos TF ni cambia la cinematica.", ORANGE);
  card(slide, 865, 175, 358, 350, "inertial/origin", "Ubicaria el centro de masa para dinamica. Fue eliminado porque no existe una simulacion fisica ni datos CAD validados.", RED);
  addText(slide, "En la version final: 0 <inertial> y 0 <collision>", 210, 565, 860, 58, { typeface: MONO, size: 25, bold: true, color: WHITE, align: "center", valign: "middle", fill: NAVY, borderRadius: 12 });
  addNote(slide, "La geometria visual provisional no altera los frames. La fisica queda fuera del alcance de este Hito 1.");
}

// 10. Error
{
  const slide = baseSlide(10, "Como calculamos el error DH frente a URDF", "VALIDACION");
  card(slide, 55, 160, 505, 155, "Camino 1", "T_DH(q): producto de las seis matrices Denavit-Hartenberg.", TEAL);
  card(slide, 720, 160, 503, 155, "Camino 2", "T_URDF(q): origins del XML seguidos por Rz(q_i).", ORANGE);
  addRect(slide, 581, 208, 118, 58, ORANGE, { geometry: "rightArrow" });
  addText(slide, "comparar", 580, 270, 120, 32, { size: 15, bold: true, color: MUTED, align: "center" });
  addText(slide, "Error de posicion", 85, 365, 300, 35, { size: 22, bold: true, color: TEAL });
  addText(slide, "e_p = || p_DH - p_URDF ||_2", 85, 410, 510, 70, { typeface: MONO, size: 25, bold: true, color: NAVY, align: "center", valign: "middle", fill: PALE_BLUE, borderRadius: 10 });
  addText(slide, "Error de orientacion", 685, 365, 330, 35, { size: 22, bold: true, color: ORANGE });
  addText(slide, "R_rel = R_DH^T R_URDF\ne_R = angulo(R_rel)", 685, 410, 510, 70, { typeface: MONO, size: 23, bold: true, color: NAVY, align: "center", valign: "middle", fill: PALE_ORANGE, borderRadius: 10 });
  addText(slide, "Tolerancia", 165, 545, 260, 35, { size: 18, bold: true, color: MUTED, align: "center" });
  addText(slide, "1e-6 m", 165, 580, 260, 55, { size: 32, bold: true, color: NAVY, align: "center", valign: "middle" });
  addText(slide, "Maximo medido", 510, 545, 260, 35, { size: 18, bold: true, color: MUTED, align: "center" });
  addText(slide, "1.12e-16 m", 510, 580, 260, 55, { size: 32, bold: true, color: GREEN, align: "center", valign: "middle" });
  addText(slide, "Conclusion", 855, 545, 260, 35, { size: 18, bold: true, color: MUTED, align: "center" });
  addText(slide, "APROBADO", 855, 580, 260, 55, { size: 32, bold: true, color: GREEN, align: "center", valign: "middle" });
  addNote(slide, "Formula implementada en kinematics/urdf_chain.py y mostrada por verify_model.py. El valor observado es error de redondeo numerico.");
}

// 11. Pose A
{
  const slide = baseSlide(11, "Prueba A: postura de trabajo", "DOS PRUEBAS JUSTIFICADAS");
  addText(slide, "q = [30, -20, 15, 40, -35, 60] grados", 60, 155, 1160, 58, { typeface: MONO, size: 26, bold: true, color: NAVY, align: "center", valign: "middle", fill: PALE_BLUE, borderRadius: 10 });
  card(slide, 55, 245, 540, 270, "Por que se eligio", "• Las seis juntas son distintas de cero.\n• Evita la simetria de la postura cero.\n• Ejercita signos y offsets.\n• Representa aproximacion elevada de trabajo.", TEAL);
  card(slide, 625, 245, 598, 270, "Resultado", "p = [0.237055, 0.106212, 0.676427] m\n\nDistancia radial = 0.259762 m\n\ne_p = 1.118863e-16 m\ne_R = 4.209341e-16 rad", GREEN);
  addText(slide, "Esta pose comprueba una configuracion general, no una coincidencia accidental en q = 0.", 135, 560, 1010, 58, { size: 22, bold: true, color: NAVY, align: "center", valign: "middle", fill: WHITE, line: { style: "solid", fill: "#D1D8DF", width: 1 }, borderRadius: 10 });
  addNote(slide, "Resultados generados por ros2 run irb120_hito1 verify_model.");
}

// 12. Pose B
{
  const slide = baseSlide(12, "Prueba B: postura plegada critica", "DOS PRUEBAS JUSTIFICADAS");
  addText(slide, "q = [90, -60, 60, 90, 60, 180] grados", 60, 155, 1160, 58, { typeface: MONO, size: 26, bold: true, color: NAVY, align: "center", valign: "middle", fill: PALE_ORANGE, borderRadius: 10 });
  card(slide, 55, 245, 540, 270, "Por que se eligio", "• Pliega la cadena cerca del eje de la base.\n• Es sensible a signos y offsets.\n• Explora una region de riesgo geometrico.\n• Todas las juntas participan.", ORANGE);
  card(slide, 625, 245, 598, 270, "Resultado", "p = [-0.062354, 0.104173, 0.495000] m\n\nDistancia radial = 0.121409 m\n\ne_p = 1.022163e-16 m\ne_R = 1.605583e-16 rad", GREEN);
  addText(slide, "No afirmamos colision certificada: sin geometria collision validada, esta es una prueba cinematica en una region critica.", 105, 550, 1070, 78, { size: 20, bold: true, color: RED, align: "center", valign: "middle", fill: "#FBECEC", line: { style: "solid", fill: "#E5B7B7", width: 1 }, borderRadius: 10 });
  addNote(slide, "RViz no detecta colisiones. Para una prueba formal se necesitan mallas collision y MoveIt 2 o un simulador apropiado.");
}

// 13. Evidence
{
  const slide = baseSlide(13, "Evidencia verificable del Hito 1", "RESULTADOS");
  addNativeTable(slide, [
    ["Comprobacion", "Resultado"],
    ["Juntas revolutas", "6"],
    ["Juntas fijas", "0"],
    ["Links totales", "7 (incluye base_link)"],
    ["inertial / collision", "0 / 0"],
    ["Pruebas automatizadas", "12 aprobadas"],
    ["Error maximo", "1.118863e-16 m"],
    ["Tolerancia", "1.0e-6 m"],
  ], 75, 155, 650, 420, [355, 295], 17);
  addText(slide, "Comandos para mostrar", 770, 175, 420, 38, { size: 24, bold: true, color: TEAL });
  addText(slide,
    "ros2 run irb120_hito1 verify_model\n\ncolcon test --packages-select irb120_hito1\n\ncolcon test-result --verbose\n\ncheck_urdf /tmp/irb120.urdf",
    770, 230, 420, 270,
    { typeface: MONO, size: 18, color: WHITE, fill: NAVY, line: { style: "solid", fill: "#263B55", width: 1 }, borderRadius: 12, insets: { top: 22, left: 20, right: 20, bottom: 18 } },
  );
  addText(slide, "Esperado: APROBADO | 12 tests | arbol serial de 6 joints", 760, 535, 430, 68, { size: 19, bold: true, color: GREEN, align: "center", valign: "middle", fill: "#EAF6EF", borderRadius: 10 });
  addNote(slide, "Resultados obtenidos localmente con colcon test y ros2 run irb120_hito1 verify_model.");
}

// 14. Live demo and close
{
  const slide = pres.slides.add();
  slide.background.fill = NAVY;
  addRect(slide, 0, 0, W, 16, ORANGE);
  addText(slide, "DEMOSTRACION EN VIVO", 60, 42, 420, 30, { size: 15, bold: true, color: ORANGE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  addText(slide, "Seis pasos para cerrar la defensa", 60, 82, 1140, 55, { size: 38, bold: true, color: WHITE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  const steps = [
    ["1", "Cargar", "source ROS y workspace"],
    ["2", "Validar", "verify_model"],
    ["3", "Probar", "12 tests"],
    ["4", "Abrir", "RViz + sliders"],
    ["5", "Mover", "joint_1 a joint_6"],
    ["6", "Explicar", "DH, error y poses"],
  ];
  for (let i = 0; i < steps.length; i++) {
    const x = 58 + (i % 3) * 404;
    const y = 175 + Math.floor(i / 3) * 180;
    addCircle(slide, x, y + 22, 70, ORANGE, ORANGE);
    addText(slide, steps[i][0], x, y + 30, 70, 48, { size: 28, bold: true, color: NAVY, align: "center", valign: "middle", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
    addText(slide, steps[i][1], x + 90, y + 12, 250, 38, { size: 25, bold: true, color: WHITE, insets: { top: 0, left: 0, right: 0, bottom: 0 } });
    addText(slide, steps[i][2], x + 90, y + 58, 260, 50, { size: 18, color: "#C9D6E5", insets: { top: 0, left: 0, right: 0, bottom: 0 } });
  }
  addText(slide, "Hito 1 completado", 265, 560, 750, 66, { size: 38, bold: true, color: NAVY, align: "center", valign: "middle", fill: ORANGE, borderRadius: 14 });
  addText(slide, "Pendiente futuro: CAD por eslabon, colisiones, dinamica y control", 240, 640, 800, 34, { size: 18, color: "#C9D6E5", align: "center", valign: "middle" });
  addNote(slide, "Antes de empezar, cerrar cualquier launch antiguo con Ctrl+C para no visualizar el modelo anterior.");
}

const requirements = {
  explicitTotalSlideCount: 14,
  requiredNativeTableOwnerSlides: [5, 7, 13],
  requiredNativeChartOwnerSlides: [],
};
const fontPolicy = {
  basis: "reference",
  families: ["Liberation Sans", "Liberation Mono"],
  referencePath: path.join(workspaceDir, "archivo", "hito1", "entregables_anteriores", "Defensa_Hito1_ABB_IRB120_ROS2_v2.pptx"),
  referenceSha256: "c959e471dfc00a973692e555e498dbbd7ed79b34e076d4cfaf0e242604b9eb81",
};
const expectedSlideSizeEmu = "12192000,6858000";
const stagingDir = path.join(TMP_DIR, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "candidate.pptx");
await (await PresentationFile.exportPptx(pres)).save(candidatePath);

const tableOwners = requirements.requiredNativeTableOwnerSlides;
const result = await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools", "inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", expectedSlideSizeEmu,
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    ...tableOwners.flatMap((number) => ["--require-native-table-slide", String(number)]),
  ],
  requiredNativeTableOwnerSlides: tableOwners,
  requiredNativeChartOwnerSlides: [],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
});

console.log(JSON.stringify({ final: FINAL_PPTX, result }, null, 2));
