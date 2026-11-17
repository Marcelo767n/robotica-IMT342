#include "widget_estado.hpp"

#include <QFormLayout>
#include <QJsonArray>
#include <QVBoxLayout>

#include "json_util.hpp"

namespace irb120_rviz_panel
{

WidgetEstado::WidgetEstado(QWidget * padre)
: QWidget(padre)
{
  auto * caja = new QVBoxLayout(this);
  caja->setContentsMargins(0, 0, 0, 0);
  simulado_ = new QLabel(QStringLiteral("SIMULADO · sin robot"));
  simulado_->setStyleSheet(QStringLiteral(
      "background:#f59e0b; color:#111; font-weight:bold; padding:3px 8px; border-radius:4px;"));
  simulado_->hide();
  caja->addWidget(simulado_);

  auto * formulario = new QFormLayout();
  formulario->setContentsMargins(0, 0, 0, 0);
  formulario->setVerticalSpacing(2);
  modo_ = new QLabel;
  motores_ = new QLabel;
  rapid_ = new QLabel;
  servidor_ = new QLabel;
  modulo_ = new QLabel;
  ultimo_ = new QLabel;
  formulario->addRow(QStringLiteral("Modo:"), modo_);
  formulario->addRow(QStringLiteral("Motores:"), motores_);
  formulario->addRow(QStringLiteral("RAPID:"), rapid_);
  formulario->addRow(QStringLiteral("ServidorPC:"), servidor_);
  formulario->addRow(QStringLiteral("Módulo:"), modulo_);
  formulario->addRow(QStringLiteral("Último:"), ultimo_);
  caja->addLayout(formulario);

  faltas_ = new QLabel;
  faltas_->setWordWrap(true);
  faltas_->setTextFormat(Qt::RichText);
  caja->addWidget(faltas_);
  nota_ = new QLabel(QStringLiteral(
      "Manual: los motores solo quedan en ON mientras se sostiene el habilitador. "
      "Para motores ON fijos: modo AUTO (./brazo.sh instalar-auto)."));
  nota_->setWordWrap(true);
  nota_->setStyleSheet(QStringLiteral("color:#b45309;"));
  nota_->hide();
  caja->addWidget(nota_);
  sinConexion();
}

void WidgetEstado::pintar(QLabel * etiqueta, const QString & valor, bool bien)
{
  etiqueta->setText(valor);
  etiqueta->setStyleSheet(bien ? QStringLiteral("color:#15803d; font-weight:bold;") :
    QStringLiteral("color:#b91c1c; font-weight:bold;"));
}

void WidgetEstado::actualizar(const QJsonObject & e)
{
  simulado_->setVisible(e.value("simulado").toBool());
  const QString modo = texto(e.value("modo"));
  const QString motores = texto(e.value("motores"));
  const QString rapid = texto(e.value("rapid"));
  QString nombreModo = modo;
  if (modo == "MANR") {
    nombreModo = QStringLiteral("Manual reducido");
  } else if (modo == "MANF") {
    nombreModo = QStringLiteral("Manual 100 %");
  } else if (modo == "AUTO") {
    nombreModo = QStringLiteral("Automático");
  }
  pintar(modo_, nombreModo, modo == "MANR" || modo == "AUTO" || modo == "SIMULADO");
  pintar(motores_, motores == "motoron" ? QStringLiteral("ON") : motores, motores == "motoron");
  pintar(rapid_, rapid == "running" ? QStringLiteral("en ejecución") : rapid, rapid == "running");
  const bool activo = e.value("servidor_activo").toBool();
  pintar(servidor_, activo ? QStringLiteral("activo") : QStringLiteral("inactivo"), activo);
  const QString modulo = texto(e.value("modulo"));
  pintar(modulo_, modulo, modulo != "no_verificado" && modulo != "—");
  ultimo_->setText(texto(e.value("ultimo")));

  const QJsonArray faltas = e.value("faltas").toArray();
  if (e.value("ocupado").toBool()) {
    faltas_->setText(QStringLiteral("<span style='color:#c2410c; font-weight:bold;'>Moviendo: ") +
                     e.value("progreso").toString().toHtmlEscaped() + QStringLiteral("</span>"));
  } else if (faltas.isEmpty()) {
    faltas_->setText(QStringLiteral(
        "<span style='color:#15803d; font-weight:bold;'>Listo para recibir órdenes.</span>"));
  } else {
    QString html = QStringLiteral("<span style='color:#b91c1c;'><b>FALTA:</b><ul style='margin:0;'>");
    for (const auto & falta : faltas) {
      html += QStringLiteral("<li>") + falta.toString().toHtmlEscaped() + QStringLiteral("</li>");
    }
    faltas_->setText(html + QStringLiteral("</ul></span>"));
  }
  nota_->setVisible(modo == "MANR" && motores != "motoron");
}

void WidgetEstado::sinConexion()
{
  simulado_->hide();
  nota_->hide();
  for (QLabel * etiqueta : {modo_, motores_, rapid_, servidor_, modulo_, ultimo_}) {
    etiqueta->setText(QStringLiteral("—"));
    etiqueta->setStyleSheet(QString());
  }
  faltas_->setText(QStringLiteral(
      "<span style='color:#b91c1c; font-weight:bold;'>Sin conexión con irb120_panel_rws "
      "(¿está corriendo ./brazo.sh panel?)</span>"));
}

}  // namespace irb120_rviz_panel
