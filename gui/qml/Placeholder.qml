import QtQuick

// Platzhalter-Bildschirm (bauplan-phase2.md AP 15, Nachtrag 17.09.2026).
//
// Die eigentlichen sieben Bildschirme entstehen erst ab AP 16a (konzept.md, „Die sieben
// Bildschirme der Oberfläche"); bis dahin zeigt der Bildschirmstapel aus `Main.qml` nur
// diesen einen. Er trägt Vorführdaten statt einer leeren Fläche — genug echten Text, damit
// `tools/gui_screenshot.py` schon jetzt etwas zu messen hat: QML-Warnungen, Layoutüberlauf,
// Kontrast im gerenderten Bild an jeder Textstelle (technik.md §14, „Gemessen wird im
// Bild, nicht aus den Token").
Item {
    id: screen

    readonly property int margin: Theme.pageMargin(width)

    // Die sieben kommenden Bildschirme, in der Reihenfolge aus konzept.md — reine
    // Vorführdaten, keine Programmlogik: Die Liste steuert nichts, sie füllt den
    // Platzhalter nur mit echtem statt erfundenem Text.
    readonly property var upcomingScreens: [
        "Einrichtung",
        "Buch und Kapitel",
        "Fortschritt",
        "Triage-Liste",
        "Triage-Eintrag",
        "Blockende",
        "Abschluss",
    ]

    Rectangle {
        anchors.fill: parent
        color: Theme.ground
    }

    Column {
        id: layout
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: screen.margin
        spacing: Theme.space.m

        Text {
            objectName: "headline"
            text: "LibreVerbum"
            color: Theme.ink
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.title
            font.weight: Theme.strong
        }

        Text {
            objectName: "subtitle"
            text: "Gerüst der Oberfläche — bauplan-phase2.md AP 15"
            color: Theme.inkSoft
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.small
        }

        Rectangle {
            width: layout.width
            height: Theme.borderWidth
            color: Theme.hairline
        }

        Text {
            objectName: "body"
            width: layout.width
            wrapMode: Text.WordWrap
            text: "Die sieben Bildschirme aus konzept.md entstehen ab AP 16a. Bis dahin " +
                  "steht hier nur dieser Platzhalter mit Vorführdaten, damit die " +
                  "Screenshot-Prüfschleife schon jetzt etwas zu messen hat."
            color: Theme.ink
            font.family: Theme.fonts.book
            font.pixelSize: Theme.size.reading
        }

        Text {
            objectName: "listLabel"
            text: "Kommende Bildschirme:"
            color: Theme.inkSoft
            font.family: Theme.fonts.ui
            font.pixelSize: Theme.size.small
        }

        // `required property` am Delegaten ist seit der Nachbesserung von Befund B1
        // (Durchsicht d993e3e) wieder unbedenklich: `tools/gui_screenshot.py` erkennt
        // eine Textstelle über `inherits("QQuickText")`, nicht mehr über den wörtlichen
        // Vergleich `className() == "QQuickText"` — ein `required property`-Delegat
        // erzeugt zwar einen eigenen QML-Untertyp mit einem anderen Metaobjektnamen,
        // bleibt aber ein Nachkomme von `QQuickText` und wird deshalb weiter gemessen
        // (am Bestand geprüft, siehe tests/test_gui_screenshot.py).
        Repeater {
            model: screen.upcomingScreens

            delegate: Text {
                id: upcomingDelegate
                required property int index
                required property string modelData

                objectName: "upcomingItem"
                text: (upcomingDelegate.index + 1) + "  " + upcomingDelegate.modelData
                color: Theme.inkFaint
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.normal
            }
        }
    }
}
