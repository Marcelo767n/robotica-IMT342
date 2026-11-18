#include "widget_velocidad.hpp"

#include <QHBoxLayout>
#include <QPushButton>
#include <QSlider>
#include <QSpinBox>
#include <QVBoxLayout>

#include <cmath>

namespace irb120_rviz_panel
{

WidgetVelocidad::WidgetVelocidad(QWidget * padre)
: QWidget(padre)
{
  auto * caja = new QVBoxLayout(this);
  caja->setContentsMargins(0, 0, 0, 0);

  auto * fila = new QHBoxLayout();
  deslizador_ = new QSlider(Qt::Horizontal);
  deslizador_->setRange(1, 100);
  deslizador_->setValue(10);
  numero_ = new QSpinBox;
  numero_->setRange(1, 100);
  numero_->setSuffix(QStringLiteral(" %"));
  numero_->setValue(10);
  fila->addWidget(deslizador_, 1);
  fila->addWidget(numero_);
  caja->addLayout(fila);

  auto * rapidos = new QHBoxLayout();
  for (int pct : {10, 25, 50, 75, 100}) {
    auto * boton = new QPushButton(QStringLiteral("%1 %").arg(pct));
    connect(boton, &QPushButton::clicked, this, [this, pct]() {poner(pct);});
    rapidos->addWidget(boton);
  }
  caja->addLayout(rapidos);

  equivalencia_ = new QLabel;
  caja->addWidget(equivalencia_);
  aviso_ = new QLabel(QStringLiteral("Velocidad alta: celda despejada"));
  aviso_->setStyleSheet(QStringLiteral("color:#c2410c; font-weight:bold;"));
  aviso_->hide();
  caja->addWidget(aviso_);

  debounce_.setSingleShot(true);
  debounce_.setInterval(300);
  connect(&debounce_, &QTimer::timeout, this, [this]() {emit velocidadElegida(numero_->value());});

  // El slider arrastrado solo envía al soltarlo; con teclado o rueda, tras el debounce.
  connect(deslizador_, &QSlider::valueChanged, this, [this](int v) {
      numero_->blockSignals(true);
      numero_->setValue(v);
      numero_->blockSignals(false);
      mostrar(v, 2.5 * v, 0.6 * v);
      if (!deslizador_->isSliderDown()) {
        debounce_.start();
      }
    });
  connect(deslizador_, &QSlider::sliderReleased, this, [this]() {debounce_.start();});
  connect(numero_, QOverload<int>::of(&QSpinBox::valueChanged), this, [this](int v) {
      deslizador_->blockSignals(true);
      deslizador_->setValue(v);
      deslizador_->blockSignals(false);
      mostrar(v, 2.5 * v, 0.6 * v);
      debounce_.start();
    });
  mostrar(10, 25.0, 6.0);
}

bool WidgetVelocidad::editando() const
{
  return deslizador_->isSliderDown() || debounce_.isActive() || numero_->hasFocus();
}

void WidgetVelocidad::poner(int pct)
{
  numero_->setValue(pct);   // dispara valueChanged → debounce (si ya valía lo mismo, reenvía igual)
  debounce_.start();
}

void WidgetVelocidad::mostrar(int pct, double mm_s, double deg_s)
{
  equivalencia_->setText(QStringLiteral("≈ %1 mm/s · %2 °/s")
    .arg(mm_s, 0, 'f', 1).arg(deg_s, 0, 'f', 1));
  aviso_->setVisible(pct > 50);
}

void WidgetVelocidad::actualizar(const QJsonObject & estado)
{
  const QJsonValue v = estado.value("velocidad_pct");
  if (!v.isDouble() || editando()) {
    return;
  }
  const int pct = std::clamp(static_cast<int>(std::lround(v.toDouble())), 1, 100);
  const QJsonValue mm = estado.value("velocidad_mm_s");
  const QJsonValue dg = estado.value("velocidad_deg_s");
  deslizador_->blockSignals(true);
  numero_->blockSignals(true);
  deslizador_->setValue(pct);
  numero_->setValue(pct);
  deslizador_->blockSignals(false);
  numero_->blockSignals(false);
  mostrar(pct, mm.isDouble() ? mm.toDouble() : 2.5 * pct, dg.isDouble() ? dg.toDouble() : 0.6 * pct);
}

void WidgetVelocidad::setBloqueado(bool bloqueado)
{
  setEnabled(!bloqueado);
}

}  // namespace irb120_rviz_panel
