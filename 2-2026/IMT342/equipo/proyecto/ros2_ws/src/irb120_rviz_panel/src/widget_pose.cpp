#include "widget_pose.hpp"

#include <QFormLayout>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QHeaderView>
#include <QJsonArray>
#include <QSignalBlocker>
#include <QVBoxLayout>

#include "json_util.hpp"

namespace irb120_rviz_panel
{

WidgetPose::WidgetPose(QWidget * padre)
: QWidget(padre)
{
  auto * caja = new QVBoxLayout(this);
  caja->setContentsMargins(0, 0, 0, 0);

  auto * lectura = new QFormLayout();
  lectura->setVerticalSpacing(2);
  herramienta_ = new QComboBox;
  herramienta_->addItem(QStringLiteral("TCP del proyecto (150 mm)"), QStringLiteral("tcp"));
  herramienta_->addItem(QStringLiteral("Brida (tool0)"), QStringLiteral("brida"));
  poseMedida_ = new QLabel(QStringLiteral("—"));
  poseObjetivo_ = new QLabel(QStringLiteral("—"));
  poseMedida_->setWordWrap(true);
  poseObjetivo_->setWordWrap(true);
  lectura->addRow(QStringLiteral("Punto:"), herramienta_);
  lectura->addRow(QStringLiteral("Pose medida:"), poseMedida_);
  lectura->addRow(QStringLiteral("Pose objetivo:"), poseObjetivo_);
  caja->addLayout(lectura);

  auto * rejilla = new QGridLayout();
  rejilla->setHorizontalSpacing(6);
  const QStringList nombres = {"X (mm)", "Y (mm)", "Z (mm)", "Roll · Rx (°)", "Pitch · Ry (°)", "Yaw · Rz (°)"};
  for (int i = 0; i < 6; ++i) {
    auto * campo = new QDoubleSpinBox;
    campo->setDecimals(i < 3 ? 1 : 2);
    campo->setRange(i < 3 ? -1500.0 : -180.0, i < 3 ? 1500.0 : 180.0);
    campo->setSingleStep(i < 3 ? 5.0 : 1.0);
    campo->setKeyboardTracking(false);
    rejilla->addWidget(new QLabel(nombres[i]), (i / 3) * 2, i % 3);
    rejilla->addWidget(campo, (i / 3) * 2 + 1, i % 3);
    campos_.append(campo);
  }
  caja->addLayout(rejilla);

  auto * botones = new QHBoxLayout();
  calcular_ = new QPushButton(QStringLiteral("Calcular ángulos (IK)"));
  copiar_ = new QPushButton(QStringLiteral("Copiar pose medida"));
  botones->addWidget(calcular_);
  botones->addWidget(copiar_);
  caja->addLayout(botones);
  auto * ayuda = new QLabel(QStringLiteral(
      "Respecto a la base; R = Rz·Ry·Rx. Calcular solo cambia el objetivo naranja: "
      "revisar en la vista 3D y luego «Enviar al robot»."));
  ayuda->setWordWrap(true);
  ayuda->setStyleSheet(QStringLiteral("color:gray; font-size:small;"));
  caja->addWidget(ayuda);

  veredicto_ = new QLabel;
  veredicto_->setWordWrap(true);
  caja->addWidget(veredicto_);
  ramas_ = new QTableWidget(0, 12);
  ramas_->setHorizontalHeaderLabels({QStringLiteral("Rama"), QStringLiteral("Brazo"),
      QStringLiteral("Codo"), QStringLiteral("Muñeca"), "J1", "J2", "J3", "J4", "J5", "J6",
      QStringLiteral("Cambio"), QStringLiteral("Estado")});
  ramas_->setEditTriggers(QAbstractItemView::NoEditTriggers);
  ramas_->setSelectionBehavior(QAbstractItemView::SelectRows);
  ramas_->setSelectionMode(QAbstractItemView::SingleSelection);
  ramas_->verticalHeader()->hide();
  ramas_->horizontalHeader()->setSectionResizeMode(QHeaderView::ResizeToContents);
  ramas_->setMinimumHeight(120);
  ramas_->setToolTip(QStringLiteral("Doble clic en una rama utilizable para usarla como objetivo."));
  ramas_->hide();
  caja->addWidget(ramas_);

  connect(herramienta_, QOverload<int>::of(&QComboBox::activated), this, [this](int indice) {
      emit herramientaElegida(herramienta_->itemData(indice).toString());
      camposPuestos_ = false;   // rellenar con la pose del nuevo punto
    });
  connect(calcular_, &QPushButton::clicked, this, [this]() {
      QVector<double> pose;
      for (const auto * campo : campos_) {
        pose.append(campo->value());
      }
      emit calcular(pose);
    });
  connect(copiar_, &QPushButton::clicked, this, [this]() {
      for (int i = 0; i < 6 && poseMedidaActual_.size() == 6; ++i) {
        campos_[i]->setValue(poseMedidaActual_[i]);
      }
    });
  connect(ramas_, &QTableWidget::cellDoubleClicked, this, [this](int fila, int) {usarFila(fila);});
}

QString WidgetPose::textoPose(const QVector<double> & p)
{
  if (p.size() != 6) {
    return QStringLiteral("—");
  }
  return QString::asprintf("X %.1f  Y %.1f  Z %.1f mm · roll %.1f°  pitch %.1f°  yaw %.1f°",
           p[0], p[1], p[2], p[3], p[4], p[5]);
}

void WidgetPose::actualizar(const QJsonObject & estado)
{
  poseMedidaActual_ = seis(estado.value("pose_medida"));
  const QVector<double> objetivo = seis(estado.value("pose_objetivo"));
  poseMedida_->setText(textoPose(poseMedidaActual_));
  poseObjetivo_->setText(textoPose(objetivo));
  const int indice = herramienta_->findData(estado.value("herramienta").toString());
  if (indice >= 0 && !herramienta_->view()->isVisible()) {
    const QSignalBlocker bloqueo(herramienta_);
    herramienta_->setCurrentIndex(indice);
  }
  if (!camposPuestos_ && objetivo.size() == 6) {
    for (int i = 0; i < 6; ++i) {
      campos_[i]->setValue(objetivo[i]);
    }
    camposPuestos_ = true;
  }
  copiar_->setEnabled(poseMedidaActual_.size() == 6);
  const QJsonObject ik = estado.value("ik").toObject();
  if (!ik.isEmpty() && ik.value("id").toInt(-1) != ikMostrado_) {
    ikMostrado_ = ik.value("id").toInt(-1);
    mostrarIk(ik);
  }
}

void WidgetPose::mostrarIk(const QJsonObject & ik)
{
  const bool hay = ik.value("elegida").isDouble();
  veredicto_->setText(ik.value("veredicto").toString());
  veredicto_->setStyleSheet(hay ? QStringLiteral("color:#15803d; font-weight:bold;") :
    QStringLiteral("color:#b91c1c; font-weight:bold;"));
  const int elegida = ik.value("elegida").toInt(-1);
  const QJsonArray ramas = ik.value("ramas").toArray();
  ramas_->setRowCount(ramas.size());
  qRamas_.clear();
  for (int fila = 0; fila < ramas.size(); ++fila) {
    const QJsonObject r = ramas[fila].toObject();
    const QVector<double> q = seis(r.value("q"));
    const bool usable = r.value("usable").toBool() && q.size() == 6;
    qRamas_.append(usable ? q : QVector<double>());
    QStringList celdas = {texto(r.value("rama")), texto(r.value("brazo")), texto(r.value("codo")),
      texto(r.value("muneca"))};
    for (int j = 0; j < 6; ++j) {
      celdas << (q.size() == 6 ? QString::number(q[j], 'f', 1) : QStringLiteral("—"));
    }
    celdas << (r.value("cambio_max").isDouble() ?
      QString::number(r.value("cambio_max").toDouble(), 'f', 1) + QStringLiteral("°") : QStringLiteral("—"));
    celdas << (usable ? QStringLiteral("%1 · doble clic = usar").arg(texto(r.value("estado"))) :
      texto(r.value("estado")));
    const bool esElegida = r.value("rama").toInt(-2) == elegida;
    for (int c = 0; c < celdas.size(); ++c) {
      auto * celda = new QTableWidgetItem(celdas[c]);
      if (esElegida) {
        QFont fuente = celda->font();
        fuente.setBold(true);
        celda->setFont(fuente);
        celda->setBackground(QColor(194, 65, 12, 60));
      } else if (!usable) {
        celda->setForeground(Qt::gray);
      }
      ramas_->setItem(fila, c, celda);
    }
  }
  ramas_->setVisible(!ramas.isEmpty());
}

void WidgetPose::usarFila(int fila)
{
  if (fila >= 0 && fila < qRamas_.size() && !qRamas_[fila].isEmpty() && calcular_->isEnabled()) {
    emit usarRama(qRamas_[fila]);
    for (int f = 0; f < ramas_->rowCount(); ++f) {
      for (int c = 0; c < ramas_->columnCount(); ++c) {
        if (auto * celda = ramas_->item(f, c)) {
          QFont fuente = celda->font();
          fuente.setBold(f == fila);
          celda->setFont(fuente);
          celda->setBackground(f == fila ? QColor(194, 65, 12, 60) : QColor(Qt::transparent));
        }
      }
    }
  }
}

void WidgetPose::setBloqueado(bool bloqueado)
{
  herramienta_->setEnabled(!bloqueado);
  calcular_->setEnabled(!bloqueado);
  for (auto * campo : campos_) {
    campo->setEnabled(!bloqueado);
  }
}

}  // namespace irb120_rviz_panel
