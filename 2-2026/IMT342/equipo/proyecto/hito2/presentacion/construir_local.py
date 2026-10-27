"""Genera Hito2_en_vivo.html: un solo archivo autocontenido (funciona sin internet; solo las fuentes usan la red).

Uso (desde hito2/presentacion/):  python3 construir_local.py
"""
from pathlib import Path

here = Path(__file__).resolve().parent
page = (here / "index.html").read_text(encoding="utf-8")
for name in ("irb120.js", "app.js"):
    code = (here / name).read_text(encoding="utf-8")
    page = page.replace(f'<script src="{name}"></script>', f"<script>\n{code}\n</script>")
html = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        "<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}"
        "body{margin:0}[hidden]{display:none!important}</style>\n</head>\n<body>\n" + page + "\n</body>\n</html>\n")
out = here / "Hito2_en_vivo.html"
out.write_text(html, encoding="utf-8")
print("escrito", out, f"({len(html) // 1024} KB)")
