import QtQuick
import Mock

// Die Bildlaufleiste. Sie war der teuerste fehlende Posten des alten Entwurfs (Kritik
// Runde 1, B5: „Nirgends im Bestand gibt es einen Bildlauf") — die Blockliste rechnete
// stattdessen die sichtbaren Zeilen aus der Panelhöhe und schnitt den Rest mit einer Zahl
// ab, die zudem falsch war (B11).
//
// Sie hängt an `visibleArea` einer echten `ListView`, sagt also die Wahrheit über Größe
// und Lage des Ausschnitts, und sie ist nur da, wenn es etwas zu rollen gibt. Zwei Pixel
// breit und in `inkFaint`: Sie ist eine Angabe, kein Bedienelement — gerollt wird mit der
// Tastatur.
Rectangle {
    id: track

    property var view: null

    readonly property bool needed: view && view.visibleArea.heightRatio < 1

    width: Theme.space.xs
    radius: width / 2
    visible: needed
    color: Theme.hairline

    Rectangle {
        width: parent.width
        radius: parent.radius
        color: Theme.inkFaint
        y: track.needed ? track.height * track.view.visibleArea.yPosition : 0
        height: track.needed ? Math.max(Theme.space.l, track.height * track.view.visibleArea.heightRatio) : 0
    }
}
