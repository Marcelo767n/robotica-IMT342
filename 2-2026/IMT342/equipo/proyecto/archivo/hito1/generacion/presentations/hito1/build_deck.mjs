import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const WORKSPACE = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../..");
const SKILL_DIR = "/home/marcelo767/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const BUILD_DIR = path.join(WORKSPACE, "archivo/hito1/generacion/presentations/hito1");
const FINAL_PPTX = path.join(WORKSPACE, "archivo/hito1/entregables_anteriores/Defensa_Hito1_ABB_IRB120_ROS2_v2.pptx");
const SCREENSHOT = path.join(WORKSPACE, "docs/hito1/assets/rviz_irb120_demo_automatica.png");
const RUNTIME_PYTHON = "/home/marcelo767/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python";

const {
  resolvePresentationFont,
  makeNativeBulletParagraphs,
  finalizePresentation,
} = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href);

await fs.mkdir(BUILD_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });

const FONT = "Liberation Sans";
const MONO = "Liberation Mono";
const C = {
  paper: "#F7F5F2",
  white: "#FFFFFF",
  navy: "#17212B",
  orange: "#F06C00",
  orangePale: "#FFF0E5",
  teal: "#087E8B",
  tealPale: "#E7F4F5",
  green: "#15803D",
  greenPale: "#EAF6EE",
  gray: "#5B6573",
  grayPale: "#E8ECEF",
  line: "#CED5DC",
  red: "#B42318",
};

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const requirements = {
  explicitTotalSlideCount: 14,
  requiredNativeTableOwnerSlides: [5, 12],
  requiredNativeChartOwnerSlides: [],
};
const fontPolicy = { basis: "design", families: [FONT, MONO] };
const expectedSlideSizeEmu = "12192000,6858000";

function addShape(slide, geometry, position, fill, lineFill = "none", lineWidth = 0) {
  return slide.shapes.add({
    geometry,
    position,
    fill,
    line: { fill: lineFill, width: lineWidth },
  });
}

function addText(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: options.typeface ?? FONT,
    fontSize: options.fontSize ?? 20,
    bold: options.bold ?? false,
    italic: options.italic ?? false,
    color: options.color ?? C.navy,
    alignment: options.alignment ?? "left",
    verticalAlignment: options.verticalAlignment ?? "top",
    autoFit: options.autoFit ?? "shrinkText",
    wrap: "square",
    lineSpacing: options.lineSpacing ?? 1.0,
    insets: options.insets ?? { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return shape;
}

function addBullets(slide, items, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text.set(
    makeNativeBulletParagraphs(items, {
      marginLeftPoints: options.marginLeftPoints ?? 20,
      hangingPoints: options.hangingPoints ?? 10,
      spaceAfterPoints: options.spaceAfterPoints ?? 8,
      bulletCharacter: "•",
    }),
  );
  shape.text.style = {
    typeface: FONT,
    fontSize: options.fontSize ?? 20,
    color: options.color ?? C.navy,
    autoFit: "shrinkText",
    verticalAlignment: "top",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
  };
  return shape;
}

function addTitle(slide, index, title, kicker) {
  slide.background.fill = C.paper;
  addShape(slide, "rect", { left: 0, top: 0, width: 18, height: 720 }, C.orange);
  addText(slide, String(index).padStart(2, "0"), { left: 54, top: 38, width: 50, height: 26 }, {
    fontSize: 15, bold: true, color: C.orange,
  });
  addText(slide, kicker.toUpperCase(), { left: 112, top: 38, width: 1050, height: 24 }, {
    fontSize: 14, bold: true, color: C.teal,
  });
  addText(slide, title, { left: 54, top: 76, width: 1160, height: 58 }, {
    fontSize: 38, bold: true, color: C.navy, verticalAlignment: "middle",
  });
  addShape(slide, "rect", { left: 54, top: 142, width: 1170, height: 2 }, C.line);
  addText(slide, `IMT-342  ·  Hito 1  ·  ${index}/14`, { left: 54, top: 683, width: 1170, height: 18 }, {
    fontSize: 11, color: C.gray, alignment: "right",
  });
}

function addPill(slide, text, position, fill, color = C.navy) {
  const shape = addShape(slide, "roundRect", position, fill, "none", 0);
  shape.text = text;
  shape.text.style = {
    typeface: FONT,
    fontSize: 17,
    bold: true,
    color,
    alignment: "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
    insets: { top: 6, right: 8, bottom: 6, left: 8 },
  };
  return shape;
}

function addPanel(slide, position, fill = C.white, line = C.line) {
  return addShape(slide, "roundRect", position, fill, line, 1);
}

function addNotes(slide, script, sources) {
  slide.speakerNotes.textFrame.setText(
    `${script}\n\nFuentes:\n${sources.map((source) => `- ${source}`).join("\n")}`,
  );
}

function addTable(slide, values, position, columnWidths, headerFill = C.navy) {
  const table = slide.tables.add({
    rows: values.length,
    columns: values[0].length,
    left: position.left,
    top: position.top,
    width: position.width,
    height: position.height,
    columnWidths,
    values,
  });
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: values.length, columnCount: values[0].length }).assign({
    textStyle: { typeface: FONT, fontSize: 15, color: C.navy },
    fill: C.white,
    margins: { top: 4, right: 7, bottom: 4, left: 7 },
    anchor: "middle",
  });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: values[0].length }).assign({
    textStyle: { typeface: FONT, fontSize: 15, bold: true, color: C.white },
    fill: headerFill,
    anchor: "middle",
  });
  for (let row = 1; row < values.length; row += 1) {
    if (row % 2 === 0) {
      table.cells.block({ row, column: 0, rowCount: 1, columnCount: values[0].length }).fill = C.grayPale;
    }
  }
  return table;
}

