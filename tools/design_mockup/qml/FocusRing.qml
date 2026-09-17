import QtQuick
import Mock

// Der sichtbare Tastaturfokus — Teil des Systems, nicht Zubehör (review_round1.md B13:
// kein einziges Bauteil des alten Entwurfs kannte `activeFocus`).
//
// Gezeichnet wird in `accent`, nie in der Kantenfarbe. Bei einem kleinen Bauteil liegt er
// **außen** herum (`inset` negativ), damit dessen eigene Kante sichtbar bleibt; bei einer
// Fläche, die `clip` setzt, liegt er mit `inset: 0` genau auf deren Kante — außen würde
// die Fläche ihn wegschneiden, und der Fokus wäre unsichtbar, ohne dass irgendetwas
// warnt. Die gemeinsame Prüfzeile aller sieben Bildschirme verlangt ihn im Screenshot.
Rectangle {
    id: ring

    objectName: "focusRing"

    property bool shown: false
    property int inset: -Theme.space.xs

    anchors.fill: parent
    anchors.margins: inset
    visible: shown
    color: "transparent"
    radius: (parent && parent.radius !== undefined ? parent.radius : Theme.radius) - inset
    border.width: Theme.focusWidth
    border.color: Theme.accent
}
