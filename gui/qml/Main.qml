import QtQuick
import QtQuick.Window

// Fenster und Bildschirmstapel der Oberfläche (bauplan-phase2.md AP 15).
//
// Der Stapel ist hier ein einzelner Platz: `screen` nennt den Namen, `Loader` lädt die
// gleichnamige Datei aus diesem Verzeichnis. Das ist die Erweiterungsstelle für AP 16a und
// folgende, die die sieben Bildschirme aus konzept.md, „Die sieben Bildschirme der
// Oberfläche" nacheinander eintragen — nicht mehr, weil AP 15 nur das Gerüst verlangt und
// Regel 14 keine Abstraktion vor dem zweiten Anwendungsfall will. Bis dahin steht hier nur
// `Placeholder.qml`.
//
// `Theme` kommt ohne `import`-Zeile: Als `pragma Singleton`-Datei im selben Verzeichnis
// (`gui/qml/`) ist sie über den impliziten Verzeichnisimport verfügbar, den jede QML-Datei
// für ihr eigenes Verzeichnis bekommt — keine Kopie, keine zweite Quelle (technik.md §14,
// „Der Mockup rendert gegen den Bestand" gilt sinngemäß: Hier *ist* dieses Verzeichnis der
// Bestand).
Window {
    id: window

    width: 1280
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: true
    title: "LibreVerbum"
    color: Theme.ground

    // Name des sichtbaren Bildschirms — eine Datei `<Name>.qml` in diesem Verzeichnis.
    property string screen: "Placeholder"

    Loader {
        id: stack
        objectName: "screenStack"
        anchors.fill: parent
        source: window.screen + ".qml"
    }
}
