import QtQuick
import Mock

// Die Tastenkappe: ein kleines Quadrat mit dem Buchstaben, das vor einer Beschriftung
// steht und in einem Bauteil sagt, dass dieselbe Sache über die Tastatur geht.
//
// Aus Runde 1 übernommen (review_round1.md 2.7: „die richtige Lösung für Prüfzeile 5.9 und für
// einen Nutzer, der das Werkzeug lange benutzt") — nur der Behälter ist weg. Sie ist
// **nie gefüllt**: Eine gefüllte Taste hieße „gedrückt" oder „gewählt", und beides ist auf
// der Triage keine Aussage, die die Oberfläche machen darf (B12).
Rectangle {
    id: cap

    property string key: ""
    property color tone: Theme.inkSoft

    // Quadratisch, solange der Buchstabe hineinpasst — und breiter, sobald er es nicht
    // tut. Eine feste Breite von 24 px hat „Esc" auf dem Fortschrittsbildschirm über den
    // eigenen Rand hinaus geschrieben, ohne dass eine Warnung kam: derselbe stille
    // Fehlschlag wie B1, nur im Kleinen.
    implicitWidth: Math.max(Theme.space.l, label.implicitWidth + Theme.space.s + Theme.space.xs)
    implicitHeight: Theme.space.l
    radius: Theme.radiusKey
    color: "transparent"
    border.width: Theme.borderWidth
    border.color: tone

    Text {
        id: label
        anchors.centerIn: parent
        text: cap.key
        color: cap.tone
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.tag
        font.weight: Theme.strong
    }
}
