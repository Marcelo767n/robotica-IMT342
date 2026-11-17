#include "widget_ejes.hpp"

#include <QGridLayout>
#include <QJsonArray>
#include <QSignalBlocker>

#include <cmath>

#include "json_util.hpp"

namespace irb120_rviz_panel
{

WidgetEjes::WidgetEjes(QWidget * padre)
: QWidget(padre)
{
  auto * rejilla = new QGridLayout(this);
  rejilla->setContentsMargins(0, 0, 0, 0);
  rejilla->setHorizontalSpacing(6);
  rejilla->setVerticalSpacing(2);
  const QStringList cabecera = {QString(), QStringLiteral("Medido"), QStringLiteral("Objetivo"),
    QString(), QStringLiteral("Cambio")};
  for (int c = 0; c < cabecera.size(); ++c) {
    auto * titulo = new QLabel(cabecera[c]);
    titulo->setStyleSheet(QStringLiteral("color:gray; font-size:small;"));
    rejilla->addWidget(titulo, 0, c);
  }
  for (int i = 0; i < EJES; ++i) {
    auto * nombre = new QLabel(QStringLiteral("<b>J%1</b>").arg(i + 1));
    auto * medido = new QLabel(QStringLiteral("—"));
    medido->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    medido->setMinimumWidth(52);
    auto * casilla = new QDoubleSpinBox;
    casilla->setDecimals(2);
    casilla->setSingleStep(0.5);
    casilla->setSuffix(QStringLiteral("°"));
    casilla->setKeyboardTracking(false);
    casilla->setRange(-400.0, 400.0);
    casilla->setMinimumWidth(76);
    auto * deslizador = new QSlider(Qt::Horizontal);
    deslizador->setRange(-4000, 4000);
    deslizador->setMinimumWidth(40);
    auto * cambio = new QLabel;
    cambio->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
    cambio->setMinimumWidth(48);
    rejilla->addWidget(nombre, i + 1, 0);
    rejilla->addWidget(medido, i + 1, 1);
    rejilla->addWidget(casilla, i + 1, 2);
    rejilla->addWidget(deslizador, i + 1, 3);
    rejilla->addWidget(cambio, i + 1, 4);
    medidos_.append(medido);
    casillas_.append(casilla);
    deslizadores_.append(deslizador);
    cambios_.append(cambio);
    connect(casilla, QOverload<double>::of(&QDoubleSpinBox::valueChanged), this,
      [this, i](double v) {editado(i, v, false);});
    connect(deslizador, &QSlider::valueChanged, this,
      [this, i](int v) {editado(i, v / ESCALA, true);});
  }
  rejilla->setColumnStretch(3, 1);
  rebote_.setSingleShot(true);
  rebote_.setInterval(150);
  connect(&rebote_, &QTimer::timeout, this, [this]() {emit objetivoEditado(objetivo());});
}

void WidgetEjes::editado(int eje, double valor, bool desdeDeslizador)
{
  if (desdeDeslizador) {
    const QSignalBlocker bloqueo(casillas_[eje]);
    casillas_[eje]->setValue(valor);
  } else {
    const QSignalBlocker bloqueo(deslizadores_[eje]);
    deslizadores_[eje]->setValue(static_cast<int>(std::lround(valor * ESCALA)));
  }
  ultimaEdicion_.start();
  pintarCambios();
  rebote_.start();
}

bool WidgetEjes::usuarioEditando() const
{
  if (rebote_.isActive() || (ultimaEdicion_.isValid() && ultimaEdicion_.elapsed() < 800)) {
    return true;
  }
  for (const auto * casilla : casillas_) {
    if (casilla->hasFocus()) {
      return true;
    }
  }
  for (const auto * deslizador : deslizadores_) {
    if (deslizador->isSliderDown()) {
      return true;
    }
  }
  return false;
}

QVector<double> WidgetEjes::objetivo() const
{
  QVector<double> valores;
  for (const auto * casilla : casillas_) {
    valores.append(casilla->value());
  }
  return valores;
}

void WidgetEjes::ponerObjetivo(const QVector<double> & valores)
{
  if (valores.size() != EJES) {
    return;
  }
  for (int i = 0; i < EJES; ++i) {
    const QSignalBlocker b1(casillas_[i]);
    const QSignalBlocker b2(deslizadores_[i]);
    casillas_[i]->setValue(valores[i]);
    deslizadores_[i]->setValue(static_cast<int>(std::lround(valores[i] * ESCALA)));
  }
  objetivoPuesto_ = true;
  pintarCambios();
}

void WidgetEjes::actualizar(const QJsonObject & estado)
{
  const QJsonArray limites = estado.value("limites").toArray();
  if (!limitesPuestos_ && limites.size() == EJES) {
    for (int i = 0; i < EJES; ++i) {
      const QVector<double> par = {limites[i].toArray().at(0).toDouble(-400),
        limites[i].toArray().at(1).toDouble(400)};
      const QSignalBlocker b1(casillas_[i]);
      const QSignalBlocker b2(deslizadores_[i]);
      casillas_[i]->setRange(par[0], par[1]);
      casillas_[i]->setToolTip(QStringLiteral("%1° … %2°").arg(par[0]).arg(par[1]));
      deslizadores_[i]->setRange(static_cast<int>(par[0] * ESCALA), static_cast<int>(par[1] * ESCALA));
    }
    limitesPuestos_ = true;
  }
  medido_ = seis(estado.value("medido"));
  for (int i = 0; i < EJES; ++i) {
    medidos_[i]->setText(medido_.isEmpty() ? QStringLiteral("—") :
      QString::number(medido_[i], 'f', 3) + QStringLiteral("°"));
  }
  // El objetivo también cambia desde los marcadores 3D o la cinemática inversa.
  const QVector<double> remoto = seis(estado.value("objetivo"));
  if (!remoto.isEmpty() && (!objetivoPuesto_ ||
    (!usuarioEditando() && cambioMaximo(remoto, objetivo()) > 1e-6)))
  {
    ponerObjetivo(remoto);
  }
  pintarCambios();
}

void WidgetEjes::pintarCambios()
{
  for (int i = 0; i < EJES; ++i) {
    if (medido_.isEmpty()) {
      cambios_[i]->clear();
      continue;
    }
    const double cambio = casillas_[i]->value() - medido_[i];
    const bool hay = std::abs(cambio) >= 0.005;
    cambios_[i]->setText(hay ? QString::asprintf("%+.2f°", cambio) : QString());
    cambios_[i]->setStyleSheet(hay ? QStringLiteral("color:#c2410c; font-weight:bold;") : QString());
  }
}

void WidgetEjes::setBloqueado(bool bloqueado)
{
  for (int i = 0; i < EJES; ++i) {
    casillas_[i]->setEnabled(!bloqueado);
    deslizadores_[i]->setEnabled(!bloqueado);
  }
}

}  // namespace irb120_rviz_panel
