// Bloque «Estado del robot»: modo, motores, RAPID, servidor, módulo y lo que falta.
#pragma once

#include <QJsonObject>
#include <QLabel>
#include <QWidget>

namespace irb120_rviz_panel
{

class WidgetEstado : public QWidget
{
  Q_OBJECT

public:
  explicit WidgetEstado(QWidget * padre = nullptr);
  void actualizar(const QJsonObject & estado);
  void sinConexion();

private:
  static void pintar(QLabel * etiqueta, const QString & valor, bool bien);

  QLabel * simulado_;
  QLabel * modo_;
  QLabel * motores_;
  QLabel * rapid_;
  QLabel * servidor_;
  QLabel * modulo_;
  QLabel * ultimo_;
  QLabel * faltas_;
  QLabel * nota_;
};

}  // namespace irb120_rviz_panel
