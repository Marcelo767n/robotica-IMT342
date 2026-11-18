// Panel de RViz «IRB 120»: compone estado, ejes, pose e IK, y las acciones de envío.
// Todo pasa por el nodo irb120_panel_rws (./brazo.sh panel): este panel no habla con el robot.
#pragma once

#include <QComboBox>
#include <QElapsedTimer>
#include <QJsonObject>
#include <QLabel>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QTimer>
#include <QWidget>

#include <rviz_common/panel.hpp>

namespace irb120_rviz_panel
{

class ClienteRos;
class WidgetEjes;
class WidgetEstado;
class WidgetPose;
class WidgetVerificacion;

class PanelIRB120 : public rviz_common::Panel
{
  Q_OBJECT

public:
  explicit PanelIRB120(QWidget * padre = nullptr);
  ~PanelIRB120() override;
  void onInitialize() override;

private:
  QWidget * construirAcciones();
  void recibir(const QJsonObject & estado);
  void vigilar();
  void habilitar();
  void confirmarEnvio();
  void confirmarTerminar();
  void orden(const QString & accion, const QJsonObject & cuerpo = {});

  ClienteRos * ros_ = nullptr;
  WidgetEstado * estado_;
  WidgetEjes * ejes_;
  WidgetPose * pose_;
  WidgetVerificacion * verificacion_;
  QComboBox * paso_;
  QPushButton * posCero_;
  QPushButton * posReposo_;
  QPushButton * enviar_;
  QPushButton * sincronizar_;
  QPushButton * cancelar_;
  QPushButton * terminar_;
  QLabel * progreso_;
  QLabel * error_;
  QPlainTextEdit * registro_;
  QWidget * contenido_;
  QTimer vigilancia_;
  QElapsedTimer ultimoEstado_;
  QJsonObject ultimo_;
  int respuestaVista_ = -1;
  bool conectado_ = false;
  bool estabaOcupado_ = false;
};

}  // namespace irb120_rviz_panel
