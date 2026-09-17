import QtQuick
import Mock

// Eine Etappe des Kapitellaufs.
//
// Das Zustandszeichen links steht in `StateMark` — dieselbe Form, die auch die drei
// Schritte der Einrichtung tragen.
//
// Der Zähler steht nur da, wo `ChapterProgress` einen führt. Wo `done == total == 0`
// steht **kein** Zähler (Prüfzeile 3.3, technik.md §13: ein erfundener Zähler behauptet
// Fortschritt, den es nicht gibt).
// **Wo der Zähler steht** (review_round3.md C2): Er hing am rechten Kartenrand, und
// zwischen „Buch analysieren" und „9 von 13 Kapiteln mit Text" lagen rund 550 px Leere —
// dieselbe Wanderung ohne Führungsstrich wie in der Kapitelliste. Er steht jetzt in einer
// eigenen Spalte **dicht hinter** den Etappennamen: nah genug, dass er zu seiner Zeile
// gehört, und ausgerichtet genug, dass sechs Zähler eine Spalte bilden statt eines
// Flatterrands. `counterColumn` setzt der Bildschirm, weil erst er die Kartenbreite kennt.
Item {
    id: stage

    property string label: ""
    property int phase: 0          // 0 offen, 1 läuft, 2 erledigt (`state` ist bei Item belegt)
    property string counter: ""
    property int counterColumn: 0  // linke Kante der Zählerspalte, vom Bildschirm gesetzt
    // Die Zeilenhöhe hängt an der **Fenster**breite, und die kennt die Zeile nicht: Ihre
    // eigene Breite ist die der Karte, und die ist in beiden Fenstern dieselbe.
    property int windowWidth: Theme.narrowWidth

    implicitHeight: Theme.stageHeight(stage.windowWidth)

    readonly property color toneColor: phase === 2 ? Theme.inkSoft
                                                   : (phase === 1 ? Theme.accent : Theme.inkFaint)

    StateMark {
        id: mark
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        phase: stage.phase
    }

    Text {
        objectName: "stageLabel"
        anchors.left: mark.right
        anchors.leftMargin: Theme.space.m
        anchors.verticalCenter: parent.verticalCenter
        width: Math.max(0, stage.counterColumn - Theme.space.m
                           - (mark.width + Theme.space.m))
        text: stage.label
        color: stage.phase === 1 ? Theme.ink : stage.toneColor
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.normal
        font.weight: stage.phase === 1 ? Theme.strong : Theme.regular
        elide: Text.ElideRight
    }

    Text {
        id: counter
        anchors.left: parent.left
        anchors.leftMargin: stage.counterColumn
        anchors.verticalCenter: parent.verticalCenter
        text: stage.counter
        color: Theme.inkSoft
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
    }
}
