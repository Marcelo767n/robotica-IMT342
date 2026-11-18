#include "widget_verificacion.hpp"

#include <QDialog>
#include <QGridLayout>
#include <QHBoxLayout>
#include <QPushButton>
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

  // Ida y vuelta IK(FK(q)): q IK, q recuperado y error por eje.
  auto * titulo = new QLabel(QStringLiteral("<b>Ida y vuelta IK(FK(q))</b>"));
  caja->addWidget(titulo);
  auto * ida = new QGridLayout();
  ida->setContentsMargins(0, 0, 0, 0);
  ida->setHorizontalSpacing(10);
  ida->setVerticalSpacing(1);
  const QStringList cabIda{QString(), QStringLiteral("q IK °"), QStringLiteral("q recuperado °"),
    QStringLiteral("Error °")};
  for (int c = 0; c < cabIda.size(); ++c) {
    auto * cab = new QLabel(cabIda[c]);
    cab->setStyleSheet(QStringLiteral("color:#6b7280; font-size:8pt;"));
    ida->addWidget(cab, 0, c, c == 0 ? Qt::AlignLeft : Qt::AlignRight);
  }
  for (int i = 0; i < 6; ++i) {
    auto * nombre = new QLabel(QStringLiteral("J%1").arg(i + 1));
    nombre->setStyleSheet(QStringLiteral("font-weight:bold;"));
    ida->addWidget(nombre, i + 1, 0);
    QVector<QLabel *> fila;
    for (int c = 1; c <= 3; ++c) {
      auto * celda = new QLabel(QStringLiteral("—"));
      celda->setAlignment(Qt::AlignRight | Qt::AlignVCenter);
      ida->addWidget(celda, i + 1, c);
      fila.append(celda);
    }
    idaVuelta_.append(fila);
  }
  caja->addLayout(ida);
  auto * filaIda = new QHBoxLayout();
  idaVueltaOk_ = new QLabel;
  matrices_ = new QPushButton(QStringLiteral("Ver matrices T"));
  filaIda->addWidget(idaVueltaOk_, 1);
  filaIda->addWidget(matrices_);
  caja->addLayout(filaIda);
  connect(matrices_, &QPushButton::clicked, this, &WidgetVerificacion::mostrarMatrices);

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
  for (auto & fila : idaVuelta_) {
    for (QLabel * celda : fila) {
      celda->setText(QStringLiteral("—"));
      celda->setStyleSheet(QString());
    }
  }
  idaVueltaOk_->setText(QStringLiteral("<span style='color:#6b7280;'>Ida y vuelta: —</span>"));
  matrices_->setEnabled(false);
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
    pintarFila(ikFk_, QString::asprintf("posición %.4f mm · orientación %.4f°\ncriterio ≤ 0,001 mm / 0,001°",
      numero(ik, "pos_mm"), numero(ik, "rot_deg")), ik.value("ok").toBool() ? Verde : Rojo);
  }

  actualizarIdaVuelta(v);

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
    "Tolerancias: IK→FK %.3g mm / %.3g° · ida y vuelta %.3g° · llegada %.3g mm / %.3g° · modelo %.3g mm / %.3g°",
    numero(tol, "ik_mm"), numero(tol, "ik_deg"), numero(tol, "ida_vuelta_deg"), numero(tol, "llegada_mm"), numero(tol, "llegada_deg"),
    numero(tol, "modelo_mm"), numero(tol, "modelo_deg"));
  tolerancias_->setText(QStringLiteral("Pose deseada (%1): %2\n%3")
    .arg(texto(v.value("herramienta")), pose(seis(v.value("pose_deseada"))), textoTol));
  setToolTip(textoTol);
}