// 1. Portada
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addShape(slide, "rect", { left: 0, top: 0, width: 1280, height: 18 }, C.orange);
  addText(slide, "PROYECTO FINAL IMT-342", { left: 76, top: 74, width: 660, height: 30 }, {
    fontSize: 18, bold: true, color: "#DDE5EC",
  });
  addText(slide, "Hito 1", { left: 76, top: 126, width: 560, height: 78 }, {
    fontSize: 56, bold: true, color: C.white,
  });
  addText(slide, "Gemelo digital del ABB IRB 120", { left: 76, top: 205, width: 720, height: 62 }, {
    fontSize: 35, bold: true, color: C.white,
  });
  addText(slide, "ROS 2 Jazzy  ·  URDF/Xacro  ·  Cinemática DH  ·  Pinza paralela", { left: 76, top: 286, width: 800, height: 38 }, {
    fontSize: 20, color: "#C9D3DC",
  });
  addPill(slide, "9 pruebas aprobadas", { left: 76, top: 383, width: 255, height: 48 }, C.greenPale, C.green);
  addPill(slide, "Error máximo 2.22 x 10⁻¹⁶ m", { left: 350, top: 383, width: 335, height: 48 }, C.orangePale, C.orange);

  addShape(slide, "ellipse", { left: 930, top: 500, width: 88, height: 88 }, C.orange);
  addShape(slide, "rect", { left: 902, top: 454, width: 180, height: 54 }, C.orange);
  addShape(slide, "ellipse", { left: 1032, top: 410, width: 72, height: 72 }, C.orange);
  const arm1 = addShape(slide, "rect", { left: 1037, top: 342, width: 180, height: 45 }, C.orange);
  arm1.rotation = -24;
  addShape(slide, "ellipse", { left: 1157, top: 302, width: 64, height: 64 }, C.orange);
  const wrist = addShape(slide, "rect", { left: 1176, top: 268, width: 88, height: 28 }, C.white);
  wrist.rotation = -12;
  addShape(slide, "rect", { left: 1217, top: 244, width: 18, height: 54 }, C.teal);
  addShape(slide, "rect", { left: 1250, top: 244, width: 18, height: 54 }, C.teal);
  addText(slide, "Versión comprobada el 10 de septiembre de 2026", { left: 76, top: 636, width: 700, height: 25 }, {
    fontSize: 14, color: "#95A3AF",
  });
  addNotes(
    slide,
    "Presenta el objetivo general. Aclara desde el inicio que la geometría es provisional, pero la cadena cinemática y el pasaporte ya fueron verificados.",
    [
      `${WORKSPACE}/referencias/bibliografia/Guia_PFI.pdf, sección 4`,
      `${WORKSPACE}/docs/hito1/resultados.md`,
    ],
  );
}

// 2. Requisito
{
  const slide = presentation.slides.add();
  addTitle(slide, 2, "El Hito 1 convierte una exigencia en una prueba", "Objetivo y pasaporte");
  addPanel(slide, { left: 54, top: 174, width: 650, height: 425 });
  addText(slide, "Lo que exige la guía", { left: 84, top: 204, width: 580, height: 36 }, {
    fontSize: 25, bold: true, color: C.teal,
  });
  addBullets(slide, [
    "Paquete ROS del ABB IRB 120 con pinza",
    "Descripción URDF modular",
    "Cinemática directa programada por el equipo",
    "Comparación cartesiana reproducible",
    "Sin resolver la cinemática mediante MoveIt",
  ], { left: 84, top: 262, width: 570, height: 275 }, { fontSize: 20, spaceAfterPoints: 10 });

  addPanel(slide, { left: 744, top: 174, width: 480, height: 425 }, C.navy, C.navy);
  addText(slide, "Criterio", { left: 786, top: 212, width: 390, height: 30 }, {
    fontSize: 18, bold: true, color: "#B7C4CF", alignment: "center",
  });
  addText(slide, "error < 1 x 10⁻⁶ m", { left: 774, top: 266, width: 420, height: 70 }, {
    fontSize: 38, bold: true, color: C.white, alignment: "center", verticalAlignment: "middle",
  });
  addShape(slide, "rect", { left: 802, top: 366, width: 354, height: 12 }, "#3B4A57");
  addShape(slide, "rect", { left: 802, top: 366, width: 75, height: 12 }, C.green);
  addText(slide, "Resultado real", { left: 802, top: 410, width: 354, height: 24 }, {
    fontSize: 17, color: "#B7C4CF", alignment: "center",
  });
  addText(slide, "2.22 x 10⁻¹⁶ m", { left: 802, top: 445, width: 354, height: 50 }, {
    fontSize: 31, bold: true, color: "#6ED18C", alignment: "center",
  });
  addText(slide, "APROBADO", { left: 802, top: 528, width: 354, height: 28 }, {
    fontSize: 20, bold: true, color: "#6ED18C", alignment: "center",
  });
  addNotes(slide, "Lee el criterio y después muestra que el resultado medido está muchos órdenes de magnitud por debajo del límite.", [
    `${WORKSPACE}/referencias/bibliografia/Guia_PFI.pdf, sección 4`,
    `${WORKSPACE}/docs/hito1/resultados.md`,
  ]);
}

