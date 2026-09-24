import QtQuick

// Angriffsvorlage (Befund N4, Nachprüfung 00ce53b): ein unteilbares, zusammengesetztes
// Wort mit `wrapMode: Text.WordWrap` in einem schmalen Kasten — Qt bricht bei `WordWrap`
// nur an Wortgrenzen, ein einzelnes zu breites Wort läuft deshalb unverändert über den
// Kasten hinaus und in den Nachbarn hinein. Die alte Prüfung griff nur bei
// `wrapMode == Text.NoWrap` und übersah diesen, im Deutschen alltäglichen Fall.
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

    Rectangle {
        x: 20
        y: 20
        width: 150
        height: 60
        color: "#fdfcfa"

        Text {
            objectName: "umbruch"
            width: 150
            wrapMode: Text.WordWrap
            text: "Donaudampfschifffahrtsgesellschaftskapitaen"
            color: "#1a1f26"
            font.family: "Inter"
            font.pixelSize: 16
        }
    }

    Text {
        objectName: "nachbar"
        x: 180
        y: 20
        text: "Nachbar"
        color: "#1a1f26"
        font.family: "Inter"
        font.pixelSize: 16
    }
}
