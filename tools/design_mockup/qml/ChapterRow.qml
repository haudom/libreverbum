import QtQuick
import Mock

// Eine Zeile der Kapitelliste: Nummer · Titel · Wortzahl — oder statt der Zahl der
// `skip_reason` im Klartext.
//
// Drei Spalten, beide Zahlenspalten rechtsbündig, Einrückung je Gliederungsebene
// (Prüfzeile 2.2–2.5). Ein übersprungenes Kapitel ist nicht bloß blasser, sondern trägt
// **den Grund** — eine gedimmte Zeile ohne Grund wäre genau die stille Auslassung, gegen
// die Regel 1 steht.
Item {
    id: row

    property int number: 0
    property string title: ""
    property int level: 0
    property int words: 0          // -1: nicht lesbar
    property string skipReason: ""
    property bool selected: false

    readonly property bool skipped: skipReason !== ""

    implicitHeight: Theme.tableRowHeight

    Rectangle {
        anchors.fill: parent
        visible: row.selected
        color: Theme.marked
        radius: Theme.radiusTag
    }

    Rectangle {
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.markerWidth
        height: parent.height - Theme.space.s
        radius: width / 2
        visible: row.selected
        color: Theme.accentFill
    }

    Text {
        id: number
        anchors.left: parent.left
        anchors.leftMargin: Theme.space.m
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.space.xl
        horizontalAlignment: Text.AlignRight
        text: row.number
        color: Theme.inkFaint
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
    }

    Text {
        anchors.left: number.right
        anchors.leftMargin: Theme.space.m + row.level * Theme.space.l
        anchors.right: right.left
        anchors.rightMargin: Theme.space.m
        anchors.verticalCenter: parent.verticalCenter
        text: row.title
        color: row.skipped ? Theme.inkFaint : Theme.ink
        font.family: Theme.fonts.book
        font.pixelSize: Theme.size.normal
        font.weight: row.selected ? Theme.strong : Theme.regular
        elide: Text.ElideRight
    }

    Text {
        id: right
        anchors.right: parent.right
        anchors.rightMargin: Theme.space.m
        anchors.verticalCenter: parent.verticalCenter
        horizontalAlignment: Text.AlignRight
        // Nur die Zahl: Das Wort „Wörter" steht einmal im Spaltenkopf und muss nicht in
        // jeder der zweiundzwanzig Zeilen wiederholt werden. Die Zahlen bilden dadurch
        // eine Spalte, die man von oben nach unten lesen kann.
        text: row.skipped
              ? row.skipReason
              : (row.words < 0 ? "nicht lesbar"
                               : row.words.toLocaleString(Qt.locale("de_DE"), "f", 0))
        color: Theme.inkFaint
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
    }
}
