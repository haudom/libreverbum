import QtQuick

// Angriffsvorlage (B7, Befund B3, Durchsicht d993e3e): ein dunkler Balken im selben
// Textkasten wie ein blasser Text. Der alte Kontrastcheck maß den "extremsten Pixel im
// ganzen Kasten" als Vordergrund — der Balken hätte den blassen Text dabei überdeckt und
// einen guten Kontrast vorgetäuscht, während der eigentliche Text kaum lesbar ist.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Item {
        id: box
        x: 20
        y: 20
        width: 220
        height: 30

        Text {
            id: text
            objectName: "blasserTextMitLinie"
            width: 220
            height: 30
            text: "Blasser Text mit Linie"
            color: "#cfcabf"
            font.family: "Inter"
            font.pixelSize: 16
        }

        // Liegt bewusst über der Mitte der Textzeile (nicht darunter oder darüber) —
        // nur so überschneidet sich der Balken mit dem eigenen Rechteck des `Text`, das
        // gemessen wird, statt nur mit dem größeren `box`-Rechteck darum herum.
        Rectangle {
            x: 0
            y: text.height / 2 - 1
            width: 220
            height: 3
            color: "#1a1f26"
        }
    }
}
