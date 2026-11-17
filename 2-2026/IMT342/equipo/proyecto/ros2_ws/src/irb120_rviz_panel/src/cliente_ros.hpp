// Conexión ROS del panel: recibe el estado (JSON) del nodo irb120_panel_rws y publica órdenes.
#pragma once

#include <QJsonObject>
#include <QObject>

#include <rclcpp/rclcpp.hpp>
#include <std_msgs/msg/string.hpp>

namespace irb120_rviz_panel
{

class ClienteRos : public QObject
{
  Q_OBJECT

public:
  static constexpr const char * TOPICO_ESTADO = "/irb120/panel/estado";
  static constexpr const char * TOPICO_ORDEN = "/irb120/panel/orden";

  ClienteRos(rclcpp::Node::SharedPtr nodo, QObject * padre = nullptr);
  ~ClienteRos() override;

  // Publica {"id": n, "accion": accion, ...cuerpo} y devuelve el id usado.
  int enviar(const QString & accion, QJsonObject cuerpo = {});

signals:
  void estadoRecibido(const QJsonObject & estado);

private:
  void entregar(const QByteArray & datos);

  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr suscripcion_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publicador_;
  int siguienteId_ = 1;
};

}  // namespace irb120_rviz_panel
