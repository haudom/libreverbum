import QtQuick
import Mock

// Auswahlknopf für die sechs Niveaustufen der Einrichtung.
//
// Zustand als **Form**, nicht nur als Farbe: gewählt ist ein Ring mit Kern, offen ein
// leerer Ring. Dieselbe Sprache wie die Etappen des Fortschritts (review_round1.md 2.4 —
// „überlebt jede Gestaltungswahl"). Der leere Ring wird in `inkFaint` gezeichnet und nicht
// in der Kantenfarbe: Ein Bedienelement braucht 3:1, und der alte leere Ring hatte 1,63:1.
Item {
    id: option

    property string label: ""
    property string detail: ""
    property bool selected: false
    property bool focused: false

    implicitHeight: Theme.controlHeight
    implicitWidth: dot.width + Theme.space.s + texts.implicitWidth

    Rectangle {
        id: dot
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.space.m
        height: Theme.space.m
        radius: width / 2
        color: "transparent"
        border.width: option.selected ? Theme.focusWidth : Theme.borderWidth
        border.color: option.selected ? Theme.accent : Theme.inkFaint

        Rectangle {
            anchors.centerIn: parent
            width: Theme.space.s
            height: Theme.space.s
            radius: width / 2
            visible: option.selected
            color: Theme.accent
        }
    }

    Row {
        id: texts
        anchors.left: dot.right
        anchors.leftMargin: Theme.space.s
        anchors.verticalCenter: parent.verticalCenter
        spacing: Theme.space.s

        Text {
            text: option.label
            color: Theme.ink
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.normal
            font.weight: option.selected ? Theme.strong : Theme.regular
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: option.detail
            color: Theme.inkFaint
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.small
        }
    }

    FocusRing {
        shown: option.focused
        inset: -Theme.space.xs
        radius: Theme.radius
    }
}
