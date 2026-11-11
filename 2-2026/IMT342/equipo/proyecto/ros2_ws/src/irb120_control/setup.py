from setuptools import find_packages,setup
setup(name='irb120_control',version='0.1.0',packages=find_packages(),
      data_files=[('share/ament_index/resource_index/packages',['resource/irb120_control']),
                  ('share/irb120_control',['package.xml','README.md']),
                  ('share/irb120_control/config',['config/sesion_robot.ejemplo.yaml'])],
      package_data={'irb120_control.vendor':['LICENSE.txt','ORIGEN.json']},
      install_requires=['setuptools','numpy','PyYAML','protobuf>=4.21.12,<5'],
      zip_safe=False,maintainer='Equipo IMT-342',maintainer_email='equipo.imt342@example.com',
      description='Control articular individual desde RViz con EGM',license='Apache-2.0',
      entry_points={'console_scripts':['ensayo_articular=irb120_control.arranque:main']})
