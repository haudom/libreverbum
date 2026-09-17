import QtQuick
import QtQuick.Layouts
import Mock

// Ein Schritt der Einrichtung: Zeichen · Nummer · Titel · Auskunft, darunter eingerückt
// das, was dieser Schritt zu tun gibt.
//
// Prüfzeile 1.2 verlangt, dass die drei Schritte als nummerierte Liste untereinander
// stehen und **der offene der einzige mit Schaltflächen** ist. Deshalb trägt das Bauteil
// den Inhalt als eigenen Bereich und nicht jeder Bildschirmabschnitt seinen eigenen:
// Ein erledigter Schritt hat schlicht keinen.
//
// Die Einrückung ist kein gemalter Wert, sondern die Summe der Spalten links davon
// (24 + 8 + 16 + 16 = 64 = 8 × Rastereinheit) — der Inhalt beginnt genau unter dem Titel.
ColumnLayout {
    id: step

    property int number: 0
    property string title: ""
    property string detail: ""
    property int phase: 0          // 0 offen, 1 dran, 2 erledigt
    default property alias content: inner.data

    readonly property int indent: Theme.space.l + Theme.space.s + Theme.space.m + Theme.space.m

    spacing: 0

    RowLayout {
        Layout.fillWidth: true
        Layout.preferredHeight: Theme.space.xl
        spacing: Theme.space.s

        StateMark {
            phase: step.phase
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            Layout.preferredWidth: Theme.space.m
            Layout.alignment: Qt.AlignVCenter
            horizontalAlignment: Text.AlignRight
            text: step.number
            color: Theme.inkFaint
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.small
        }

        // Der Titel ist das dehnbare Element dieser Zeile und schiebt die Auskunft nach
        // rechts. Vorher stand dort ein Federelement und die Auskunft war auf die halbe
        // **Zeilenbreite** gedeckelt — das ist ein Maß, das von der Zeile abhängt, die es
        // selbst mitbestimmt, und Qt meldete prompt „Detected recursive rearrange".
        Text {
            Layout.leftMargin: Theme.space.s
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            text: step.title
            color: step.phase === 0 ? Theme.inkSoft : Theme.ink
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.normal
            font.weight: step.phase === 1 ? Theme.strong : Theme.regular
            elide: Text.ElideRight
        }

        Text {
            Layout.alignment: Qt.AlignVCenter
            horizontalAlignment: Text.AlignRight
            text: step.detail
            color: Theme.inkSoft
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.small
            elide: Text.ElideRight
        }
    }

    ColumnLayout {
        id: inner

        Layout.fillWidth: true
        Layout.leftMargin: step.indent
        Layout.topMargin: children.length > 0 ? Theme.space.s : 0
        spacing: Theme.space.m
    }
}
