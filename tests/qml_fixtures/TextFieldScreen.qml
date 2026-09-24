import QtQuick
import QtQuick.Controls

// Angriffsvorlage (B7, Befund B1): ein `TextField` — weder `className() == "QQuickText"`
// noch `inherits("QQuickText")` trifft zu (TextInput ist ein eigener Zweig), deshalb
// braucht check_layout()/check_contrast() dafür eine eigene Verzweigung
// (`inherits("QQuickTextInput")`). Blasser Text im Feld, damit ein stehen gebliebener
// Befund sichtbar bleibt.
//
// (Befund N1, Nachprüfung 00ce53b): Die Feldfläche (`background`) bekommt absichtlich
// eine **andere** Farbe als die Seite — vorher deckte sich beides zufällig (`#e3dfd6`
// hier wie dort), und `item.setOpacity(0)` blendete beim Ausblenden die Feldfläche mit
// aus; das „ohne"-Bild zeigte dadurch zufällig dieselbe Farbe wie die echte Feldfläche
// und verdeckte den Fehler. Mit unterschiedlichen Farben verrät ein Rückfall auf
// `opacity` sich sofort — das „ohne"-Bild zeigte dann die Seitenfarbe (`#e3dfd6`) statt
// der Feldfläche (`#fdfcfa`), und die Messung träfe Schrift gegen die falsche Fläche.
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
            color: "#fdfcfa"
        }
    }
}
