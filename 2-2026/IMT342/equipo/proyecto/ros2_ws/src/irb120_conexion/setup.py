from setuptools import find_packages, setup

setup(
    name="irb120_conexion", version="0.1.0", packages=find_packages(),
    data_files=[("share/ament_index/resource_index/packages", ["resource/irb120_conexion"]),
                ("share/irb120_conexion", ["package.xml", "README.md"])],
    package_data={"irb120_conexion": ["nodos/monitor_comunicacion/panel.html", "nodos/validacion_fk/panel.html"]},
    install_requires=["setuptools", "numpy", "PyYAML", "requests"],
    zip_safe=False, maintainer="Equipo IMT-342", maintainer_email="equipo.imt342@example.com",
    description="Conexión y validación FK de solo lectura del ABB IRB 120", license="Apache-2.0",
    entry_points={"console_scripts": [
        "puente_rws = irb120_conexion.nodos.lectura_articular.puente_rws:main",
        "monitor_comunicacion = irb120_conexion.nodos.monitor_comunicacion.monitor:main",
        "validacion_fk = irb120_conexion.nodos.validacion_fk.nodo:main",
        "prueba_comunicacion = irb120_conexion.arranque.comunicacion:main",
        "prueba_fk = irb120_conexion.arranque.validacion_fk:main",
    ]},
)
