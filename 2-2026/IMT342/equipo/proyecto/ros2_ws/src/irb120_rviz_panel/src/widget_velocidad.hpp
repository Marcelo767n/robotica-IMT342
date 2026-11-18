// Bloque «Velocidad»: porcentaje 1–100 que el nodo aplica a la siguiente orden del robot.
#pragma once

#include <QJsonObject>
#include <QLabel>
#include <QTimer>
#include <QWidget>

class QSlider;
class QSpinBox;

namespace irb120_rviz_panel
{

class WidgetVelocidad : public QWidget
{
  Q_OBJECT

public:
  explicit WidgetVelocidad(QWidget * padre = nullptr);
  void actualizar(const QJsonObject & estado);
  void setBloqueado(bool bloqueado);

signals:
  void velocidadElegida(int porcentaje);

private:
  void poner(int pct);          // cambio hecho por el usuario: reinicia el debounce
  void mostrar(int pct, double mm_s, double deg_s);
  bool editando() const;

  QSlider * deslizador_;
  QSpinBox * numero_;
  QLabel * equivalencia_;
  QLabel * aviso_;
  QTimer debounce_;
};

}  // namespace irb120_rviz_panel
