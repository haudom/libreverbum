import QtQuick
import Mock

// Fortschrittsbalken mit Beschriftung und **zwei Zahlen** — geladen und gesamt.
//
// Prüfzeile 1.4 verlangt, dass sich die beiden Zahlen zwischen zwei Screenshots
// unterscheiden; ein Balken ohne Zahlen kann das nicht zeigen (review_round1.md B23: der
// alte Gelbalken hatte weder Beschriftung noch Zahlen). Die Zahlen stehen **neben** dem
// Balken, nicht darauf: Schrift auf einer laufenden Füllung wechselt mitten im Wort den
// Hintergrund und ist dann nicht mehr messbar.
Item {
    id: meter

    property real value: 0
    property real maximum: 1
    property string caption: ""
    property bool stopped: false

    implicitHeight: Theme.space.l

    Rectangle {
        id: track
        anchors.left: parent.left
        anchors.right: numbers.left
        anchors.rightMargin: Theme.space.m
        anchors.verticalCenter: parent.verticalCenter
        height: Theme.space.s
        radius: height / 2
        color: Theme.ground
        border.width: Theme.borderWidth
        border.color: Theme.hairline

        Rectangle {
            x: 0
            y: 0
            height: parent.height
            // Abgebrochen heißt: der Balken steht da, wo er stehen blieb, und zeigt den
            // Stand nicht als Erfolg. Die Farbe wechselt deshalb auf `warn` (Regel 13).
            width: Math.max(height, parent.width * Math.min(1, meter.value / meter.maximum))
            radius: height / 2
            color: meter.stopped ? Theme.warn : Theme.accentFill
        }
    }

    Text {
        id: numbers
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: meter.caption
        color: Theme.inkSoft
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
    }
}
