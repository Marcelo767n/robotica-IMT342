#include <QApplication>
#include <QTimer>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <iostream>
#include "rviz_common/visualization_frame.hpp"
#include "rviz_common/visualization_manager.hpp"
#include "rviz_common/display_group.hpp"
#include "rviz_common/properties/status_property.hpp"
#include "rviz_common/ros_integration/ros_client_abstraction.hpp"
using rviz_common::properties::Property;
using rviz_common::properties::StatusProperty;
void statuses(Property *p, QJsonArray &out, bool &ok) {
  if (auto *s=dynamic_cast<StatusProperty*>(p)) {
    out.append(QJsonObject{{"name",s->getName()},{"level",int(s->getLevel())},{"value",s->getValue().toString()}});
    if (s->getLevel()!=StatusProperty::Ok) ok=false;
  }
  for(int i=0;i<p->numChildren();i++) statuses(p->childAt(i),out,ok);
}
int main(int argc, char **argv) {
  if(argc<2)return 2;
  QString config=argv[1];
  rviz_common::ros_integration::RosClientAbstraction ros;
  auto node=ros.init(argc,argv,"irb120_rviz_probe",false);
  QApplication app(argc,argv);
  rviz_common::VisualizationFrame frame(node);frame.setApp(&app);frame.setSplashPath("");frame.initialize(node,config);
  frame.show();
  bool passed=false;
  QTimer::singleShot(6000,[&] {
    auto *group=frame.getManager()->getRootDisplayGroup(); QJsonArray displays;passed=true;
    for(int i=0;i<group->numDisplays();i++) {
      auto *d=group->getDisplayAt(i);QJsonArray state;bool ok=true;statuses(d,state,ok);
      if(d->getClassId()!="rviz_default_plugins/Grid" && state.size()<2)ok=false;
      passed=passed&&ok;
      displays.append(QJsonObject{{"name",d->getName()},{"class",d->getClassId()},{"ok",ok},{"statuses",state}});
    }
    std::cout<<"RVIZ_PROBE "<<QJsonDocument(displays).toJson(QJsonDocument::Compact).toStdString()<<std::endl;
    const auto screenshot=qEnvironmentVariable("IRB120_RVIZ_SCREENSHOT");
    if(!screenshot.isEmpty())frame.getRenderWindow()->captureScreenShot(screenshot.toStdString());
    app.quit();
  });
  app.exec();ros.shutdown();return passed?0:1;
}
