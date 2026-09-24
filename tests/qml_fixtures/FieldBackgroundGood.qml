import QtQuick
import QtQuick.Controls

// Gegenprobe zu `FieldBackground.qml` (Befund N1, Nachprüfung 00ce53b): dieselbe Bauform
// — ein gefülltes Eingabefeld mit eigener, von der Seite verschiedener Fläche — aber mit
// gut lesbarer Schrift. Eine falsch-rot messende Fassung (die die Feldfläche beim
// Ausblenden mit wegnimmt, `item.setOpacity(0)` statt `color: transparent`) meldet hier
// fälschlich einen Kontrastfehler gegen die Seitenfarbe (#e3dfd6), obwohl die Schrift auf
// ihrer eigenen Fläche (#fdfcfa) einwandfrei ist.
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
        text: "Gut lesbare Eingabe"
        color: "#1a1f26"
        font.family: "Inter"
        font.pixelSize: 16
        background: Rectangle {
            color: "#fdfcfa"
            border.color: "#4a545f"
            border.width: 1
        }
    }
}
