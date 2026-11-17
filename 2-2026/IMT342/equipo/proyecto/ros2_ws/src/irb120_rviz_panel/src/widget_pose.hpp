// Bloque «Posición cartesiana → ángulos»: punto de referencia, pose pedida y ramas de Pieper.
#pragma once

#include <QComboBox>
#include <QDoubleSpinBox>
#include <QJsonObject>
#include <QLabel>
#include <QPushButton>
#include <QTableWidget>
#include <QVector>
#include <QWidget>

namespace irb120_rviz_panel
{

class WidgetPose : public QWidget
{
  Q_OBJECT

public:
  explicit WidgetPose(QWidget * padre = nullptr);
  void actualizar(const QJsonObject & estado);
  void setBloqueado(bool bloqueado);

signals:
  void herramientaElegida(const QString & herramienta);
  void calcular(const QVector<double> & pose);
  void usarRama(const QVector<double> & q);

private:
  void mostrarIk(const QJsonObject & ik);
  void usarFila(int fila);
  static QString textoPose(const QVector<double> & pose);

  QComboBox * herramienta_;
  QLabel * poseMedida_;
  QLabel * poseObjetivo_;
  QVector<QDoubleSpinBox *> campos_;
  QPushButton * calcular_;
  QPushButton * copiar_;
  QLabel * veredicto_;
  QTableWidget * ramas_;
  QVector<QVector<double>> qRamas_;   // q de cada fila (vacío si no es usable)
  QVector<double> poseMedidaActual_;
  int ikMostrado_ = -1;
  bool camposPuestos_ = false;
};

}  // namespace irb120_rviz_panel
