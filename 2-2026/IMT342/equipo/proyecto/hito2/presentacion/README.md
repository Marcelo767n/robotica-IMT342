# Presentación interactiva del Hito 2 (`IRB 120 · Hito 2 en vivo`)

Página web que **calcula todo el pipeline en vivo** y lo muestra por criterio de la rúbrica. El docente escribe una pose
(x, y, z, roll, pitch, yaw) y ve las 8 ramas en 3D, la validación, la selección, el LSPB animado, el Jacobiano, la
singularidad y el torque.

## Cómo abrirla

| Situación | Qué abrir |
|---|---|
| Sin internet (aula) | `Hito2_en_vivo.html`, con doble clic. Es un solo archivo; sin red solo cambia la tipografía |
| Con internet | Enlace privado de claude.ai: https://claude.ai/artifact/MbzXsgggYrTaPofMAMrbBr |

## Secciones (barra izquierda)

| Sección | Criterio | Qué se puede hacer en vivo |
|---|---|---|
| Pipeline | — | Resumen de cada etapa, la tabla de la rúbrica y el movimiento en 3D |
| Pieper · 8 ramas | A | Ver cada rama en 3D (girar con el ratón), paso a paso numérico y tabla de 8 ramas |
| Validación FK | B | Errores por rama; **inyectar errores** (un error solo en q6 se rechaza); ida y vuelta con 300 poses; FK frente al modelo oficial de ROS-Industrial |
| Selección de rama | A | Criterio en 4 pasos y tabla de decisión |
| Trayectoria LSPB | C | Animación 3D sincronizada con q, q̇, q̈; cambiar v_max (% del datasheet) y la rampa |
| Jacobiano | D | J(q(t)) en vivo, validación numérica y σ_min a lo largo del movimiento |
| Singularidad | D | Control deslizante q5 → 0: σ_i, rango, det; **animación del movimiento nulo** (q̇4 = −q̇6 no mueve el TCP) |
| Dinámica 1R | E | Péndulo equivalente animado; τ_in, τ_g y τ; sostén al final; 1R frente al modelo completo |
| Verificación y defensa | F, G | Verificaciones en vivo, entregables y respuestas cortas G1–G4 |

## ¿Es el mismo cálculo que el notebook?

Sí. `irb120.js` es una traducción función por función del paquete Python `../irb120/`. Se verifica así (desde
`hito2/`):

```bash
.venv/bin/python presentacion/generar_vectores.py   # 105 casos de referencia calculados con Python
node presentacion/verificar_port.mjs                # compara la versión JavaScript con Python
```

Último resultado: 105 casos, 0 discrepancias en ramas, etiquetas, límites y rama elegida; diferencias numéricas
≤ 1e-9. **El entregable sigue siendo el notebook y el informe IEEE**: esta página es un apoyo visual para la defensa.

## Archivos

| Archivo | Qué es |
|---|---|
| `index.html` + `app.js` + `irb120.js` | Fuente de la página (la publicada en claude.ai) |
| `Hito2_en_vivo.html` | Versión de un solo archivo, generada con `python3 construir_local.py` |
| `generar_vectores.py`, `verificar_port.mjs`, `vectores.json` | Verificación de la traducción JavaScript contra Python |
