import QtQuick

// Angriffsvorlage (B7): ein zu schmaler Text mit elide — layout_check() muss `truncated`
// erkennen, unabhängig davon, dass ELIDE_ERLAUBT für diesen Namen leer bleibt.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    Text {
        objectName: "gekuerzt"
        x: 20
        y: 20
        width: 120
        elide: Text.ElideRight
        text: "Dieser Text ist länger als die erlaubte Breite und wird deshalb gekürzt"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }
}
