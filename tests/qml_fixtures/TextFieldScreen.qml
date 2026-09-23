import QtQuick
import QtQuick.Controls

// Angriffsvorlage (B7, Befund B1): ein `TextField` — weder `className() == "QQuickText"`
// noch `inherits("QQuickText")` trifft zu (TextInput ist ein eigener Zweig), deshalb
// braucht check_layout()/check_contrast() dafür eine eigene Verzweigung
// (`inherits("QQuickTextInput")`). Blasser Text im Feld, damit ein stehen gebliebener
// Befund sichtbar bleibt.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    TextField {
        objectName: "eingabefeld"
        x: 20
        y: 20
        width: 200
        text: "Blasser Eingabetext"
        color: "#cfcabf"
        font.family: "Inter"
        font.pixelSize: 16
        background: Rectangle {
            color: "#e3dfd6"
        }
    }
}
