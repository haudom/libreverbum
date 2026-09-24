import QtQuick

// Angriffsvorlage (Befund N7, Nachprüfung 00ce53b): `opacity` sitzt auf einem Vorfahren
// der Textstelle, nicht auf ihr selbst — die Hausregel „opacity nie auf Text"
// (CLAUDE.md, Gestaltung) galt bisher nur für die eigene Opacity und überging einen
// gedämpften Vorfahren unbemerkt.
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

    Item {
        opacity: 0.8
        x: 20
        y: 20
        width: 400
        height: 40

        Text {
            objectName: "gedaempft"
            text: "Vorfahr opacity 0.8"
            color: "#1a1f26"
            font.family: "Inter"
            font.pixelSize: 16
        }
    }
}