// 3. Arquitectura
{
  const slide = presentation.slides.add();
  addTitle(slide, 3, "Una sola muestra alimenta visualización y validación", "Arquitectura ROS 2");
  const boxes = [
    { x: 58, w: 210, title: "Comando", body: "Usuario o motion_demo", fill: C.orangePale, accent: C.orange },
    { x: 330, w: 250, title: "Estado articular", body: "joint_state_source\npublica /joint_states", fill: C.white, accent: C.teal },
    { x: 650, w: 250, title: "Modelo espacial", body: "robot_state_publisher\npublica TF", fill: C.white, accent: C.teal },
    { x: 970, w: 250, title: "Vista 3D", body: "RViz muestra links\ny frames", fill: C.greenPale, accent: C.green },
  ];
  for (const box of boxes) {
    addPanel(slide, { left: box.x, top: 210, width: box.w, height: 130 }, box.fill, box.accent);
    addShape(slide, "rect", { left: box.x, top: 210, width: 8, height: 130 }, box.accent);
    addText(slide, box.title, { left: box.x + 24, top: 232, width: box.w - 40, height: 28 }, {
      fontSize: 20, bold: true, color: box.accent,
    });
    addText(slide, box.body, { left: box.x + 24, top: 274, width: box.w - 40, height: 54 }, {
      fontSize: 17, color: C.navy,
    });
  }
  for (const x of [278, 598, 918]) {
    addShape(slide, "rect", { left: x, top: 271, width: 34, height: 5 }, C.gray);
    addShape(slide, "triangle", { left: x + 26, top: 263, width: 18, height: 21 }, C.gray).rotation = 90;
  }
  addShape(slide, "rect", { left: 447, top: 340, width: 5, height: 84 }, C.gray);
  addShape(slide, "rect", { left: 447, top: 419, width: 200, height: 5 }, C.gray);
  addShape(slide, "triangle", { left: 638, top: 411, width: 18, height: 21 }, C.gray).rotation = 90;
  addPanel(slide, { left: 650, top: 374, width: 570, height: 150 }, C.tealPale, C.teal);
  addText(slide, "fk_validator", { left: 684, top: 398, width: 190, height: 28 }, {
    fontSize: 21, bold: true, color: C.teal,
  });
  addText(slide, "Calcula la pose por DH y por la cadena URDF", { left: 684, top: 443, width: 360, height: 46 }, {
    fontSize: 18, color: C.navy,
  });
  addPill(slide, "error en metros", { left: 1043, top: 414, width: 145, height: 52 }, C.white, C.green);
  addText(slide, "Mismo /joint_states", { left: 292, top: 392, width: 145, height: 26 }, {
    fontSize: 14, bold: true, color: C.gray, alignment: "right",
  });
  addNotes(slide, "Explica la bifurcación: el mismo estado llega a robot_state_publisher para TF y al validador para comparar DH contra URDF.", [
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/launch/display.launch.py`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/nodes/fk_validator.py`,
  ]);
}

// 4. Modularidad
{
  const slide = presentation.slides.add();
  addTitle(slide, 4, "La organización permite cambiar la apariencia sin romper la matemática", "Paquete modular");
  addPanel(slide, { left: 54, top: 174, width: 655, height: 445 }, C.navy, C.navy);
  addText(slide, "irb120_hito1/", { left: 84, top: 201, width: 580, height: 30 }, {
    typeface: MONO, fontSize: 18, bold: true, color: "#9ED7DD",
  });
  addText(slide,
    "urdf/\n  materials.xacro\n  irb120.macro.xacro\n  gripper.macro.xacro\n  irb120_with_gripper.urdf.xacro\nkinematics/\n  dh.py\n  urdf_chain.py\nnodes/\n  joint_state_source.py\n  motion_demo.py\n  fk_validator.py\nlaunch/   rviz/   config/   test/",
    { left: 84, top: 250, width: 580, height: 335 },
    { typeface: MONO, fontSize: 17, color: "#E6EDF3", lineSpacing: 1.05 },
  );
  addText(slide, "Tres capas", { left: 760, top: 190, width: 420, height: 34 }, {
    fontSize: 25, bold: true, color: C.teal,
  });
  const layers = [
    ["1", "Modelo", "URDF, Xacro, DH y parámetros"],
    ["2", "Ejecución", "Nodos, tópicos, TF y launch"],
    ["3", "Evidencia", "Pruebas, error y documentación"],
  ];
  layers.forEach(([n, title, body], i) => {
    const y = 254 + i * 108;
    addShape(slide, "ellipse", { left: 760, top: y, width: 48, height: 48 }, i === 0 ? C.orange : C.teal);
    addText(slide, n, { left: 760, top: y + 6, width: 48, height: 30 }, {
      fontSize: 20, bold: true, color: C.white, alignment: "center",
    });
    addText(slide, title, { left: 830, top: y, width: 320, height: 28 }, {
      fontSize: 21, bold: true, color: C.navy,
    });
    addText(slide, body, { left: 830, top: y + 36, width: 340, height: 44 }, {
      fontSize: 17, color: C.gray,
    });
  });
  addPanel(slide, { left: 760, top: 560, width: 410, height: 60 }, C.greenPale, C.green);
  addText(slide, "CAD futuro: solo visual y collision", { left: 782, top: 578, width: 365, height: 24 }, {
    fontSize: 17, bold: true, color: C.green, alignment: "center",
  });
  addNotes(slide, "Usa esta diapositiva para demostrar modularidad real. Señala que el CAD podrá cambiar sin editar los joints ni el código DH.", [
    `${WORKSPACE}/ros2_ws/src/irb120_hito1`,
    `${WORKSPACE}/docs/hito1/trazabilidad.md`,
  ]);
}

