from glob import glob
from pathlib import Path

from setuptools import find_packages, setup


PACKAGE_NAME = "irb120_hito1"


def package_files(directory: str) -> list[tuple[str, list[str]]]:
    """Collect non-Python resources while preserving their package layout."""
    result: list[tuple[str, list[str]]] = []
    root = Path(directory)
    for path in sorted(root.rglob("*")):
        if path.is_file():
            destination = Path("share") / PACKAGE_NAME / path.parent
            result.append((str(destination), [str(path)]))
    return result


setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=("test",)),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        *package_files("urdf"),
        *package_files("launch"),
        *package_files("config"),
        *package_files("rviz"),
    ],
    install_requires=["setuptools", "numpy"],
    zip_safe=True,
    maintainer="Equipo IMT-342",
    maintainer_email="equipo.imt342@example.com",
    description="Gemelo digital y cinematica directa del ABB IRB 120 para el Hito 1.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "fk_validator = irb120_hito1.nodes.fk_validator:main",
            "joint_state_source = irb120_hito1.nodes.joint_state_source:main",
            "verify_model = irb120_hito1.verify_model:main",
        ],
    },
)
