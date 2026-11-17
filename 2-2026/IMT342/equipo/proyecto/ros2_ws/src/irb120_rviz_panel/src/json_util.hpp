// Lectura tolerante del JSON de /irb120/panel/estado: cualquier clave puede faltar o ser null.
#pragma once

#include <QJsonArray>
#include <QJsonObject>
#include <QJsonValue>
#include <QString>
#include <QVector>

#include <cmath>

namespace irb120_rviz_panel
{

// Seis números finitos, o vector vacío si el valor no lo es.
inline QVector<double> seis(const QJsonValue & valor)
{
  QVector<double> salida;
  if (!valor.isArray() || valor.toArray().size() != 6) {
    return salida;
  }
  for (const auto & elemento : valor.toArray()) {
    if (!elemento.isDouble() || !std::isfinite(elemento.toDouble())) {
      return {};
    }
    salida.append(elemento.toDouble());
  }
  return salida;
}

inline QString texto(const QJsonValue & valor, const QString & siFalta = QStringLiteral("—"))
{
  if (valor.isString()) {
    return valor.toString();
  }
  if (valor.isDouble()) {
    return QString::number(valor.toDouble());
  }
  if (valor.isBool()) {
    return valor.toBool() ? QStringLiteral("sí") : QStringLiteral("no");
  }
  return siFalta;
}

inline QJsonArray arreglo(const QVector<double> & valores)
{
  QJsonArray salida;
  for (double v : valores) {
    salida.append(v);
  }
  return salida;
}

inline double cambioMaximo(const QVector<double> & a, const QVector<double> & b)
{
  double peor = 0.0;
  for (int i = 0; i < a.size() && i < b.size(); ++i) {
    peor = std::max(peor, std::abs(a[i] - b[i]));
  }
  return peor;
}

}  // namespace irb120_rviz_panel
