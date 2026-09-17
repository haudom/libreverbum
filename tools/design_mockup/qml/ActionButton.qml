import QtQuick
import Mock

// Schaltfläche in zwei Rängen und drei Zuständen — das Bauteil, das dem alten Entwurf
// vollständig fehlte (review_round1.md B5: „Schaltfläche **ohne** Tastenkappe in zwei
// Rängen").
//
// `primary` füllt mit `accentFill` und schreibt in `inkOnAccent`; sekundär ist eine
// Umrisslinie. `enabled: false` nimmt die Farbe auf `inkFaint` zurück — unbedienbar ist
// ein eigener Zustand und nicht bloß blasser (Prüfzeile 2.4 verlangt ihn im Bild).
// `shortcut` hängt eine Tastenkappe davor, wo dieselbe Sache auch über die Tastatur geht.
Item {
    id: button

    property string label: ""
    property string shortcut: ""
    property bool primary: false
    property bool focused: false

    implicitHeight: Theme.controlHeight
    implicitWidth: body.implicitWidth + Theme.space.l * 2

    Rectangle {
        id: body
        anchors.fill: parent
        radius: Theme.radius
        color: button.primary && button.enabled ? Theme.accentFill : "transparent"
        border.width: button.primary && button.enabled ? 0 : Theme.borderWidth
        border.color: button.enabled ? Theme.inkSoft : Theme.hairline

        implicitWidth: row.implicitWidth

        readonly property color contentColor: !button.enabled
                                              ? Theme.inkFaint
                                              : (button.primary ? Theme.inkOnAccent : Theme.ink)

        Row {
            id: row
            anchors.centerIn: parent
            spacing: Theme.space.s

            KeyCap {
                key: button.shortcut
                tone: body.contentColor
                visible: button.shortcut !== ""
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: button.label
                color: body.contentColor
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.small
                font.weight: button.primary ? Theme.strong : Theme.regular
            }
        }
    }

    FocusRing { shown: button.focused }
}
