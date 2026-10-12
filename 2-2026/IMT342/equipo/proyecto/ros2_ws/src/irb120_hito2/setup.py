from glob import glob

from setuptools import find_packages, setup

PACKAGE_NAME = "irb120_hito2"

setup(
    name=PACKAGE_NAME,
    version="0.1.0",
    packages=find_packages(exclude=("test",)),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{PACKAGE_NAME}"]),
        (f"share/{PACKAGE_NAME}", ["package.xml"]),
        (f"share/{PACKAGE_NAME}/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools", "numpy"],
    zip_safe=True,
    maintainer="Equipo IMT-342",
    maintainer_email="equipo.imt342@example.com",
    description="Cinematica inversa de Pieper y trayectorias LSPB del ABB IRB 120 (Hito 2).",
    license="Apache-2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "ik_trajectory_node = irb120_hito2.nodes.ik_trajectory_node:main",
            "send_target = irb120_hito2.nodes.send_target:main",
        ],
    },
)
