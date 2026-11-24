// Pestaña «Trayectorias»: lista (vistosas y guardadas), ejecutar/vista previa/pausa/bucle y grabación de puntos.
// No habla con el robot: emite órdenes JSON (trayectoria_ejecutar, grabar_punto...) que el panel reenvía al nodo.
#pragma once

#include <QJsonObject>
#include <QSet>
#include <QString>
#include <QStringList>
#include <QWidget>

class QCheckBox;
class QLabel;
class QLineEdit;
class QListWidget;
class QListWidgetItem;
class QPushButton;

namespace irb120_rviz_panel
{

class WidgetTrayectorias : public QWidget
{
  Q_OBJECT

public:
  explicit WidgetTrayectorias(QWidget * padre = nullptr);
  void actualizar(const QJsonObject & estado);
  void sinConexion();
  void mostrarError(const QString & texto);

signals:
  void ordenPedida(const QString & accion, const QJsonObject & cuerpo);

private:
  void reconstruirLista(const QJsonArray & filas);
  void reconstruirGrabacion(const QJsonArray & puntos);
  void confirmarEjecucion();
  void habilitar();
  QString archivoElegido() const;

  QListWidget * lista_;
  QCheckBox * bucle_;
  QPushButton * vistaPrevia_;
  QPushButton * ejecutar_;
  QPushButton * pausar_;
  QPushButton * reanudar_;
  QPushButton * detenerFinal_;
  QPushButton * cancelar_;
  QLabel * progreso_;
  QLabel * error_;
  QPushButton * capturar_;
  QPushButton * borrarUltimo_;
  QPushButton * vaciar_;
  QListWidget * puntos_;
  QLineEdit * nombre_;
  QCheckBox * bucleGrabado_;
  QPushButton * guardar_;

  QJsonObject ultimo_;
  QString firmaLista_;
  QString firmaPuntos_;
  QSet<QString> archivosVistos_;
  bool conectado_ = false;
  bool guardando_ = false;
  int nPuntos_ = 0;
};

}  // namespace irb120_rviz_panel
