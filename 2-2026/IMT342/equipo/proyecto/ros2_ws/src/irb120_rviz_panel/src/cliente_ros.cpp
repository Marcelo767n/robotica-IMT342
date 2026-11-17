#include "cliente_ros.hpp"

#include <QJsonDocument>
#include <QMetaObject>

namespace irb120_rviz_panel
{

ClienteRos::ClienteRos(rclcpp::Node::SharedPtr nodo, QObject * padre)
: QObject(padre)
{
  publicador_ = nodo->create_publisher<std_msgs::msg::String>(TOPICO_ORDEN, 10);
  suscripcion_ = nodo->create_subscription<std_msgs::msg::String>(
    TOPICO_ESTADO, 10,
    [this](std_msgs::msg::String::ConstSharedPtr mensaje) {
      // El ejecutor de RViz puede no ser el hilo de la GUI: entregar siempre en cola.
      const QByteArray datos = QByteArray::fromStdString(mensaje->data);
      QMetaObject::invokeMethod(this, [this, datos]() {entregar(datos);}, Qt::QueuedConnection);
    });
}

ClienteRos::~ClienteRos()
{
  suscripcion_.reset();
  publicador_.reset();
}

void ClienteRos::entregar(const QByteArray & datos)
{
  QJsonParseError error{};
  const QJsonDocument documento = QJsonDocument::fromJson(datos, &error);
  if (error.error == QJsonParseError::NoError && documento.isObject()) {
    emit estadoRecibido(documento.object());
  }
}

int ClienteRos::enviar(const QString & accion, QJsonObject cuerpo)
{
  const int id = siguienteId_++;
  cuerpo.insert(QStringLiteral("id"), id);
  cuerpo.insert(QStringLiteral("accion"), accion);
  std_msgs::msg::String mensaje;
  mensaje.data = QJsonDocument(cuerpo).toJson(QJsonDocument::Compact).toStdString();
  publicador_->publish(mensaje);
  return id;
}

}  // namespace irb120_rviz_panel
