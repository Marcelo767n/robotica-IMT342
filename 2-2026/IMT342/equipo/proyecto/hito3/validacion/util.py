"""Utilidades de salida: CSV, JSON, YAML mínimo y tablas LaTeX (booktabs)."""

import csv
import json
import math
import re
from pathlib import Path

import numpy as np

from . import rutas


def _plano(v):
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def _json_default(v):
    r = _plano(v)
    if r is v:
        raise TypeError(f"no serializable: {type(v)}")
    return r


def escribir_json(ruta, datos):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as fh:
        json.dump(datos, fh, indent=2, ensure_ascii=False, default=_json_default, allow_nan=True)


def escribir_csv(ruta, columnas, filas):
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(columnas)
        for f in filas:
            w.writerow([_plano(v) if not isinstance(v, (list, tuple)) else _lista(v) for v in f])


def _lista(v):
    return "[" + " ".join(f"{_plano(x):.12g}" if isinstance(_plano(x), float) else str(_plano(x)) for x in v) + "]"


def vec(v, nd=10) -> str:
    return "[" + ", ".join(f"{float(x):.{nd}g}" for x in np.asarray(v).ravel()) + "]"


# ------------------------------------------------------------------------------------------ YAML mínimo
def _escalar_yaml(v):
    v = _plano(v)
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    if s == "" or re.search(r"[:#\[\]{},&*!|>'\"%@`\n]", s) or s.strip() != s or s.lower() in ("null", "true", "false", "yes", "no") or re.fullmatch(r"[-+0-9.eE_]+", s):
        return json.dumps(s, ensure_ascii=False)
    return s


def a_yaml(dato, nivel=0) -> str:
    sangria = "  " * nivel
    salida = []
    if isinstance(dato, dict):
        for k, v in dato.items():
            if isinstance(v, (dict, list)) and v:
                if isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v) and len(v) <= 8:
                    salida.append(f"{sangria}{k}: [" + ", ".join(_escalar_yaml(x) for x in v) + "]")
                else:
                    salida.append(f"{sangria}{k}:")
                    salida.append(a_yaml(v, nivel + 1))
            elif isinstance(v, (dict, list)):
                salida.append(f"{sangria}{k}: " + ("{}" if isinstance(v, dict) else "[]"))
            else:
                salida.append(f"{sangria}{k}: {_escalar_yaml(v)}")
    else:
        for v in dato:
            if isinstance(v, (dict, list)):
                salida.append(f"{sangria}-")
                salida.append(a_yaml(v, nivel + 1))
            else:
                salida.append(f"{sangria}- {_escalar_yaml(v)}")
    return "\n".join(salida)


# ------------------------------------------------------------------------------------------ LaTeX
_ESC = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


_UNI = {"≥": r"$\ge$", "≤": r"$\le$", "≈": r"$\approx$", "≠": r"$\neq$", "⇒": r"$\Rightarrow$", "→": r"$\to$", "↔": r"$\leftrightarrow$", "δ": r"$\delta$", "Δ": r"$\Delta$",
        "Σ": r"$\Sigma$", "ω": r"$\omega$", "ε": r"$\epsilon$", "κ": r"$\kappa$", "σ": r"$\sigma$", "τ": r"$\tau$", "π": r"$\pi$", "λ": r"$\lambda$", "θ": r"$\theta$", "×": r"$\times$",
        "−": "-", "·": r"$\cdot$", "‖": r"$\Vert$", "⟂": r"$\perp$", "∥": r"$\parallel$", "∛": r"$\sqrt[3]{\cdot}$", "∞": r"$\infty$", "²": r"$^2$", "ᵀ": r"$^T$", "…": "...", "°": r"$^\circ$",
        "≫": r"$\gg$", "∈": r"$\in$", "⁻": r"$^-$", "¹": r"$^1$", "á": "\\'a", "é": "\\'e", "í": "\\'i", "ó": "\\'o", "ú": "\\'u", "ñ": "\\~n", "Á": "\\'A"}


def tex(s) -> str:
    """Escapa texto plano para LaTeX (para matemática usar `mat`, `num`, `vectex`)."""
    return "".join(_ESC.get(c, _UNI.get(c, c)) for c in str(s))


def mat(s) -> str:
    return f"${s}$"


def num(x, nd=3) -> str:
    """Número en notación científica LaTeX, 'n/d' si no es finito."""
    if x is None:
        return "n/d"
    x = float(x)
    if math.isnan(x):
        return "n/d"
    if math.isinf(x):
        return r"$\infty$" if x > 0 else r"$-\infty$"
    if x == 0.0:
        return "$0$"
    exp = int(math.floor(math.log10(abs(x))))
    if -3 <= exp <= 3:
        return f"${x:.{nd}g}$"
    m = x / 10 ** exp
    return rf"${m:.{max(nd - 1, 1)}f}\times10^{{{exp}}}$"


def vectex(v, nd=4) -> str:
    return "$[" + ",\\,".join(f"{float(x):.{nd}g}" for x in np.asarray(v).ravel()) + "]$"


def tabla_latex(encabezados, filas, spec, caption=None, label=None, tam=r"\scriptsize", nota=None, ajustar=False, largo=False) -> str:
    """Tabla booktabs. Las celdas ya deben venir escapadas/formateadas (usar tex(), num(), mat()).

    ajustar=True envuelve en \\resizebox{\\linewidth}{!}{} (graphicx); largo=True usa longtable (varias páginas).
    """
    cab = " & ".join(rf"\textbf{{{h}}}" for h in encabezados) + r" \\"
    cuerpo = [" & ".join(str(c) for c in f) + r" \\" for f in filas]
    pie = rf"{{\tiny {nota}}}" if nota else None
    if largo:
        salida = [r"% Generado por hito3.validacion; requiere \usepackage{booktabs,longtable,array}", r"\begingroup", tam, r"\setlength{\tabcolsep}{2.5pt}", r"\renewcommand{\arraystretch}{1.12}",
                  rf"\begin{{longtable}}{{{spec}}}"]
        if caption:
            salida.append(rf"\caption{{{caption}}}" + (rf"\label{{{label}}}" if label else "") + r"\\")
        salida += [r"\toprule", cab, r"\midrule", r"\endfirsthead", r"\toprule", cab, r"\midrule", r"\endhead", r"\bottomrule", r"\endfoot", *cuerpo, r"\end{longtable}"]
        if pie:
            salida.append(pie)
        salida.append(r"\endgroup")
        return "\n".join(salida) + "\n"
    salida = [r"% Generado por hito3.validacion; requiere \usepackage{booktabs,array" + (",graphicx" if ajustar else "") + "}", r"\begin{table}[htbp]", r"\centering", tam,
              r"\setlength{\tabcolsep}{3pt}", r"\renewcommand{\arraystretch}{1.15}"]
    if caption:
        salida.append(rf"\caption{{{caption}}}")
    if label:
        salida.append(rf"\label{{{label}}}")
    if ajustar:
        salida.append(r"\resizebox{\linewidth}{!}{%")
    salida += [rf"\begin{{tabular}}{{{spec}}}", r"\toprule", cab, r"\midrule", *cuerpo, r"\bottomrule", r"\end{tabular}"]
    if ajustar:
        salida.append("}")
    if pie:
        salida += [r"\par\vspace{2pt}", pie]
    salida.append(r"\end{table}")
    return "\n".join(salida) + "\n"


def escribir_tex(nombre, contenido):
    rutas.LATEX.mkdir(parents=True, exist_ok=True)
    (rutas.LATEX / nombre).write_text(contenido, encoding="utf-8")
