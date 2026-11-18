#include "widget_verificacion.hpp"

#include <QGridLayout>
#include <QJsonArray>
#include <QVBoxLayout>

#include <cmath>

#include "json_util.hpp"

namespace irb120_rviz_panel
{

namespace
{
enum Estado {Gris = 0, Verde = 1, Rojo = 2};

QString pose(const QVector<double> & p)
{
  if (p.size() != 6) {
    return QStringLiteral("—");
  }
  return QString::asprintf("X %.1f  Y %.1f  Z %.1f mm · roll %.1f°  pitch %.1f°  yaw %.1f°",
           p[0], p[1], p[2], p[3], p[4], p[5]);
}

double numero(const QJsonObject & o, const char * clave)
{
  const QJsonValue v = o.value(QLatin1String(clave));
  return v.isDouble() ? v.toDouble() : std::nan("");
}
}  // namespace

WidgetVerificacion::WidgetVerificacion(QWidget * padre)
: QWidget(padre)
{
  auto * caja = new QVBoxLayout(this);
  caja->setContentsMargins(0, 0, 0, 0);
  auto * rejilla = new QGridLayout();
  rejilla->setContentsMargins(0, 0, 0, 0);
  rejilla->setHorizontalSpacing(6);
  rejilla->setVerticalSpacing(3);
  rejilla->setColumnStretch(2, 1);
  ikFk_ = crearFila(rejilla, 0, QStringLiteral("1 · IK → FK (cálculo)"));
  robot_ = crearFila(rejilla, 1, QStringLiteral("2 · Robot real → pose deseada"));
  controlador_ = crearFila(rejilla, 2, QStringLiteral("3 · Modelo vs controlador ABB"));
  desglose_ = new QLabel;
  desglose_->setStyleSheet(QStringLiteral("color:#374151;"));
  rejilla->addWidget(desglose_, 5, 1, 1, 2);   // justo bajo la fila 2 (cada fila ocupa 3 renglones)
  caja->addLayout(rejilla);

  // Tabla por eje: objetivo, medido, error y error relativo al recorrido de la última orden.
  auto * tabla = new QGridLayout();
  tabla->setContentsMargins(0, 4, 0, 0);
  tabla->setHorizontalSpacing(10);
  tabla->setVerticalSpacing(1);
  const QStringList cabeceras{QString(), QStringLiteral("Objetivo °"), QStringLiteral("Medido °"),
    QStringLiteral("Error °"), QStringLiteral("Error %")};
  for (int c = 0; c < cabeceras.size(); ++c) {
    auto * cab = new QLabel(cabeceras[c]);
    cab->setStyleSheet(QStringLiteral("color:#6b7280; font-size:8pt;"));
    tabla->addWidget(cab, 0, c, c == 0 ? Qt::AlignLeft : Qt::AlignRight);
  }
  for (int i = 0; i < 6; ++i) {
    auto * nombre = new QLabel(QStringLiteral("J%1").arg(i + 1));
    nombre->setStyleSheet(QStringLiteral("font-weight:bold;"));
    tabla->addWidget(nombre, i + 1, 0);
    QVector<QLabel *> fila;
    for (int c = 1; c <= 4; ++c) {
      auto * celda = new QLabel(QStringLiteral("—"));
      celda->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
      tabla->addWidget(celda, i + 1, c);
      fila.append(celda);
    }
    ejes_.append(fila);
  }
  caja->addLayout(tabla);

  auto * fila = new QHBoxLayout();
  limites_ = new QLabel;
  alcanzable_ = new QLabel;
  fila->addWidget(limites_);
  fila->addSpacing(12);
  fila->addWidget(alcanzable_);
  fila->addStretch(1);
  caja->addLayout(fila);

  veredicto_ = new QLabel;
  veredicto_->setWordWrap(true);
  caja->addWidget(veredicto_);
  tolerancias_ = new QLabel;
  tolerancias_->setWordWrap(true);
  tolerancias_->setStyleSheet(QStringLiteral("color:#6b7280; font-size:8pt;"));
  caja->addWidget(tolerancias_);

  resalte_.setSingleShot(true);
  resalte_.setInterval(2500);
  connect(&resalte_, &QTimer::timeout, this, [this]() {
      robot_.valores->setStyleSheet(QString());
    });
  sinConexion();
}

WidgetVerificacion::Fila WidgetVerificacion::crearFila(QGridLayout * rejilla, int fila, const QString & titulo)
{
  Fila salida{new QLabel, new QLabel};
  salida.indicador->setFixedSize(14, 14);
  auto * nombre = new QLabel(titulo);
  nombre->setStyleSheet(QStringLiteral("font-weight:bold;"));
  salida.valores->setWordWrap(false);   // saltos de línea explícitos: altura fija y sin cortes
  rejilla->addWidget(salida.indicador, fila * 3, 0, Qt::AlignTop);
  rejilla->addWidget(nombre, fila * 3, 1, 1, 2);
  rejilla->addWidget(salida.valores, fila * 3 + 1, 1, 1, 2);
  return salida;
}

void WidgetVerificacion::pintarFila(const Fila & fila, const QString & texto, int estado)
{
  const char * color = estado == Verde ? "#15803d" : estado == Rojo ? "#b91c1c" : "#9ca3af";
  fila.indicador->setStyleSheet(QStringLiteral("background:%1; border-radius:7px;").arg(QLatin1String(color)));
  fila.valores->setText(texto);
}

void WidgetVerificacion::sinConexion()
{
  desglose_->clear();
  for (auto & fila : ejes_) {
    for (QLabel * celda : fila) {
      celda->setText(QStringLiteral("—"));
      celda->setStyleSheet(QString());
    }
  }
  ultima_ = {};
  permitido_ = false;
  motivo_ = QStringLiteral("sin conexión con irb120_panel_rws");
  for (const Fila * f : {&ikFk_, &robot_, &controlador_}) {
    pintarFila(*f, QStringLiteral("—"), Gris);
  }
  limites_->setText(QStringLiteral("Límites: —"));
  alcanzable_->setText(QStringLiteral("Alcanzable: —"));
  veredicto_->setText(QStringLiteral("<span style='color:#6b7280;'>Sin verificación</span>"));
  tolerancias_->clear();
}

void WidgetVerificacion::actualizar(const QJsonObject & estado)
{
  const QJsonValue valor = estado.value("verificacion");
  if (!valor.isObject()) {
    sinConexion();
    motivo_ = QStringLiteral("el nodo no envía verificación");
    veredicto_->setText(QStringLiteral(
        "<span style='color:#b91c1c; font-weight:bold; font-size:11pt;'>ENVÍO BLOQUEADO: %1</span>")
        .arg(motivo_.toHtmlEscaped()));
    return;
  }
  const QJsonObject v = valor.toObject();
  ultima_ = v;
  const QJsonObject tol = v.value("tolerancias").toObject();

  const QJsonObject ik = v.value("ik_fk").toObject();
  if (ik.isEmpty()) {
    pintarFila(ikFk_, v.value("origen").toString() == QStringLiteral("angulos") ?
      QStringLiteral("— (objetivo escrito en ángulos: la pose deseada es su FK)") : QStringLiteral("—"), Gris);
  } else {
    pintarFila(ikFk_, QString::asprintf("posición %.4f mm · orientación %.4f°",
      numero(ik, "pos_mm"), numero(ik, "rot_deg")), ik.value("ok").toBool() ? Verde : Rojo);
  }

  const QJsonObject rb = v.value("robot").toObject();
  if (rb.isEmpty()) {
    pintarFila(robot_, QStringLiteral("— (sin lectura del robot)"), Gris);
  } else {
    pintarFila(robot_, QString::asprintf("posición %.3f mm · orientación %.3f°\nmáx. error articular %.3f°",
      numero(rb, "pos_mm"), numero(rb, "rot_deg"), numero(rb, "max_eje_deg")),
      rb.value("ok").toBool() ? Verde : Rojo);
  }

  if (rb.isEmpty()) {
    desglose_->clear();
  } else {
    const double pct = numero(rb, "pos_pct");
    desglose_->setText(QString::asprintf("dx %+.3f  dy %+.3f  dz %+.3f mm\n", numero(rb, "dx_mm"),
      numero(rb, "dy_mm"), numero(rb, "dz_mm")) + (std::isfinite(pct) ?
      QStringLiteral("%1 % del recorrido").arg(pct, 0, 'f', 2) : QStringLiteral("% del recorrido: —")));
  }
  const QJsonArray ejes = v.value("ejes").toArray();
  for (int i = 0; i < 6; ++i) {
    const QJsonObject e = i < ejes.size() ? ejes[i].toObject() : QJsonObject();
    const double obj = numero(e, "objetivo");
    const double med = numero(e, "medido");
    const double err = numero(e, "error_deg");
    const double pct = numero(e, "error_pct");
    auto fmt = [](double x, int d, const char * suf = "") {
        return std::isfinite(x) ? QString::number(x, 'f', d) + QLatin1String(suf) : QStringLiteral("—");
      };
    ejes_[i][0]->setText(fmt(obj, 2));
    ejes_[i][1]->setText(fmt(med, 3));
    ejes_[i][2]->setText(std::isfinite(err) ? QString::asprintf("%+.3f", err) : QStringLiteral("—"));
    ejes_[i][3]->setText(fmt(pct, 2, " %"));
    const bool bien = !std::isfinite(err) || std::abs(err) <= 0.1;
    const QString estilo = bien ? QStringLiteral("color:#15803d;") : QStringLiteral("color:#b91c1c; font-weight:bold;");
    ejes_[i][2]->setStyleSheet(estilo);
    ejes_[i][3]->setStyleSheet(estilo);
  }

  const QJsonObject ct = v.value("controlador").toObject();
  if (ct.isEmpty()) {
    pintarFila(controlador_, QStringLiteral("— (sin dato del controlador)"), Gris);
  } else if (!ct.value("valida").toBool(true)) {
    pintarFila(controlador_, QStringLiteral("en movimiento / sin dato\n%1").arg(texto(ct.value("fuente"))), Gris);
  } else {
    pintarFila(controlador_, QString::asprintf("posición %.3f mm · orientación %.3f°\n",
      numero(ct, "pos_mm"), numero(ct, "rot_deg")) +
      QStringLiteral("%1, hace %2 s").arg(texto(ct.value("fuente"))).arg(numero(ct, "edad_s"), 0, 'f', 1),
      ct.value("ok").toBool() ? Verde : Rojo);
  }

  const bool limites = v.value("limites_ok").toBool();
  const bool alcanzable = v.value("alcanzable").toBool();
  limites_->setText(QStringLiteral("Límites: <b style='color:%1;'>%2</b>")
    .arg(limites ? "#15803d" : "#b91c1c", limites ? "OK" : "fuera"));
  alcanzable_->setText(QStringLiteral("Alcanzable: <b style='color:%1;'>%2</b>")
    .arg(alcanzable ? "#15803d" : "#b91c1c", alcanzable ? "sí" : "no"));

  permitido_ = v.value("envio_permitido").toBool();
  motivo_ = v.value("motivo").toString();
  veredicto_->setText(permitido_ ?
    QStringLiteral("<span style='color:#15803d; font-weight:bold; font-size:11pt;'>ENVÍO PERMITIDO</span>") :
    QStringLiteral("<span style='color:#b91c1c; font-weight:bold; font-size:11pt;'>ENVÍO BLOQUEADO: %1</span>")
      .arg((motivo_.isEmpty() ? QStringLiteral("sin motivo informado") : motivo_).toHtmlEscaped()));

  const QString textoTol = tol.isEmpty() ? QString() : QString::asprintf(
    "Tolerancias: IK→FK %.3g mm / %.3g° · llegada %.3g mm / %.3g° · modelo %.3g mm / %.3g°",
    numero(tol, "ik_mm"), numero(tol, "ik_deg"), numero(tol, "llegada_mm"), numero(tol, "llegada_deg"),
    numero(tol, "modelo_mm"), numero(tol, "modelo_deg"));
  tolerancias_->setText(QStringLiteral("Pose deseada (%1): %2\n%3")
    .arg(texto(v.value("herramienta")), pose(seis(v.value("pose_deseada"))), textoTol));
  setToolTip(textoTol);
}

void WidgetVerificacion::resaltarLlegada()
{
  robot_.valores->setStyleSheet(QStringLiteral("background:rgba(21,128,61,0.18); font-weight:bold;"));
  resalte_.start();
}

QString WidgetVerificacion::resumenHtml() const
{
  if (ultima_.isEmpty()) {
    return QStringLiteral("<p><b>Sin verificación del nodo.</b></p>");
  }
  const QJsonObject ik = ultima_.value("ik_fk").toObject();
  const QJsonObject ct = ultima_.value("controlador").toObject();
  QString html = QStringLiteral("<p><b>Pose deseada (%1):</b> %2</p><ul>")
    .arg(texto(ultima_.value("herramienta")), pose(seis(ultima_.value("pose_deseada"))));
  html += ik.isEmpty() ? QStringLiteral("<li>IK → FK: — (objetivo en ángulos)</li>") :
    QString::asprintf("<li>IK → FK: %.4f mm · %.4f° (%s)</li>", numero(ik, "pos_mm"), numero(ik, "rot_deg"),
      ik.value("ok").toBool() ? "OK" : "FUERA");
  html += ct.isEmpty() || !ct.value("valida").toBool(true) ?
    QStringLiteral("<li>Modelo vs controlador ABB: sin dato</li>") :
    QString::asprintf("<li>Modelo vs controlador ABB: %.3f mm · %.3f° (%s)</li>", numero(ct, "pos_mm"),
      numero(ct, "rot_deg"), ct.value("ok").toBool() ? "OK" : "FUERA");
  return html + QStringLiteral("</ul>");
}

}  // namespace irb120_rviz_panel
