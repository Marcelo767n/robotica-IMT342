cmake_minimum_required(VERSION 3.16)
project(irb120_rviz_panel LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)

find_package(ament_cmake REQUIRED)
find_package(pluginlib REQUIRED)
find_package(class_loader REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rviz_common REQUIRED)
find_package(std_msgs REQUIRED)
find_package(Qt5 REQUIRED COMPONENTS Widgets)

add_library(${PROJECT_NAME} SHARED
  src/json_util.hpp
  src/cliente_ros.hpp src/cliente_ros.cpp
  src/widget_estado.hpp src/widget_estado.cpp
  src/widget_ejes.hpp src/widget_ejes.cpp
  src/widget_pose.hpp src/widget_pose.cpp
  src/widget_verificacion.hpp src/widget_verificacion.cpp
  src/widget_velocidad.hpp src/widget_velocidad.cpp
  src/widget_trayectorias.hpp src/widget_trayectorias.cpp
  src/panel_irb120.hpp src/panel_irb120.cpp
)
target_compile_options(${PROJECT_NAME} PRIVATE -Wall -Wextra)

# Ubuntu 26 con paquetes de ROS Jazzy (noble): igual que rviz2 y test/rviz_probe de
# irb120_control, se enlaza la biblioteca binaria de rviz_common sin arrastrar las
# dependencias CMake de tinyxml2 del sistema anfitrión. Por eso tampoco se enlaza
# pluginlib::pluginlib (añadiría libtinyxml2.so.11 junto a la .so.10 de rviz_common):
# para exportar la clase basta class_loader.
get_filename_component(ros_prefix "${rviz_common_DIR}/../../.." ABSOLUTE)
file(GLOB ros_headers LIST_DIRECTORIES true "${ros_prefix}/include/*")
target_include_directories(${PROJECT_NAME} SYSTEM PRIVATE ${ros_headers})
get_target_property(rviz_common_library rviz_common::rviz_common IMPORTED_LOCATION_NONE)
target_link_libraries(${PROJECT_NAME}
  "${rviz_common_library}"
  rclcpp::rclcpp
  ${std_msgs_TARGETS}
  class_loader::class_loader
  Qt5::Widgets
  rviz_ogre_vendor::OgreMain)

pluginlib_export_plugin_description_file(rviz_common plugins_description.xml)

install(TARGETS ${PROJECT_NAME}
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin)

ament_package()
