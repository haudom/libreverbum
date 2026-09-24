import QtQuick

// Gegenprobe zu `Overlap.qml` (Befund N3, Nachprüfung 00ce53b): Ein Rechteck
// überschneidet den Textkasten geometrisch genauso wie ein Deckel — liegt aber mit
// niedrigerem `z` **hinter** dem Text und verdeckt ihn deshalb nicht, sondern hebt ihn
// nur hervor (die laufende Zeile einer Liste, `Theme.qml`s Token `marked`). Eine
// Verdeckungsprüfung, die nur geometrisch überschneidet und `z` ignoriert, meldete das
// fälschlich als Befund.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Text {
        objectName: "kontrolle"
        x: 20
        y: 560
        text: "Kontrolle gut lesbar"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Text {
        objectName: "oben"
        x: 20
        y: 20
        z: 3
        text: "Text liegt oben"
        color: "#1a1f26"
        font.family: "Inter"
        font.pixelSize: 20
    }

    Rectangle {
        objectName: "unten"
        x: 10
        y: 10
        width: 400
        height: 50
        color: "#fdfcfa"
        z: 1
    }
}
