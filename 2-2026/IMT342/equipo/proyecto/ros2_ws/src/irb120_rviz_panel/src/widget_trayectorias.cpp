#include "widget_trayectorias.hpp"

#include <QCheckBox>
#include <QFont>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMessageBox>
#include <QPushButton>
#include <QVBoxLayout>

#include "json_util.hpp"

namespace irb120_rviz_panel
{

namespace
{
constexpr int ROL_ARCHIVO = Qt::UserRole;
constexpr int ROL_BUCLE = Qt::UserRole + 1;

const char * ESTILO_GRANDE =
  "QPushButton{font-weight:bold; padding:8px 12px; color:white; background:%1;}"
  "QPushButton:disabled{background:#9ca3af; color:#eee;}";

QPushButton * botonGrande(const QString & texto, const QString & color)
{
  auto * b = new QPushButton(texto);
  b->setStyleSheet(QString::fromLatin1(ESTILO_GRANDE).arg(color));
  b->setMinimumHeight(34);
  return b;
}

void cabecera(QListWidget * lista, const QString & titulo)
{
  auto * item = new QListWidgetItem(titulo);
  QFont f = item->font();
  f.setBold(true);
  item->setFont(f);
  item->setFlags(Qt::NoItemFlags);
  item->setBackground(QColor(128, 128, 128, 40));
  lista->addItem(item);
}
}  // namespace

WidgetTrayectorias::WidgetTrayectorias(QWidget * padre)
: QWidget(padre)
{
  auto * capa = new QVBoxLayout(this);
  capa->setContentsMargins(4, 4, 4, 4);

  // ---------- biblioteca ----------
  auto * caja = new QGroupBox(QStringLiteral("Trayectorias"));
  auto * c = new QVBoxLayout(caja);
  lista_ = new QListWidget;
  lista_->setMinimumHeight(140);
  lista_->setMaximumHeight(190);
  c->addWidget(lista_);
  bucle_ = new QCheckBox(QStringLiteral("Bucle (repetir hasta «Detener al final»)"));
  c->addWidget(bucle_);
  auto * fila1 = new QHBoxLayout();
  vistaPrevia_ = botonGrande(QStringLiteral("Vista previa"), QStringLiteral("#2563eb"));
  vistaPrevia_->setToolTip(QStringLiteral("Anima el robot naranja; el robot real no se mueve"));
  ejecutar_ = botonGrande(QStringLiteral("Ejecutar"), QStringLiteral("#c2410c"));
  fila1->addWidget(vistaPrevia_);
  fila1->addWidget(ejecutar_);
  c->addLayout(fila1);
  auto * fila2 = new QHBoxLayout();
  pausar_ = new QPushButton(QStringLiteral("Pausar"));
  reanudar_ = new QPushButton(QStringLiteral("Reanudar"));
  detenerFinal_ = new QPushButton(QStringLiteral("Detener al final"));
  cancelar_ = new QPushButton(QStringLiteral("Cancelar"));
  for (auto * b : {pausar_, reanudar_, detenerFinal_, cancelar_}) {
    fila2->addWidget(b);
  }
  c->addLayout(fila2);
  progreso_ = new QLabel;
  progreso_->setWordWrap(true);
  progreso_->setStyleSheet(QStringLiteral("color:#c2410c;"));
  error_ = new QLabel;
  error_->setWordWrap(true);
  error_->setStyleSheet(QStringLiteral("color:#b91c1c;"));
  c->addWidget(progreso_);
  c->addWidget(error_);
  capa->addWidget(caja);

  // ---------- grabación ----------
  auto * grabar = new QGroupBox(QStringLiteral("Grabar trayectoria"));
  auto * g = new QVBoxLayout(grabar);
  capturar_ = botonGrande(QStringLiteral("Capturar punto (postura actual del robot)"), QStringLiteral("#15803d"));
  g->addWidget(capturar_);
  puntos_ = new QListWidget;
  puntos_->setMinimumHeight(80);
  puntos_->setMaximumHeight(130);
  puntos_->setSelectionMode(QAbstractItemView::NoSelection);
  g->addWidget(puntos_);
  auto * fila3 = new QHBoxLayout();
  borrarUltimo_ = new QPushButton(QStringLiteral("Borrar último"));
  vaciar_ = new QPushButton(QStringLiteral("Vaciar"));
  fila3->addWidget(borrarUltimo_);
  fila3->addWidget(vaciar_);
  g->addLayout(fila3);
  auto * fila4 = new QHBoxLayout();
  nombre_ = new QLineEdit;
  nombre_->setPlaceholderText(QStringLiteral("Nombre de la trayectoria"));
  nombre_->setMaxLength(60);
  bucleGrabado_ = new QCheckBox(QStringLiteral("Bucle"));
  guardar_ = new QPushButton(QStringLiteral("Guardar"));
  fila4->addWidget(nombre_, 1);
  fila4->addWidget(bucleGrabado_);
  fila4->addWidget(guardar_);
  g->addLayout(fila4);
  auto * nota = new QLabel(QStringLiteral(
      "Mover el robot (o el control 3D → «Añadir postura actual del robot») y capturar al menos 2 puntos. "
      "Se guarda cerrada (A→B→…→A), en articular."));
  nota->setWordWrap(true);
  g->addWidget(nota);
  capa->addWidget(grabar);

  auto * parar = new QLabel(QStringLiteral(
      "<b>Para parar YA:</b> Stop, soltar el habilitador o paro de emergencia. «Cancelar» y «Pausar» actúan "
      "al terminar el tramo en curso."));
  parar->setWordWrap(true);
  parar->setStyleSheet(QStringLiteral(
      "border-left:4px solid #b91c1c; padding:4px 6px; background:rgba(185,28,28,0.08);"));
  capa->addWidget(parar);
  capa->addStretch(1);

  connect(lista_, &QListWidget::currentItemChanged, this, [this](QListWidgetItem * item, QListWidgetItem *) {
      if (item != nullptr) {
        bucle_->setChecked(item->data(ROL_BUCLE).toBool());
      }
      habilitar();
    });
  connect(vistaPrevia_, &QPushButton::clicked, this, [this]() {
      emit ordenPedida(QStringLiteral("trayectoria_vista_previa"), {{QStringLiteral("archivo"), archivoElegido()}});
    });
  connect(ejecutar_, &QPushButton::clicked, this, &WidgetTrayectorias::confirmarEjecucion);
  connect(pausar_, &QPushButton::clicked, this, [this]() {emit ordenPedida(QStringLiteral("pausar"), {});});
  connect(reanudar_, &QPushButton::clicked, this, [this]() {emit ordenPedida(QStringLiteral("reanudar"), {});});
  connect(detenerFinal_, &QPushButton::clicked, this, [this]() {
      emit ordenPedida(QStringLiteral("detener_al_final"), {});
    });
  connect(cancelar_, &QPushButton::clicked, this, [this]() {emit ordenPedida(QStringLiteral("cancelar"), {});});
  connect(capturar_, &QPushButton::clicked, this, [this]() {emit ordenPedida(QStringLiteral("grabar_punto"), {});});
  connect(borrarUltimo_, &QPushButton::clicked, this, [this]() {
      emit ordenPedida(QStringLiteral("grabar_borrar_ultimo"), {});
    });
  connect(vaciar_, &QPushButton::clicked, this, [this]() {
      if (QMessageBox::question(this, QStringLiteral("Vaciar grabación"),
          QStringLiteral("¿Descartar los %1 puntos grabados?").arg(nPuntos_),
          QMessageBox::Yes | QMessageBox::No, QMessageBox::No) == QMessageBox::Yes)
      {
        emit ordenPedida(QStringLiteral("grabar_vaciar"), {});
      }
    });
  connect(guardar_, &QPushButton::clicked, this, [this]() {
      guardando_ = true;
      emit ordenPedida(QStringLiteral("grabar_guardar"),
      {{QStringLiteral("nombre"), nombre_->text().trimmed()}, {QStringLiteral("bucle"), bucleGrabado_->isChecked()}});
    });
  connect(nombre_, &QLineEdit::textChanged, this, [this]() {habilitar();});
  habilitar();
}

QString WidgetTrayectorias::archivoElegido() const
{
  auto * item = lista_->currentItem();
  return item == nullptr ? QString() : item->data(ROL_ARCHIVO).toString();
}

void WidgetTrayectorias::mostrarError(const QString & texto)
{
  error_->setText(texto);
  if (!texto.isEmpty()) {
    guardando_ = false;   // la orden falló: no hay archivo nuevo que seleccionar
  }
}

void WidgetTrayectorias::sinConexion()
{
  conectado_ = false;
  progreso_->clear();
  habilitar();
}

void WidgetTrayectorias::reconstruirLista(const QJsonArray & filas)
{
  QString firma;
  for (const auto & f : filas) {
    const QJsonObject o = f.toObject();
    firma += o.value("archivo").toString() + '|' + o.value("nombre").toString() + '|' +
      QString::number(o.value("puntos").toInt()) + ';';
  }
  if (firma == firmaLista_) {
    return;
  }
  firmaLista_ = firma;
  const QString previo = archivoElegido();
  QSet<QString> ahora;
  QString nuevo;
  for (const auto & f : filas) {
    const QString a = f.toObject().value("archivo").toString();
    ahora.insert(a);
    if (guardando_ && !archivosVistos_.isEmpty() && !archivosVistos_.contains(a)) {
      nuevo = a;
    }
  }
  archivosVistos_ = ahora;
  const QString destino = nuevo.isEmpty() ? previo : nuevo;
  if (!nuevo.isEmpty()) {
    guardando_ = false;
  }
  lista_->blockSignals(true);
  lista_->clear();
  QListWidgetItem * elegir = nullptr;
  for (int grupo = 0; grupo < 2; ++grupo) {
    const bool vistosas = grupo == 0;
    bool hay = false;
    for (const auto & f : filas) {
      const QJsonObject o = f.toObject();
      if (o.value("vistosa").toBool() != vistosas) {
        continue;
      }
      if (!hay) {
        cabecera(lista_, vistosas ? QStringLiteral("Movimientos vistosos") : QStringLiteral("Guardadas"));
        hay = true;
      }
      const QString num = o.value("numero").isDouble() ?
        QStringLiteral("%1").arg(o.value("numero").toInt(), 2, 10, QLatin1Char('0')) : QStringLiteral("——");
      auto * item = new QListWidgetItem(QStringLiteral("  %1 · %2  (%3 pts)")
        .arg(num, o.value("nombre").toString()).arg(o.value("puntos").toInt()));
      item->setData(ROL_ARCHIVO, o.value("archivo").toString());
      item->setData(ROL_BUCLE, o.value("bucle_por_defecto").toBool());
      lista_->addItem(item);
      if (o.value("archivo").toString() == destino) {
        elegir = item;
      }
    }
  }
  lista_->blockSignals(false);
  if (elegir != nullptr) {
    lista_->setCurrentItem(elegir);
    if (!nuevo.isEmpty()) {
      bucle_->setChecked(elegir->data(ROL_BUCLE).toBool());
    }
  }
}

void WidgetTrayectorias::reconstruirGrabacion(const QJsonArray & puntos)
{
  QString firma;
  for (const auto & p : puntos) {
    firma += p.toObject().value("nombre").toString() + ';';
  }
  nPuntos_ = puntos.size();
  if (firma == firmaPuntos_) {
    return;
  }
  firmaPuntos_ = firma;
  puntos_->clear();
  for (const auto & p : puntos) {
    const QJsonObject o = p.toObject();
    QStringList v;
    for (double x : seis(o.value("q"))) {
      v << QString::number(x, 'f', 1);
    }
    puntos_->addItem(QStringLiteral("%1   q = [%2]°").arg(o.value("nombre").toString(), v.join(QStringLiteral(", "))));
  }
  puntos_->scrollToBottom();
  if (guardando_ && puntos.isEmpty() && !firmaLista_.isEmpty()) {
    nombre_->clear();   // se guardó: la grabación quedó vacía
  }
}

void WidgetTrayectorias::actualizar(const QJsonObject & e)
{
  conectado_ = true;
  ultimo_ = e;
  reconstruirLista(e.value("biblioteca").toArray());
  reconstruirGrabacion(e.value("grabacion").toObject().value("puntos").toArray());
  const QJsonObject t = e.value("trayectoria").toObject();
  const QString fase = t.value("fase").toString();
  const QJsonObject vista = t.value("vista_previa").toObject();
  QString texto;
  if (vista.value("activa").toBool()) {
    texto = QStringLiteral("Vista previa: %1 %").arg(qRound(vista.value("progreso").toDouble() * 100));
  } else if (fase == "ejecutando" || fase == "pausada") {
    const QString vueltas = t.value("vueltas").isDouble() ? QString::number(t.value("vueltas").toInt()) : QStringLiteral("∞");
    texto = QStringLiteral("«%1» · %2 · vuelta %3 / %4 · tramo %5/%6\n%7")
      .arg(t.value("nombre").toString(), fase, QString::number(t.value("vuelta").toInt()), vueltas,
        QString::number(t.value("tramo").toInt()), QString::number(t.value("total").toInt()),
        t.value("mensaje").toString());
    if (t.value("detener_al_final").toBool()) {
      texto += QStringLiteral("\nSe detendrá al terminar la vuelta.");
    }
  } else if (!fase.isEmpty() && fase != "lista") {
    texto = QStringLiteral("«%1» · %2: %3").arg(t.value("nombre").toString(), fase, t.value("mensaje").toString());
  }
  progreso_->setText(texto);
  habilitar();
}

void WidgetTrayectorias::habilitar()
{
  const bool ocupado = ultimo_.value("ocupado").toBool();
  const QJsonObject t = ultimo_.value("trayectoria").toObject();
  const QString fase = t.value("fase").toString();
  const bool vista = t.value("vista_previa").toObject().value("activa").toBool();
  const bool hayElegida = !archivoElegido().isEmpty();
  const bool listo = ultimo_.value("listo").toBool();
  vistaPrevia_->setEnabled(conectado_ && hayElegida && !ocupado && !vista);
  ejecutar_->setEnabled(conectado_ && hayElegida && listo && !ocupado && !vista);
  ejecutar_->setToolTip(!conectado_ ? QStringLiteral("Sin conexión con irb120_panel_rws") :
    !listo ? QStringLiteral("El robot no está listo (ver Faltas en la pestaña Mover)") : QString());
  pausar_->setEnabled(conectado_ && fase == "ejecutando");
  reanudar_->setEnabled(conectado_ && fase == "pausada");
  detenerFinal_->setEnabled(conectado_ && (fase == "ejecutando" || fase == "pausada"));
  cancelar_->setEnabled(conectado_ && (ocupado || vista));
  const bool libre = conectado_ && !ocupado && !vista;
  capturar_->setEnabled(libre && seis(ultimo_.value("medido")).size() == 6);
  borrarUltimo_->setEnabled(conectado_ && nPuntos_ > 0);
  vaciar_->setEnabled(conectado_ && nPuntos_ > 0);
  guardar_->setEnabled(conectado_ && nPuntos_ >= 2 && !nombre_->text().trimmed().isEmpty());
  guardar_->setToolTip(nPuntos_ < 2 ? QStringLiteral("Capturar al menos 2 puntos") :
    nombre_->text().trimmed().isEmpty() ? QStringLiteral("Escribir un nombre") : QString());
}

void WidgetTrayectorias::confirmarEjecucion()
{
  auto * item = lista_->currentItem();
  if (item == nullptr) {
    return;
  }
  const QString nombre = item->text().trimmed();
  const bool bucle = bucle_->isChecked();
  const QJsonValue vel = ultimo_.value("velocidad_pct");
  const QString velocidad = vel.isDouble() ?
    QStringLiteral("%1 %").arg(vel.toInt()) + (ultimo_.value("velocidad_mm_s").isDouble() ?
    QStringLiteral(" (≈ %1 mm/s)").arg(qRound(ultimo_.value("velocidad_mm_s").toDouble())) : QString()) :
    QStringLiteral("desconocida");
  QString html = QStringLiteral(
    "<p><b>%1</b></p><table cellspacing='4'>"
    "<tr><td>Robot:</td><td><b>%2</b></td></tr>"
    "<tr><td>Bucle:</td><td><b>%3</b></td></tr>"
    "<tr><td>Velocidad:</td><td><b>%4</b></td></tr></table>"
    "<p>Se planifica desde la postura actual y cada tramo se verifica antes de enviarse. "
    "El primer movimiento lleva el robot al primer punto.</p>"
    "<p><b>Para parar YA:</b> Stop, soltar el habilitador o paro de emergencia. «Cancelar» solo evita "
    "los tramos siguientes.</p>")
    .arg(nombre.toHtmlEscaped(),
      ultimo_.value("simulado").toBool() ? QStringLiteral("simulado") : QStringLiteral("REAL"),
      bucle ? QStringLiteral("sí (hasta «Detener al final»)") : QStringLiteral("no (una vuelta)"), velocidad);
  QMessageBox caja(QMessageBox::Question, QStringLiteral("¿Ejecutar esta trayectoria?"), html,
    QMessageBox::Cancel, this);
  caja.setTextFormat(Qt::RichText);
  QPushButton * si = caja.addButton(QStringLiteral("Ejecutar"), QMessageBox::AcceptRole);
  caja.setDefaultButton(QMessageBox::Cancel);
  caja.exec();
  if (caja.clickedButton() == si) {
    emit ordenPedida(QStringLiteral("trayectoria_ejecutar"),
    {{QStringLiteral("archivo"), archivoElegido()}, {QStringLiteral("bucle"), bucle}});
  }
}

}  // namespace irb120_rviz_panel
