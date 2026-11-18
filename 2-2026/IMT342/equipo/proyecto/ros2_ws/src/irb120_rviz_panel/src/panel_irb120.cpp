#include "panel_irb120.hpp"

#include <QGroupBox>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QMessageBox>
#include <QScrollArea>
#include <QScrollBar>
#include <QVBoxLayout>

#include <pluginlib/class_list_macros.hpp>
#include <rviz_common/display_context.hpp>
#include <rviz_common/ros_integration/ros_node_abstraction_iface.hpp>

#include <cmath>

#include "cliente_ros.hpp"
#include "json_util.hpp"
#include "widget_ejes.hpp"
#include "widget_estado.hpp"
#include "widget_pose.hpp"
#include "widget_velocidad.hpp"
#include "widget_verificacion.hpp"

namespace irb120_rviz_panel
{

namespace
{
QGroupBox * grupo(const QString & titulo, QWidget * cuerpo)
{
  auto * caja = new QGroupBox(titulo);
  auto * capa = new QVBoxLayout(caja);
  capa->setContentsMargins(6, 6, 6, 6);
  capa->addWidget(cuerpo);
  return caja;
}
}  // namespace

PanelIRB120::PanelIRB120(QWidget * padre)
: rviz_common::Panel(padre)
{
  estado_ = new WidgetEstado;
  ejes_ = new WidgetEjes;
  pose_ = new WidgetPose;
  verificacion_ = new WidgetVerificacion;
  velocidad_ = new WidgetVelocidad;

  contenido_ = new QWidget;
  auto * capa = new QVBoxLayout(contenido_);
  capa->setContentsMargins(4, 4, 4, 4);
  capa->addWidget(grupo(QStringLiteral("Estado del robot"), estado_));
  capa->addWidget(grupo(QStringLiteral("Ángulos J1–J6 (grados)"), ejes_));
  capa->addWidget(grupo(QStringLiteral("Posición cartesiana → ángulos (cinemática inversa)"), pose_));
  capa->addWidget(grupo(QStringLiteral("Verificación (en tiempo real)"), verificacion_));
  capa->addWidget(grupo(QStringLiteral("Velocidad"), velocidad_));
  capa->addWidget(construirAcciones());
  auto * parar = new QLabel(QStringLiteral(
      "<b>Para detener el robot:</b> soltar el habilitador, Stop o paro de emergencia. "
      "«Cancelar» solo evita las órdenes siguientes."));
  parar->setWordWrap(true);
  parar->setStyleSheet(QStringLiteral(
      "border-left:4px solid #b91c1c; padding:4px 6px; background:rgba(185,28,28,0.08);"));
  capa->addWidget(parar);
  registro_ = new QPlainTextEdit;
  registro_->setReadOnly(true);
  registro_->setMaximumBlockCount(300);
  registro_->setMinimumHeight(110);
  registro_->setFont(QFont(QStringLiteral("Monospace"), 8));
  capa->addWidget(grupo(QStringLiteral("Registro"), registro_));
  capa->addStretch(1);

  auto * desplazable = new QScrollArea;
  desplazable->setWidgetResizable(true);
  desplazable->setWidget(contenido_);
  // El dock se abre con el ancho del contenido: sin barra horizontal en la columna «Cambio».
  desplazable->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
  desplazable->setMinimumWidth(contenido_->sizeHint().width() + desplazable->verticalScrollBar()->sizeHint().width() + 4);
  auto * raiz = new QVBoxLayout(this);
  raiz->setContentsMargins(0, 0, 0, 0);
  raiz->addWidget(desplazable);

  connect(ejes_, &WidgetEjes::objetivoEditado, this, [this](const QVector<double> & q) {
      orden(QStringLiteral("objetivo"), {{QStringLiteral("q"), arreglo(q)}});
    });
  connect(pose_, &WidgetPose::herramientaElegida, this, [this](const QString & h) {
      orden(QStringLiteral("herramienta"), {{QStringLiteral("valor"), h}});
    });
  connect(pose_, &WidgetPose::calcular, this, [this](const QVector<double> & p) {
      orden(QStringLiteral("ik"), {{QStringLiteral("pose"), arreglo(p)}});
    });
  connect(pose_, &WidgetPose::usarRama, this, [this](const QVector<double> & q) {
      ejes_->ponerObjetivo(q);
      orden(QStringLiteral("objetivo"), {{QStringLiteral("q"), arreglo(q)}});
    });
  connect(velocidad_, &WidgetVelocidad::velocidadElegida, this, [this](int pct) {
      orden(QStringLiteral("velocidad"), {{QStringLiteral("valor"), pct}});
    });
  vigilancia_.setInterval(500);
  connect(&vigilancia_, &QTimer::timeout, this, &PanelIRB120::vigilar);
  habilitar();
}

PanelIRB120::~PanelIRB120() = default;

QWidget * PanelIRB120::construirAcciones()
{
  auto * caja = new QWidget;
  auto * capa = new QVBoxLayout(caja);
  capa->setContentsMargins(0, 0, 0, 0);
  auto * filaPos = new QHBoxLayout();
  posCero_ = new QPushButton(QStringLiteral("Posición 0 (calibración)"));
  posReposo_ = new QPushButton(QStringLiteral("Reposo (J5 30°)"));
  filaPos->addWidget(posCero_);
  filaPos->addWidget(posReposo_);
  capa->addLayout(filaPos);
  auto * fila1 = new QHBoxLayout();
  enviar_ = new QPushButton(QStringLiteral("Enviar al robot"));
  enviar_->setStyleSheet(QStringLiteral(
      "QPushButton{background:#c2410c; color:white; font-weight:bold; padding:6px 12px;}"
      "QPushButton:disabled{background:#9ca3af; color:#eee;}"));
  paso_ = new QComboBox;
  paso_->setToolTip(QStringLiteral("Paso máx. por orden"));
  for (int paso : {5, 10, 20, 40}) {
    paso_->addItem(QStringLiteral("Paso máx. por orden: %1°").arg(paso), paso);
  }
  fila1->addWidget(enviar_, 1);
  fila1->addWidget(paso_);
  capa->addLayout(fila1);
  auto * fila2 = new QHBoxLayout();
  sincronizar_ = new QPushButton(QStringLiteral("Copiar postura actual"));
  cancelar_ = new QPushButton(QStringLiteral("Cancelar tras la orden en curso"));
  fila2->addWidget(sincronizar_);
  fila2->addWidget(cancelar_);
  capa->addLayout(fila2);
  terminar_ = new QPushButton(QStringLiteral("Terminar ServidorPC en el robot"));
  capa->addWidget(terminar_);
  progreso_ = new QLabel;
  progreso_->setStyleSheet(QStringLiteral("color:#c2410c;"));
  progreso_->setWordWrap(true);
  error_ = new QLabel;
  error_->setStyleSheet(QStringLiteral("color:#b91c1c;"));
  error_->setWordWrap(true);
  capa->addWidget(progreso_);
  capa->addWidget(error_);

  connect(enviar_, &QPushButton::clicked, this, &PanelIRB120::confirmarEnvio);
  connect(posCero_, &QPushButton::clicked, this, [this]() {
      orden(QStringLiteral("posicion"), {{QStringLiteral("valor"), QStringLiteral("cero")}});
    });
  connect(posReposo_, &QPushButton::clicked, this, [this]() {
      orden(QStringLiteral("posicion"), {{QStringLiteral("valor"), QStringLiteral("reposo")}});
    });
  connect(sincronizar_, &QPushButton::clicked, this, [this]() {orden(QStringLiteral("sincronizar"));});
  connect(cancelar_, &QPushButton::clicked, this, [this]() {orden(QStringLiteral("cancelar"));});
  connect(terminar_, &QPushButton::clicked, this, &PanelIRB120::confirmarTerminar);
  connect(paso_, QOverload<int>::of(&QComboBox::activated), this, [this](int i) {
      orden(QStringLiteral("paso"), {{QStringLiteral("valor"), paso_->itemData(i).toDouble()}});
    });
  return grupo(QStringLiteral("Acciones"), caja);
}

void PanelIRB120::onInitialize()
{
  auto nodo = getDisplayContext()->getRosNodeAbstraction().lock()->get_raw_node();
  ros_ = new ClienteRos(nodo, this);
  connect(ros_, &ClienteRos::estadoRecibido, this, &PanelIRB120::recibir);
  vigilancia_.start();
}

void PanelIRB120::orden(const QString & accion, const QJsonObject & cuerpo)
{
  if (ros_ != nullptr && conectado_) {
    ros_->enviar(accion, cuerpo);
  }
}

void PanelIRB120::recibir(const QJsonObject & e)
{
  ultimoEstado_.start();
  conectado_ = true;
  ultimo_ = e;
  estado_->actualizar(e);
  ejes_->actualizar(e);
  pose_->actualizar(e);
  verificacion_->actualizar(e);
  velocidad_->actualizar(e);
  const bool ocupado = e.value("ocupado").toBool();
  if (estabaOcupado_ && !ocupado) {
    verificacion_->resaltarLlegada();
  }
  estabaOcupado_ = ocupado;
  const int pasoMax = static_cast<int>(std::lround(e.value("paso_max").toDouble(40)));
  for (int i = paso_->count() - 1; i >= 0; --i) {
    if (paso_->itemData(i).toInt() > pasoMax && paso_->count() > 1) {
      paso_->removeItem(i);
    }
  }
  const int paso = static_cast<int>(std::lround(e.value("paso").toDouble(5)));
  const int indice = paso_->findData(paso);
  if (indice >= 0 && !paso_->view()->isVisible()) {
    paso_->setCurrentIndex(indice);
  }
  progreso_->setText(e.value("progreso").toString());
  const QJsonObject respuesta = e.value("respuesta").toObject();
  if (!respuesta.isEmpty() && respuesta.value("id").toInt(-1) != respuestaVista_) {
    respuestaVista_ = respuesta.value("id").toInt(-1);
    error_->setText(respuesta.value("ok").toBool() ? QString() : respuesta.value("error").toString());
  }
  QStringList lineas;
  for (const auto & linea : e.value("registro").toArray()) {
    lineas << linea.toString();
  }
  const QString texto = lineas.join('\n');
  if (registro_->toPlainText() != texto) {
    registro_->setPlainText(texto);
    registro_->verticalScrollBar()->setValue(registro_->verticalScrollBar()->maximum());
  }
  habilitar();
}

void PanelIRB120::vigilar()
{
  if (conectado_ && ultimoEstado_.isValid() && ultimoEstado_.elapsed() > 2000) {
    conectado_ = false;
    estado_->sinConexion();
    verificacion_->sinConexion();
    progreso_->clear();
    habilitar();
  }
}

void PanelIRB120::habilitar()
{
  const bool ocupado = ultimo_.value("ocupado").toBool();
  const QVector<double> medido = ejes_->medido();
  const bool hayCambio = !medido.isEmpty() && cambioMaximo(ejes_->objetivo(), medido) >= 0.01;
  ejes_->setBloqueado(!conectado_ || ocupado);
  pose_->setBloqueado(!conectado_ || ocupado);
  velocidad_->setBloqueado(!conectado_);
  const bool permitido = verificacion_->envioPermitido();
  enviar_->setEnabled(conectado_ && ultimo_.value("listo").toBool() && !ocupado && hayCambio && permitido);
  enviar_->setToolTip(!conectado_ ? QStringLiteral("Sin conexión con irb120_panel_rws") :
    ocupado ? QStringLiteral("Hay un envío en curso") :
    !ultimo_.value("listo").toBool() ? QStringLiteral("El robot no está listo (ver FALTA)") :
    !permitido ? QStringLiteral("Envío bloqueado: %1").arg(verificacion_->motivo()) :
    !hayCambio ? QStringLiteral("El objetivo coincide con la postura actual") : QString());
  sincronizar_->setEnabled(conectado_ && !ocupado && !medido.isEmpty());
  cancelar_->setEnabled(conectado_ && ocupado);
  terminar_->setEnabled(conectado_ && !ocupado);
  paso_->setEnabled(conectado_ && !ocupado);
  posCero_->setEnabled(conectado_ && !ocupado);
  posReposo_->setEnabled(conectado_ && !ocupado);
  const QJsonObject posiciones = ultimo_.value("posiciones").toObject();
  const auto angulos = [&posiciones](const QString & clave, const QString & defecto) {
      const QJsonArray a = posiciones.value(clave).toArray();
      if (a.size() != 6) {
        return defecto;
      }
      QStringList v;
      for (const auto & x : a) {
        v << QString::number(x.toDouble(), 'f', 1);
      }
      return QStringLiteral("J1..J6 = ") + v.join(QStringLiteral(", ")) + QStringLiteral("°");
    };
  posCero_->setToolTip(QStringLiteral("Objetivo en vista previa (no envía): ") +
    angulos(QStringLiteral("cero"), QStringLiteral("todos los ejes 0°")));
  posReposo_->setToolTip(QStringLiteral("Objetivo en vista previa (no envía): ") +
    angulos(QStringLiteral("reposo"), QStringLiteral("J5 30°, resto 0°")));
}

void PanelIRB120::confirmarEnvio()
{
  const QVector<double> medido = ejes_->medido();
  const QVector<double> objetivo = ejes_->objetivo();
  if (medido.size() != 6 || objetivo.size() != 6) {
    return;
  }
  const double paso = ultimo_.value("paso").toDouble(5);
  const double mayor = cambioMaximo(objetivo, medido);
  const int ordenes = std::max(1, static_cast<int>(std::ceil((mayor - 0.05) / paso)));
  QString tabla = QStringLiteral("<table cellspacing='4'><tr><th></th><th>Medido</th><th></th>"
      "<th>Objetivo</th><th>Cambio</th></tr>");
  for (int i = 0; i < 6; ++i) {
    const double cambio = objetivo[i] - medido[i];
    tabla += QString::asprintf("<tr><td><b>J%d</b></td><td align='right'>%.2f°</td><td>→</td>"
        "<td align='right'>%.2f°</td><td align='right'>%s</td></tr>", i + 1, medido[i], objetivo[i],
        std::abs(cambio) < 0.005 ? "" : QString::asprintf("%+.2f°", cambio).toUtf8().constData());
  }
  tabla += QStringLiteral("</table><p>Cambio mayor: %1°. Se enviará en %2 orden(es) de como máximo %3° "
      "por eje. Valores en grados.</p>").arg(mayor, 0, 'f', 2).arg(ordenes).arg(paso);
  tabla += verificacion_->resumenHtml();
  QMessageBox caja(QMessageBox::Question, QStringLiteral("¿Enviar este objetivo al robot?"), tabla,
    QMessageBox::Cancel, this);
  caja.setTextFormat(Qt::RichText);
  QPushButton * si = caja.addButton(QStringLiteral("Enviar"), QMessageBox::AcceptRole);
  caja.setDefaultButton(QMessageBox::Cancel);
  caja.exec();
  if (caja.clickedButton() == si) {
    orden(QStringLiteral("enviar"), {{QStringLiteral("q"), arreglo(objetivo)}});
  }
}

void PanelIRB120::confirmarTerminar()
{
  const auto respuesta = QMessageBox::question(this, QStringLiteral("Terminar ServidorPC"),
      QStringLiteral("¿Terminar ServidorPC en el robot? Después habrá que arrancarlo de nuevo "
      "en el FlexPendant."), QMessageBox::Yes | QMessageBox::No, QMessageBox::No);
  if (respuesta == QMessageBox::Yes) {
    orden(QStringLiteral("terminar"));
  }
}

}  // namespace irb120_rviz_panel

PLUGINLIB_EXPORT_CLASS(irb120_rviz_panel::PanelIRB120, rviz_common::Panel)