// 5. Tabla DH nativa
{
  const slide = presentation.slides.add();
  addTitle(slide, 5, "Seis filas DH definen la cadena cinemática", "Modelo matemático");
  addPanel(slide, { left: 54, top: 166, width: 1170, height: 72 }, C.navy, C.navy);
  addText(slide, "T(i-1,i) = Rz(thetaᵢ)  Tz(dᵢ)  Tx(aᵢ)  Rx(alphaᵢ)", { left: 86, top: 186, width: 1105, height: 32 }, {
    typeface: MONO, fontSize: 22, color: C.white, alignment: "center",
  });
  const values = [
    ["Eje", "theta efectivo", "d [m]", "a [m]", "alpha [rad]"],
    ["1", "q1", "0.290", "0.000", "-pi/2"],
    ["2", "q2 - pi/2", "0.000", "0.270", "0"],
    ["3", "q3", "0.000", "0.070", "-pi/2"],
    ["4", "q4", "0.302", "0.000", "pi/2"],
    ["5", "q5", "0.000", "0.000", "-pi/2"],
    ["6", "q6 + pi", "0.072", "0.000", "0"],
  ];
  addTable(slide, values, { left: 88, top: 270, width: 1104, height: 318 }, [95, 320, 220, 220, 249]);
  addText(slide, "Offsets no nulos: eje 2 = -pi/2   ·   eje 6 = +pi", { left: 88, top: 614, width: 1104, height: 30 }, {
    fontSize: 18, bold: true, color: C.orange, alignment: "center",
  });
  addNotes(slide, "Define theta, d, a y alpha. Destaca los offsets de los ejes 2 y 6 porque suelen ser la fuente de errores de signo.", [
    `${WORKSPACE}/referencias/bibliografia/IJMERR-V12N2-121.pdf, Tabla I`,
    `${WORKSPACE}/docs/hito1/modelo_cinematico.md`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/kinematics/dh.py`,
  ]);
}

// 6. DH a URDF
{
  const slide = presentation.slides.add();
  addTitle(slide, 6, "Cada fila DH se descompone sin cambiar el orden", "Traducción a URDF");
  addText(slide, "URDF aplica el origin fijo antes del movimiento del joint. Por eso la fila se divide en tres transformaciones.", { left: 70, top: 170, width: 1120, height: 44 }, {
    fontSize: 20, color: C.gray, alignment: "center",
  });
  const steps = [
    { x: 74, label: "Joint móvil", formula: "Rz(qᵢ)", detail: "joint_i", fill: C.orangePale, accent: C.orange },
    { x: 433, label: "Offset fijo", formula: "Rz(offsetᵢ)", detail: "theta_offset_i", fill: C.tealPale, accent: C.teal },
    { x: 792, label: "Geometría fija", formula: "Tz(dᵢ)  Tx(aᵢ)  Rx(alphaᵢ)", detail: "dh_i", fill: C.greenPale, accent: C.green },
  ];
  steps.forEach((step, i) => {
    addPanel(slide, { left: step.x, top: 260, width: 330, height: 188 }, step.fill, step.accent);
    addText(slide, step.label, { left: step.x + 24, top: 284, width: 282, height: 28 }, {
      fontSize: 20, bold: true, color: step.accent, alignment: "center",
    });
    addText(slide, step.formula, { left: step.x + 24, top: 334, width: 282, height: 42 }, {
      typeface: MONO, fontSize: i === 2 ? 17 : 22, bold: true, color: C.navy, alignment: "center", verticalAlignment: "middle",
    });
    addPill(slide, step.detail, { left: step.x + 76, top: 396, width: 178, height: 34 }, C.white, step.accent);
  });
  for (const x of [408, 767]) {
    addText(slide, "+", { left: x, top: 328, width: 26, height: 36 }, { fontSize: 28, bold: true, color: C.gray, alignment: "center" });
  }
  addPanel(slide, { left: 160, top: 510, width: 960, height: 92 }, C.white, C.line);
  addText(slide, "Resultado", { left: 190, top: 530, width: 150, height: 28 }, { fontSize: 20, bold: true, color: C.teal });
  addText(slide, "La cadena URDF y el producto DH llegan a la misma pose para cualquier postura probada.", { left: 350, top: 526, width: 720, height: 42 }, {
    fontSize: 20, bold: true, color: C.navy, verticalAlignment: "middle",
  });
  addNotes(slide, "Explica que la descomposición no es un truco visual. Conserva exactamente el orden de la convención DH clásica.", [
    `${WORKSPACE}/docs/hito1/modelo_cinematico.md, sección Correspondencia DH-URDF`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/urdf/irb120.macro.xacro`,
  ]);
}

