import QtQuick
import Mock

// Das Zustandszeichen: gefüllt mit Häkchen = erledigt, Ring mit Kern = dran, leerer Ring
// = offen.
//
// Zustand als **Form**, nicht nur als Farbe (aus Runde 1 übernommen, Kritik 2.4: „überlebt
// jede Gestaltungswahl"). Es steht in einem eigenen Bauteil, weil zwei Bildschirme
// dieselbe Auskunft geben — die Etappen des Kapitellaufs und die drei Schritte der
// Einrichtung. Zweimal gezeichnet wären es über kurz oder lang zwei verschiedene Sprachen.
//
// Der leere Ring ist in `inkFaint` gezeichnet und nicht in der Kantenfarbe: Ein
// Bedienelement braucht 3:1, und der leere Ring des alten Entwurfs hatte 1,63:1 (B3,
// letzte Zeile der Messtabelle).
Item {
    id: mark

    property int phase: 0      // 0 offen, 1 dran, 2 erledigt

    implicitWidth: Theme.space.l
    implicitHeight: Theme.space.l

    Rectangle {                // erledigt: gefüllte Scheibe
        anchors.centerIn: parent
        width: Theme.space.m
        height: width
        radius: width / 2
        visible: mark.phase === 2
        color: Theme.inkSoft
    }

    // Die Zahlen im Häkchen sind Anteile der Zeichenfläche, keine Rastervielfachen —
    // dieselbe ausgewiesene Ausnahme wie beim Roboter: Eine Zeichnung hat
    // Proportionen, kein Raster.
    Canvas {                   // Häkchen als Pfad, nicht als Zeichen U+2713: ein Zeichen
                               // wäre eine Wette darauf, dass die mitgelieferte Schrift es
                               // führt (aus Runde 1 übernommen, Kritik 2.5).
        anchors.centerIn: parent
        width: Theme.space.s + 2
        height: Theme.space.s + 2
        visible: mark.phase === 2
        onPaint: {
            var c = getContext("2d")
            c.clearRect(0, 0, width, height)
            c.strokeStyle = Theme.surface
            c.lineWidth = 1.6
            c.lineCap = "round"
            c.lineJoin = "round"
            c.beginPath()
            c.moveTo(width * 0.18, height * 0.52)
            c.lineTo(width * 0.42, height * 0.76)
            c.lineTo(width * 0.84, height * 0.24)
            c.stroke()
        }
    }

    Rectangle {                // dran: Ring mit Kern
        anchors.centerIn: parent
        width: Theme.space.m + Theme.space.xs
        height: width
        radius: width / 2
        visible: mark.phase === 1
        color: "transparent"
        border.width: Theme.focusWidth
        border.color: Theme.accent

        Rectangle {
            anchors.centerIn: parent
            width: Theme.space.s
            height: width
            radius: width / 2
            color: Theme.accentFill
        }
    }

    Rectangle {                // offen: leerer Ring
        anchors.centerIn: parent
        width: Theme.space.m
        height: width
        radius: width / 2
        visible: mark.phase === 0
        color: "transparent"
        border.width: Theme.borderWidth
        border.color: Theme.inkFaint
    }
}
