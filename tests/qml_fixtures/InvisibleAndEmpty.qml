import QtQuick

// Angriffsvorlage (F6, Nachprüfung d00e7c9): zwei Fälle, die die alte
// Mehrheitsfarben-Heuristik verwechselte — ein leerer Text (nichts zu messen, kein
// Befund) und ein Text in exakt der Farbe seines Grundes (ein echter Befund UNSICHTBAR,
// weil kein zweites Element den Kasten überschneidet).
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Text {
        objectName: "kontrolle"
        x: 20
        y: 100
        text: "Kontrolle gut lesbar"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Text {
        objectName: "leer"
        x: 20
        y: 20
        width: 400
        text: ""
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Text {
        objectName: "farbgleich"
        x: 20
        y: 60
        text: "Verschwindet im Grund"
        color: "#e3dfd6"
        font.family: "Inter"
        font.pixelSize: 16
    }
}