// 7. Ensamble Xacro
{
  const slide = presentation.slides.add();
  addTitle(slide, 7, "Xacro une módulos y genera el URDF que ROS carga", "Descripción del robot");
  const modules = [
    ["Materiales", "materials.xacro", "Colores reutilizables", C.grayPale, C.gray],
    ["Brazo", "irb120.macro.xacro", "6 joints y frames DH", C.orangePale, C.orange],
    ["Pinza", "gripper.macro.xacro", "2 dedos y tcp_link", C.tealPale, C.teal],
  ];
  modules.forEach(([title, file, detail, fill, accent], i) => {
    const x = 68 + i * 386;
    addPanel(slide, { left: x, top: 196, width: 340, height: 150 }, fill, accent);
    addText(slide, title, { left: x + 24, top: 220, width: 292, height: 28 }, {
      fontSize: 22, bold: true, color: accent, alignment: "center",
    });
    addText(slide, file, { left: x + 18, top: 264, width: 304, height: 24 }, {
      typeface: MONO, fontSize: 15, color: C.navy, alignment: "center",
    });
    addText(slide, detail, { left: x + 24, top: 307, width: 292, height: 22 }, {
      fontSize: 16, color: C.gray, alignment: "center",
    });
  });
  modules.forEach((_, i) => {
    const x = 232 + i * 386;
    addShape(slide, "rect", { left: x, top: 347, width: 5, height: 65 }, C.gray);
  });
  addShape(slide, "rect", { left: 232, top: 407, width: 772, height: 5 }, C.gray);
  addShape(slide, "rect", { left: 615, top: 407, width: 5, height: 38 }, C.gray);
  addShape(slide, "triangle", { left: 608, top: 438, width: 19, height: 22 }, C.gray).rotation = 180;
  addPanel(slide, { left: 298, top: 466, width: 684, height: 110 }, C.navy, C.navy);
  addText(slide, "irb120_with_gripper.urdf.xacro", { left: 330, top: 488, width: 620, height: 30 }, {
    typeface: MONO, fontSize: 21, bold: true, color: C.white, alignment: "center",
  });
  addText(slide, "Xacro expande este archivo a irb120_with_gripper.urdf", { left: 330, top: 532, width: 620, height: 24 }, {
    fontSize: 17, color: "#B7C4CF", alignment: "center",
  });
  addPill(slide, "Árbol único: base_link a tcp_link", { left: 408, top: 606, width: 465, height: 38 }, C.greenPale, C.green);
  addNotes(slide, "Aclara que Xacro genera URDF. El archivo principal llama los tres módulos y deja una cadena única desde la base hasta el TCP.", [
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/urdf/irb120_with_gripper.urdf.xacro`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/urdf/irb120_with_gripper.urdf`,
  ]);
}

