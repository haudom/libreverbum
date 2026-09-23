import QtQuick

// Angriffsvorlage (F5, Nachprüfung d00e7c9): zwei Komponenten mit eigener
// `property string text` — eine spiegelt ihren Wert in einem `Text`-Nachfahren (wie
// `MessageBox` im Mockup oder ein Controls-`Button`, ausgenommen), die andere zeigt einen
// anderen Wert als ihr Nachfahre (ein echter, benannter Befund).
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    Rectangle {
        objectName: "gespiegelt"
        property string text: "Meldung"
        x: 20
        y: 20
        width: 200
        height: 30
        color: "transparent"

        Text {
            anchors.fill: parent
            text: parent.text
            color: "#000000"
            font.family: "Inter"
            font.pixelSize: 16
        }
    }

    Rectangle {
        objectName: "auseinandergelaufen"
        property string text: "Erwarteter Text"
        x: 20
        y: 60
        width: 200
        height: 30
        color: "transparent"

        Text {
            text: "Anderer Text"
            color: "#000000"
            font.family: "Inter"
            font.pixelSize: 16
        }
    }
}
