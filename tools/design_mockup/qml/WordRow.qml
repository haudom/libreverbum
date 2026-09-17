import QtQuick
import Mock

// Eine Zeile der Blockliste: Nummer · Wortart · Wortform · Häufigkeit.
//
// Vier Spalten mit festen Breiten, damit es eine linke **und** eine rechte Kante gibt
// (review_round1.md B10: im alten Entwurf saßen Zahlen bei 30 px, Marken bei 14 px und
// zusätzlich um 3° gekippt). Die Nummer ist rechtsbündig und steht immer da: Ohne sie ist
// die Sammelaktion nicht bedienbar, die „Bis zu welcher **Nummer** kennst du alles?"
// fragt (Prüfzeile 4.1/4.6). Die Häufigkeit steht ebenfalls immer da und verschwindet
// nicht, sobald daneben etwas anderes auftaucht (B10, zweiter Punkt).
//
// Die Wortform steht in der Buchschrift, die drei Angaben darum in der Oberflächenschrift:
// Sprachmaterial gegen Programmstimme (siehe `Theme.fonts`).
Item {
    id: row

    property int number: 0
    property string pos: ""
    property string word: ""
    property int frequency: 0
    property bool current: false
    // Beim schmalen Fenster geben die beiden Ränder je eine halbe Rastereinheit ab. Es
    // schrumpft der Rand, nie der Inhalt (review_round1.md B21) — hier in der Spalte
    // genauso wie auf der Seite.
    property bool compact: false

    readonly property int side: compact ? Theme.space.s : Theme.space.m

    implicitHeight: Theme.rowHeight

    Rectangle {
        anchors.fill: parent
        visible: row.current
        color: Theme.marked
        radius: Theme.radiusTag
    }

    // Der Akzentbalken sagt „hier bist du gerade" — die einzige Bedeutung, die `accent`
    // in dieser Richtung trägt.
    Rectangle {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.markerWidth
        height: parent.height - Theme.space.s
        radius: width / 2
        visible: row.current
        color: Theme.accentFill
    }

    Text {
        id: number
        anchors.left: parent.left
        anchors.leftMargin: row.side
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.space.l
        horizontalAlignment: Text.AlignRight
        text: row.number
        color: Theme.inkFaint
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
    }

    Text {
        id: part
        anchors.left: number.right
        anchors.leftMargin: Theme.space.s
        anchors.verticalCenter: parent.verticalCenter
        // Die Wortartspalte ist über alle Zeilen gleich breit (Prüfzeile 4.2) und so
        // schmal, wie die vier vorkommenden Kürzel es zulassen. Sie war eine volle
        // Rastereinheit breiter, und die fehlte dann der Wortform: Bei 900×600 wurde
        // `photograph` in der Seitenliste gekürzt — gemeldet von `layout_check.py`,
        // im Bild kaum zu sehen und nach Regel 1 trotzdem ein Fehlschlag.
        width: Theme.space.xxl - Theme.space.s
        text: row.pos
        color: Theme.inkFaint
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.tag
        font.weight: Theme.strong
        font.letterSpacing: 0.5
    }

    Text {
        anchors.left: part.right
        anchors.leftMargin: Theme.space.s
        anchors.right: count.left
        anchors.rightMargin: Theme.space.s
        anchors.verticalCenter: parent.verticalCenter
        text: row.word
        color: Theme.ink
        font.family: Theme.fonts.book
        font.pixelSize: Theme.size.normal
        font.weight: row.current ? Theme.strong : Theme.regular
        elide: Text.ElideRight
    }

    Text {
        id: count
        anchors.right: parent.right
        anchors.rightMargin: row.side
        anchors.verticalCenter: parent.verticalCenter
        text: row.frequency + "×"
        color: Theme.inkFaint
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
    }
}
