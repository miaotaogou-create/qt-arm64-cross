#include <QApplication>
#include <QLabel>

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    QLabel label(QStringLiteral("Hello CMake ARM64"));
    label.setAlignment(Qt::AlignCenter);
    label.resize(320, 120);
    label.show();
    return app.exec();
}
