"""Arranque integrado de gemelo, comunicación y validación FK física de lectura."""
import sys
from irb120_conexion.arranque.comunicacion import main as start


def main(argv=None):
    return start(["--validate-fk", "--rate", "5", *(sys.argv[1:] if argv is None else argv)])


if __name__ == "__main__":
    raise SystemExit(main())
