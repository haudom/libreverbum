import QtQuick
import QtQuick.Controls

// Angriffsvorlage (B7, Befund B1, Durchsicht d993e3e): drei Arten von Textstellen, die
// `className() == "QQuickText"` (der alte Vergleich) übersah, weil ihr Metaobjektname
// nicht wörtlich "QQuickText" heißt, obwohl sie alle davon erben — jede mit blassem Text,
// damit ein stehen gebliebener Befund sichtbar bleibt, statt nur "gesehen, aber nicht
// gemessen" zu sein:
//
// - Label (Qt Quick Controls: erbt von Text, className() ist trotzdem "QQuickLabel")
// - ein Repeater-Delegat mit `required property` (QML erzeugt dafür einen eigenen
//   Untertyp, className() ist "wie Text plus ein synthetischer Name")
// - eine eigene Komponente mit Text-Wurzel (component PaleText: Text { ... })
Item {
    id: root

    component PaleText: Text {
        color: "#cfcabf"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Column {
        x: 20
        y: 20
        spacing: 8

        Label {
            objectName: "label"
            text: "Label-Text"
            color: "#cfcabf"
            font.family: "Inter"
            font.pixelSize: 16
        }

        PaleText {
            objectName: "customComponentText"
            text: "Eigene Komponente"
        }

        Repeater {
            model: ["required-Delegat"]

            delegate: Text {
                id: delegateRoot
                required property string modelData
                objectName: "requiredDelegate"
                text: modelData
                color: "#cfcabf"
                font.family: "Inter"
                font.pixelSize: 16
            }
        }
    }
}