// 8. Movimiento y launch
{
  const slide = presentation.slides.add();
  addTitle(slide, 8, "El launch inicia todo y permite elegir el modo de demostración", "Ejecución en vivo");
  addPanel(slide, { left: 54, top: 174, width: 1170, height: 100 }, C.navy, C.navy);
  addText(slide, "ros2 launch irb120_hito1 display.launch.py demo_motion:=true", { left: 86, top: 207, width: 1105, height: 34 }, {
    typeface: MONO, fontSize: 21, color: C.white, alignment: "center",
  });
  const nodes = [
    ["1", "robot_state_publisher", "URDF y TF"],
    ["2", "joint_state_source", "Estados y límites"],
    ["3", "motion_demo", "Trayectoria suave"],
    ["4", "fk_validator", "Error DH-URDF"],
    ["5", "rviz2", "Vista 3D"],
  ];
  nodes.forEach(([n, name, role], i) => {
    const x = 55 + i * 235;
    addShape(slide, "ellipse", { left: x + 73, top: 324, width: 48, height: 48 }, i === 2 ? C.orange : C.teal);
    addText(slide, n, { left: x + 73, top: 333, width: 48, height: 24 }, {
      fontSize: 18, bold: true, color: C.white, alignment: "center",
    });
    addText(slide, name, { left: x, top: 392, width: 194, height: 48 }, {
      fontSize: 17, bold: true, color: C.navy, alignment: "center", verticalAlignment: "middle",
    });
    addText(slide, role, { left: x, top: 446, width: 194, height: 30 }, {
      fontSize: 15, color: C.gray, alignment: "center",
    });
  });
  addPanel(slide, { left: 170, top: 522, width: 940, height: 86 }, C.greenPale, C.green);
  addText(slide, "Movimiento cíclico", { left: 210, top: 544, width: 250, height: 28 }, { fontSize: 20, bold: true, color: C.green });
  addText(slide, "5 posturas clave, interpolación cosenoidal y pinza entre 0 y 0.015 m", { left: 462, top: 540, width: 610, height: 40 }, {
    fontSize: 19, color: C.navy, verticalAlignment: "middle",
  });
  addNotes(slide, "Explica que demo_motion es opcional. Sin ese argumento el robot queda quieto y acepta comandos manuales.", [
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/launch/display.launch.py`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/motion.py`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/nodes/motion_demo.py`,
  ]);
}

// 9. Evidencia RViz
{
  const slide = presentation.slides.add();
  addTitle(slide, 9, "RViz muestra la cadena completa en una postura dinámica", "Evidencia visual real");
  const bytes = new Uint8Array(await fs.readFile(SCREENSHOT));
  slide.images.add({
    blob: bytes,
    contentType: "image/png",
    alt: "Captura real de RViz con el ABB IRB 120 provisional, la pinza y los frames",
    fit: "contain",
    position: { left: 54, top: 166, width: 790, height: 474 },
  });
  addPanel(slide, { left: 880, top: 166, width: 344, height: 474 }, C.white, C.line);
  addText(slide, "Qué se observa", { left: 910, top: 198, width: 286, height: 34 }, {
    fontSize: 24, bold: true, color: C.teal,
  });
  addBullets(slide, [
    "Seis eslabones en naranja",
    "Pinza paralela montada en tool0",
    "Frames de colores visibles",
    "Grilla con base_link fijo",
    "Postura no nula durante la animación",
  ], { left: 910, top: 260, width: 276, height: 260 }, { fontSize: 18, spaceAfterPoints: 9 });
  addPanel(slide, { left: 910, top: 544, width: 286, height: 62 }, C.orangePale, C.orange);
  addText(slide, "Geometría visual provisional", { left: 928, top: 563, width: 250, height: 24 }, {
    fontSize: 16, bold: true, color: C.orange, alignment: "center",
  });
  addNotes(slide, "Esta es una captura real tomada durante la ejecución. Aclara que RViz visualiza, pero no simula dinámica ni fuerzas.", [
    `${WORKSPACE}/docs/hito1/assets/rviz_irb120_demo_automatica.png`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/rviz/hito1.rviz`,
  ]);
}

// 10. Demo en vivo
{
  const slide = presentation.slides.add();
  addTitle(slide, 10, "La demostración en vivo cabe en tres acciones", "Procedimiento para el aula");
  const steps = [
    { n: "1", title: "Preparar", code: "source /opt/ros/jazzy/setup.bash\ncd .../proyecto/ros2_ws\nsource install/setup.bash", accent: C.teal },
    { n: "2", title: "Mostrar", code: "ros2 launch irb120_hito1\n  display.launch.py\n  demo_motion:=true", accent: C.orange },
    { n: "3", title: "Cerrar", code: "Ctrl+C", accent: C.green },
  ];
  steps.forEach((step, i) => {
    const x = 58 + i * 405;
    addPanel(slide, { left: x, top: 200, width: 360, height: 330 }, C.white, step.accent);
    addShape(slide, "ellipse", { left: x + 24, top: 224, width: 52, height: 52 }, step.accent);
    addText(slide, step.n, { left: x + 24, top: 234, width: 52, height: 28 }, {
      fontSize: 20, bold: true, color: C.white, alignment: "center",
    });
    addText(slide, step.title, { left: x + 92, top: 232, width: 230, height: 36 }, {
      fontSize: 25, bold: true, color: C.navy,
    });
    addPanel(slide, { left: x + 24, top: 306, width: 312, height: 160 }, C.navy, C.navy);
    addText(slide, step.code, { left: x + 40, top: 326, width: 280, height: 118 }, {
      typeface: MONO, fontSize: i === 0 ? 14 : 16, color: C.white, verticalAlignment: "middle",
    });
  });
  addPanel(slide, { left: 170, top: 568, width: 940, height: 68 }, C.greenPale, C.green);
  addText(slide, "Señal de éxito: la terminal repite APROBADO y RViz mantiene el brazo en movimiento", { left: 205, top: 589, width: 870, height: 26 }, {
    fontSize: 19, bold: true, color: C.green, alignment: "center",
  });
  addNotes(slide, "Antes de la clase deja el workspace compilado. Durante la exposición solo carga los entornos y ejecuta launch.", [
    `${WORKSPACE}/README.md, sección Demostración recomendada`,
    `${WORKSPACE}/docs/hito1/guion_defensa.md`,
  ]);
}

