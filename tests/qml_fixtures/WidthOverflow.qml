import QtQuick

// Angriffsvorlage (F4, Nachprüfung d00e7c9): Ein Text mit fester, zu schmaler Breite,
// ohne `elide` und ohne Umbruch — die alte Layoutprüfung maß nur die Höhe
// (`implicitHeight` gegen `height`), nie die Breite, und ein solcher Text überschrieb
// seinen Nachbarn unbemerkt.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    Row {
        x: 20
        y: 20
        spacing: 8

        Text {
            objectName: "zuBreit"
            width: 80
            text: "Ein viel zu langer Kapitelname"
            color: "#000000"
            font.family: "Inter"
            font.pixelSize: 16
        }

        Text {
            objectName: "nachbar"
            text: "5.681"
            color: "#000000"
            font.family: "Inter"
            font.pixelSize: 16
        }
    }
}
