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

        // Kein `required property` am Delegaten (anders als in
        // tools/design_mockup/qml/Setup.qml): Zusätzliche Eigenschaften auf einem
        // eingebetteten `Text`-Delegaten erzeugen einen eigenen QML-Untertyp, dessen
        // `metaObject().className()` nicht mehr `"QQuickText"` heißt — genau das Muster,
        // gegen das `layout_check.py`/`contrast_check.py` prüfen (am Bestand geprüft: mit
        // `required property` blieben die sieben Zeilen hier ungemessen). `index` und
        // `modelData` stehen als Kontexteigenschaften auch ohne Deklaration zur
        // Verfügung, solange diese Datei kein `pragma ComponentBehavior: Bound` setzt.
        Repeater {
            model: screen.upcomingScreens

            delegate: Text {
                objectName: "upcomingItem"
                text: (index + 1) + "  " + modelData
                color: Theme.inkFaint
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.normal
            }
        }
    }
}