// 11. Método de validación
{
  const slide = presentation.slides.add();
  addTitle(slide, 11, "Dos caminos independientes reducen el riesgo de un falso positivo", "Método de validación");
  addPill(slide, "Misma postura q1 ... q6", { left: 468, top: 174, width: 344, height: 52 }, C.navy, C.white);
  addShape(slide, "rect", { left: 637, top: 226, width: 5, height: 52 }, C.gray);
  addShape(slide, "rect", { left: 320, top: 273, width: 640, height: 5 }, C.gray);
  addShape(slide, "rect", { left: 320, top: 273, width: 5, height: 40 }, C.gray);
  addShape(slide, "rect", { left: 955, top: 273, width: 5, height: 40 }, C.gray);
  addPanel(slide, { left: 105, top: 313, width: 430, height: 184 }, C.orangePale, C.orange);
  addText(slide, "Camino A", { left: 135, top: 340, width: 370, height: 28 }, { fontSize: 20, bold: true, color: C.orange, alignment: "center" });
  addText(slide, "Producto de seis matrices DH", { left: 145, top: 392, width: 350, height: 34 }, { fontSize: 23, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "kinematics/dh.py", { left: 145, top: 446, width: 350, height: 24 }, { typeface: MONO, fontSize: 16, color: C.gray, alignment: "center" });
  addPanel(slide, { left: 745, top: 313, width: 430, height: 184 }, C.tealPale, C.teal);
  addText(slide, "Camino B", { left: 775, top: 340, width: 370, height: 28 }, { fontSize: 20, bold: true, color: C.teal, alignment: "center" });
  addText(slide, "Recorrido independiente del URDF", { left: 785, top: 392, width: 350, height: 34 }, { fontSize: 22, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "kinematics/urdf_chain.py", { left: 785, top: 446, width: 350, height: 24 }, { typeface: MONO, fontSize: 16, color: C.gray, alignment: "center" });
  addShape(slide, "rect", { left: 535, top: 403, width: 210, height: 5 }, C.gray);
  addPill(slide, "norma de posición", { left: 535, top: 520, width: 210, height: 44 }, C.white, C.gray);
  addShape(slide, "rect", { left: 638, top: 497, width: 5, height: 23 }, C.gray);
  addPanel(slide, { left: 320, top: 594, width: 640, height: 52 }, C.greenPale, C.green);
  addText(slide, "4 posturas documentadas y 100 posturas pseudoaleatorias reproducibles", { left: 346, top: 610, width: 588, height: 24 }, {
    fontSize: 18, bold: true, color: C.green, alignment: "center",
  });
  addNotes(slide, "Subraya que no se está comparando el código consigo mismo. El evaluador URDF interpreta joints, origin y axis por una ruta separada.", [
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/kinematics/dh.py`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/kinematics/urdf_chain.py`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/test/test_urdf_matches_dh.py`,
  ]);
}

// 12. Resultados con tabla nativa
{
  const slide = presentation.slides.add();
  addTitle(slide, 12, "El pasaporte queda aprobado con amplio margen", "Resultados medidos");
  addText(slide, "2.220446049250 x 10⁻¹⁶ m", { left: 80, top: 180, width: 1120, height: 70 }, {
    fontSize: 43, bold: true, color: C.green, alignment: "center", verticalAlignment: "middle",
  });
  addText(slide, "error posicional máximo", { left: 80, top: 252, width: 1120, height: 28 }, {
    fontSize: 18, color: C.gray, alignment: "center",
  });
  const values = [
    ["Evidencia", "Resultado", "Criterio"],
    ["Construcción", "1 paquete terminado", "sin errores"],
    ["Pruebas", "9 aprobadas", "0 fallos"],
    ["Pasaporte offline", "2.22 x 10⁻¹⁶ m", "menor a 1 x 10⁻⁶ m"],
    ["Validación en movimiento", "APROBADO continuo", "DH coincide con URDF"],
  ];
  addTable(slide, values, { left: 125, top: 324, width: 1030, height: 245 }, [365, 300, 365], C.green);
  addPill(slide, "APROBADO", { left: 488, top: 604, width: 304, height: 48 }, C.green, C.white);
  addNotes(slide, "Muestra primero el número grande y luego la tabla. Explica que 1e-16 es ruido de redondeo de punto flotante.", [
    `${WORKSPACE}/docs/hito1/resultados.md`,
    `${WORKSPACE}/ros2_ws/src/irb120_hito1/irb120_hito1/verify_model.py`,
  ]);
}

// 13. Límites y CAD
{
  const slide = presentation.slides.add();
  addTitle(slide, 13, "La función está cerrada y la apariencia queda preparada para el CAD", "Alcance actual");
  addPanel(slide, { left: 54, top: 176, width: 556, height: 414 }, C.greenPale, C.green);
  addText(slide, "Completo hoy", { left: 88, top: 210, width: 488, height: 36 }, {
    fontSize: 26, bold: true, color: C.green,
  });
  addBullets(slide, [
    "Seis ejes y pinza articulados",
    "Frames base_link, tool0 y tcp_link",
    "Movimiento manual y automático",
    "Límites articulares oficiales",
    "DH, URDF y pruebas coherentes",
    "Error inferior a 1e-6 m",
  ], { left: 88, top: 280, width: 470, height: 260 }, { fontSize: 19, spaceAfterPoints: 8, color: C.navy });

  addPanel(slide, { left: 670, top: 176, width: 554, height: 414 }, C.orangePale, C.orange);
  addText(slide, "Pendiente visual", { left: 704, top: 210, width: 486, height: 36 }, {
    fontSize: 26, bold: true, color: C.orange,
  });
  addText(slide, "Formato preferido", { left: 704, top: 284, width: 486, height: 28 }, {
    fontSize: 18, bold: true, color: C.navy,
  });
  addPill(slide, ".dae visual", { left: 704, top: 332, width: 214, height: 44 }, C.white, C.orange);
  addPill(slide, ".stl colisión", { left: 944, top: 332, width: 214, height: 44 }, C.white, C.orange);
  addText(slide, "Alternativa", { left: 704, top: 414, width: 486, height: 28 }, {
    fontSize: 18, bold: true, color: C.navy,
  });
  addText(slide, "STEP con cada eslabón como componente independiente, unidades claras y postura cero indicada", { left: 704, top: 458, width: 455, height: 70 }, {
    fontSize: 18, color: C.navy,
  });
  addPanel(slide, { left: 230, top: 620, width: 820, height: 42 }, C.white, C.line);
  addText(slide, "El CAD sustituye visual y collision. No cambia joints, frames ni DH.", { left: 260, top: 631, width: 760, height: 22 }, {
    fontSize: 17, bold: true, color: C.teal, alignment: "center",
  });
  addNotes(slide, "Presenta el pendiente como una sustitución visual controlada. Una sola malla fusionada no sirve porque los eslabones deben moverse por separado.", [
    `${WORKSPACE}/README.md, sección Modelo visual pendiente`,
    `${WORKSPACE}/docs/hito1/trazabilidad.md, sección Pendiente para el gemelo visual definitivo`,
    "ABB Product specification IRB 120, 3HAC035960-001 Rev. S: https://library.e.abb.com/public/6aed5e91083f4fceb358eea2fe4c1bab/3HAC035960%20PS%20IRB%20120-en.pdf",
  ]);
}

// 14. Cierre
{
  const slide = presentation.slides.add();
  slide.background.fill = C.navy;
  addShape(slide, "rect", { left: 0, top: 0, width: 18, height: 720 }, C.orange);
  addText(slide, "Hito 1 aprobado", { left: 76, top: 82, width: 760, height: 72 }, {
    fontSize: 48, bold: true, color: C.white,
  });
  addText(slide, "Tres ideas para recordar en la defensa", { left: 76, top: 176, width: 760, height: 36 }, {
    fontSize: 23, color: "#B7C4CF",
  });
  const messages = [
    ["1", "URDF describe el robot y Xacro organiza sus módulos"],
    ["2", "DH y URDF se validan por caminos independientes"],
    ["3", "El CAD pendiente cambia la forma, no la cinemática"],
  ];
  messages.forEach(([n, message], i) => {
    const y = 262 + i * 92;
    addShape(slide, "ellipse", { left: 82, top: y, width: 46, height: 46 }, i === 0 ? C.orange : C.teal);
    addText(slide, n, { left: 82, top: y + 8, width: 46, height: 24 }, { fontSize: 18, bold: true, color: C.white, alignment: "center" });
    addText(slide, message, { left: 152, top: y + 5, width: 720, height: 40 }, { fontSize: 22, bold: true, color: C.white, verticalAlignment: "middle" });
  });
  addPanel(slide, { left: 930, top: 102, width: 286, height: 428 }, "#22303D", "#3C4D5C");
  addText(slide, "Comandos finales", { left: 960, top: 138, width: 226, height: 32 }, { fontSize: 22, bold: true, color: "#9ED7DD", alignment: "center" });
  addText(slide, "Validar", { left: 958, top: 208, width: 226, height: 24 }, { fontSize: 17, bold: true, color: C.orange, alignment: "center" });
  addText(slide, "ros2 run irb120_hito1\nverify_model", { left: 952, top: 246, width: 240, height: 56 }, { typeface: MONO, fontSize: 15, color: C.white, alignment: "center" });
  addText(slide, "Demostrar", { left: 958, top: 336, width: 226, height: 24 }, { fontSize: 17, bold: true, color: C.orange, alignment: "center" });
  addText(slide, "ros2 launch irb120_hito1\ndisplay.launch.py\ndemo_motion:=true", { left: 948, top: 372, width: 246, height: 78 }, { typeface: MONO, fontSize: 14, color: C.white, alignment: "center" });
  addPill(slide, "Preguntas", { left: 982, top: 474, width: 182, height: 38 }, C.teal, C.white);
  addText(slide, "2.22 x 10⁻¹⁶ m  ·  9 pruebas  ·  6 ejes + pinza", { left: 76, top: 620, width: 800, height: 32 }, { fontSize: 20, bold: true, color: "#6ED18C" });
  addNotes(slide, "Cierra con seguridad. Si preguntan por el CAD, responde que la interfaz de integración ya está definida y protegida por pruebas de regresión.", [
    `${WORKSPACE}/docs/hito1/guion_defensa.md`,
    `${WORKSPACE}/docs/hito1/resultados.md`,
  ]);
}

const stagingDir = path.join(BUILD_DIR, ".codex-finalizer");
await fs.mkdir(stagingDir, { recursive: true });
const candidatePath = path.join(stagingDir, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const result = await finalizePresentation({
  ...requirements,
  workspaceDir: WORKSPACE,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", expectedSlideSizeEmu,
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    ...requirements.requiredNativeTableOwnerSlides.flatMap((number) => ["--require-native-table-slide", String(number)]),
  ],
  requiredNativeTableOwnerSlides: requirements.requiredNativeTableOwnerSlides,
  requiredNativeChartOwnerSlides: requirements.requiredNativeChartOwnerSlides,
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, `${path.basename(FINAL_PPTX)}.validation.json`),
});

console.log(JSON.stringify({ final: FINAL_PPTX, font: FONT, result }, null, 2));
