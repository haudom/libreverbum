import QtQuick
import QtQuick.Controls

// Angriffsvorlage (Befund N1, Nachprüfung 00ce53b): ein gefülltes Eingabefeld mit
// eigener, von der Seite verschiedener Fläche (`background`) — die Feldschrift ist
// tatsächlich blass auf ihrer eigenen Fläche (1,16:1). Die alte, opacity-basierte
// Ausblendung hätte hier fälschlich „gegen die Seite gemessen" (#e3dfd6 statt der
// echten Feldfläche #ffffff) und einen anderen, falschen Kontrastwert geliefert.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Text {
        objectName: "kontrolle"
        x: 20
        y: 200
        text: "Kontrolle gut lesbar"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    TextField {
        objectName: "feld"
        x: 20
        y: 20
        width: 300
        text: "Eingabe hell auf hell"
        color: "#eeeeee"
        font.family: "Inter"
        font.pixelSize: 16
        background: Rectangle {
            color: "#ffffff"
        }
    }
}