void WidgetVerificacion::actualizarIdaVuelta(const QJsonObject & v)
{
  const QJsonValue crudo = v.value("ida_vuelta");
  const QJsonArray filas = crudo.toArray();
  const double tol = [&v]() {
      const double t = numero(v.value("tolerancias").toObject(), "ida_vuelta_deg");
      return std::isfinite(t) ? t : 0.001;
    }();
  bool hayDatos = false;
  for (int i = 0; i < 6; ++i) {
    const QJsonObject f = i < filas.size() ? filas[i].toObject() : QJsonObject();
    const double qik = numero(f, "q_ik");
    const double qrec = numero(f, "q_recuperado");
    const double err = numero(f, "error_deg");
    hayDatos = hayDatos || std::isfinite(qik);
    idaVuelta_[i][0]->setText(std::isfinite(qik) ? QString::number(qik, 'f', 4) : QStringLiteral("—"));
    idaVuelta_[i][1]->setText(std::isfinite(qrec) ? QString::number(qrec, 'f', 4) : QStringLiteral("—"));
    idaVuelta_[i][2]->setText(std::isfinite(err) ? QString::asprintf("%.4f", err) : QStringLiteral("—"));
    idaVuelta_[i][2]->setStyleSheet(!std::isfinite(err) ? QString() :
      std::abs(err) <= tol ? QStringLiteral("color:#15803d;") : QStringLiteral("color:#b91c1c; font-weight:bold;"));
  }
  const QJsonValue ok = v.value("ida_vuelta_ok");
  if (!hayDatos || !ok.isBool()) {
    idaVueltaOk_->setText(QStringLiteral("<span style='color:#6b7280;'>Ida y vuelta: — (objetivo en ángulos o sin IK)</span>"));
  } else {
    idaVueltaOk_->setText(QStringLiteral("<b style='color:%1;'>Ida y vuelta: %2</b> <span style='color:#6b7280;'>(≤ %3°)</span>")
      .arg(ok.toBool() ? "#15803d" : "#b91c1c", ok.toBool() ? "OK" : "FUERA").arg(tol, 0, 'g', 3));
  }
  const QJsonObject m = v.value("matrices").toObject();
  matrices_->setEnabled(m.value("T_pedida").isArray() && m.value("T_fk").isArray());
}

void WidgetVerificacion::mostrarMatrices()
{
  const QJsonObject m = ultima_.value("matrices").toObject();
  const auto leer = [](const QJsonValue & val, double (&t)[4][4]) {
      const QJsonArray a = val.toArray();
      bool ok = a.size() == 4;
      for (int i = 0; i < 4; ++i) {
        const QJsonArray r = ok ? a[i].toArray() : QJsonArray();
        ok = ok && r.size() == 4;
        for (int j = 0; j < 4; ++j) {
          t[i][j] = ok && r[j].isDouble() ? r[j].toDouble() : std::nan("");
        }
      }
      return ok;
    };
  double pedida[4][4];
  double fk[4][4];
  if (!leer(m.value("T_pedida"), pedida) || !leer(m.value("T_fk"), fk)) {
    return;
  }
  auto * dialogo = new QDialog(this);
  dialogo->setAttribute(Qt::WA_DeleteOnClose);
  dialogo->setWindowTitle(QStringLiteral("Matrices T (metros)"));
  auto * capa = new QVBoxLayout(dialogo);
  const auto bloque = [&](const QString & titulo, auto valor) {
      capa->addWidget(new QLabel(QStringLiteral("<b>%1</b>").arg(titulo)));
      auto * rejilla = new QGridLayout();
      rejilla->setHorizontalSpacing(14);
      rejilla->setVerticalSpacing(2);
      for (int i = 0; i < 4; ++i) {
        for (int j = 0; j < 4; ++j) {
          const double x = valor(i, j);
          auto * celda = new QLabel(std::isfinite(x) ? QString::asprintf("%+.4f", x) : QStringLiteral("—"));
          celda->setFont(QFont(QStringLiteral("Monospace"), 9));
          celda->setAlignment(Qt::AlignRight);
          rejilla->addWidget(celda, i, j);
        }
      }
      capa->addLayout(rejilla);
    };
  bloque(QStringLiteral("T pedida"), [&](int i, int j) {return pedida[i][j];});
  bloque(QStringLiteral("T = FK(q_IK)"), [&](int i, int j) {return fk[i][j];});
  bloque(QStringLiteral("Diferencia (T pedida − T FK)"), [&](int i, int j) {return pedida[i][j] - fk[i][j];});
  auto * cerrar = new QPushButton(QStringLiteral("Cerrar"));
  connect(cerrar, &QPushButton::clicked, dialogo, &QDialog::accept);
  capa->addWidget(cerrar, 0, Qt::AlignRight);
  dialogo->show();
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
