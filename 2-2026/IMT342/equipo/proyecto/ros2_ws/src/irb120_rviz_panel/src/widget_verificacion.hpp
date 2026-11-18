// Bloque «Verificación»: IK → FK, robot real → pose deseada y modelo frente al controlador ABB.
// Decide si se puede enviar (lo calcula el nodo; aquí solo se muestra y se consulta).
#pragma once

#include <QJsonObject>
#include <QLabel>
#include <QTimer>
#include <QVector>
#include <QWidget>

class QGridLayout;
class QPushButton;

namespace irb120_rviz_panel
{

class WidgetVerificacion : public QWidget
{
  Q_OBJECT

public:
  explicit WidgetVerificacion(QWidget * padre = nullptr);
  void actualizar(const QJsonObject & estado);
  void sinConexion();
  void resaltarLlegada();

  bool envioPermitido() const {return permitido_;}
  QString motivo() const {return motivo_;}
  // Resumen en HTML para el cuadro de confirmación del envío.
  QString resumenHtml() const;

private:
  struct Fila
  {
    QLabel * indicador;
    QLabel * valores;
  };
  Fila crearFila(QGridLayout * rejilla, int fila, const QString & titulo);
  void mostrarMatrices();
  void actualizarIdaVuelta(const QJsonObject & v);
  static void pintarFila(const Fila & fila, const QString & texto, int estado);

  Fila ikFk_;
  Fila robot_;
  Fila controlador_;
  QLabel * desglose_;                 // dx dy dz y % del recorrido del TCP (fila 2)
  QVector<QVector<QLabel *>> ejes_;   // J1..J6 × (objetivo, medido, error °, error %)
  QVector<QVector<QLabel *>> idaVuelta_;   // J1..J6 × (q IK, q recuperado, error °)
  QLabel * idaVueltaOk_;
  QPushButton * matrices_;
  QLabel * limites_;
  QLabel * alcanzable_;
  QLabel * veredicto_;
  QLabel * tolerancias_;
  QTimer resalte_;
  QJsonObject ultima_;
  bool permitido_ = false;
  QString motivo_;
};

}  // namespace irb120_rviz_panel
