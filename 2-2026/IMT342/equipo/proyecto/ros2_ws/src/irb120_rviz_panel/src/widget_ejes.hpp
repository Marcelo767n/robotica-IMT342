// Bloque «Ángulos J1–J6»: medido, objetivo (casilla + deslizador) y cambio por eje.
#pragma once

#include <QDoubleSpinBox>
#include <QElapsedTimer>
#include <QJsonObject>
#include <QLabel>
#include <QSlider>
#include <QTimer>
#include <QVector>
#include <QWidget>

namespace irb120_rviz_panel
{

class WidgetEjes : public QWidget
{
  Q_OBJECT

public:
  static constexpr int EJES = 6;
  static constexpr double ESCALA = 10.0;  // deslizador en décimas de grado

  explicit WidgetEjes(QWidget * padre = nullptr);
  void actualizar(const QJsonObject & estado);
  QVector<double> objetivo() const;
  QVector<double> medido() const {return medido_;}
  void ponerObjetivo(const QVector<double> & valores);
  void setBloqueado(bool bloqueado);

signals:
  // Tras 150 ms sin más cambios del usuario.
  void objetivoEditado(const QVector<double> & valores);

private:
  void editado(int eje, double valor, bool desdeDeslizador);
  bool usuarioEditando() const;
  void pintarCambios();

  QVector<QLabel *> medidos_;
  QVector<QDoubleSpinBox *> casillas_;
  QVector<QSlider *> deslizadores_;
  QVector<QLabel *> cambios_;
  QVector<double> medido_;
  QTimer rebote_;
  QElapsedTimer ultimaEdicion_;
  bool limitesPuestos_ = false;
  bool objetivoPuesto_ = false;
};

}  // namespace irb120_rviz_panel
