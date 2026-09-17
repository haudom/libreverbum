import QtQuick
import QtQuick.Layouts
import Mock

// Bildschirm 2 — Buch und Kapitel.
//
// Er ist hier, weil er der Beweis ist, dass die Richtung eine **lange, rollbare Liste mit
// Auswahl** trägt. In Runde 1 gab es nirgends im Bestand einen Bildlauf (review_round1.md B5:
// „besonders hart"); die eine Liste des alten Entwurfs rechnete die sichtbaren Zeilen aus
// der Panelhöhe und schnitt den Rest mit einer Zahl ab, die zudem falsch war (B11).
//
// Hier ist die Liste eine echte `ListView` mit `currentIndex`, Bildlaufleiste und einer
// Kopfzeile, deren Spalten auf denselben Token sitzen wie die Zeilen darunter. Sie ist das
// **dehnbare** Element: Kopf und Fuß haben feste Höhen, die Liste bekommt den Rest
// (Prüfzeile 2.8).
//
// Zwei echte Bücher, zwei Fälle — beide aus `tools/*.epub`, keiner erfunden:
//
// - `--fall lang` (Vorgabe): „The Picture of Dorian Gray", 22 Kapitel, eingerückte
//   Gliederungsebene, **kein** Kapitel gewählt und der Hinweis auf die fehlende
//   Navigation über der Liste. Damit stehen der Bildlauf, die Einrückung (2.5), das
//   Hinweisfeld (2.6) und die unbedienbare Schaltfläche (2.4) in einem Bild.
// - `--fall kurz`: „The Adventures of Sherlock Holmes", 14 Kapitel — die Zahl, die
//   `pipeline.list_chapters` liefert, nicht 18 (Prüfzeile 2.2) —, die längsten
//   Kapiteltitel des Bestands, das gewählte Kapitel 2 und die übersprungene letzte Zeile
//   mit ihrem `skip_reason` im Klartext (2.3).
Item {
    id: screen

    readonly property bool narrow: width < Theme.narrowWidth
    readonly property int margin: Theme.pageMargin(width)
    readonly property bool hasNotice: Content.structureNotice !== ""
    readonly property int chosen: Content.selectedChapter      // 0 = keines
    // Wo die Tastatur steht — als **Kapitelnummer**, nicht als `currentIndex`. Grund:
    // Eine `ListView` rollt beim Setzen von `currentIndex` von selbst dorthin, und damit
    // war der erste Screenshot oben um eine Zeile verschoben, ohne dass etwas gemeldet
    // wurde. Die Liste steht jetzt oben, wo sie beim Öffnen steht, und der Ring sagt
    // unabhängig davon, wo der nächste Tastendruck wirkt. Im Dorian-Fall ist noch nichts
    // gewählt — genau dafür ist der Ring da.
    readonly property int cursorRow: Content.longBook ? 4 : 2

    // Die Spalten der Liste. Sie stehen hier, weil die Kopfzeile dieselben Werte braucht
    // wie die Zeilen — zwei getrennte Zahlenreihen wären zwei Kanten.
    readonly property int numberColumn: Theme.space.xl
    readonly property int gutter: Theme.space.m

    // **Das Maß der Tabelle** (review_round3.md C3). Sie lief über die volle Fensterbreite,
    // und damit lagen bei 1280 zwischen „V. THE FIVE ORANGE PIPS" und seiner Wortzahl rund
    // 900 px Nichts — vierzehnmal untereinander, ohne Führungsstrich. Das ist die
    // klassische Falle der breiten Tabelle und der Grund, warum der Bildschirm nach
    // Datenbankmaske aussah und nicht nach Inhaltsverzeichnis; bei 900 px Fensterbreite
    // war derselbe Abstand rund 500 px, und das Bild wirkte prompt besser.
    //
    // 880 px, mittig im Fenster. Die eine Entscheidung dieses Bildschirms — welches
    // Kapitel bereite ich vor, und wie groß ist es — ist damit bei der Arbeitsgröße
    // genauso leicht zu treffen wie beim kleinen Fenster: Zwischen dem längsten Titel und
    // seiner Zahl liegen jetzt rund 500 px statt 900, dasselbe Maß, bei dem das kleine
    // Fenster schon vorher besser aussah. **Alles** richtet sich danach, auch Kopf und
    // Fuß — eine zentrierte Tabelle unter einer randbündigen Überschrift wären zwei
    // Ausrichtungen auf einem Bildschirm.
    //
    // 880 und nicht die vorgeschlagenen 800: **Am Bild gesehen**, dass bei 800 der Kopf
    // zu eng wird und „The Adventures of Sherlock Holmes · Arthur Conan Doyle" neben der
    // Schaltfläche zu „… Arthur Conan Do…" gekürzt wird. Prüfzeile 2.1 verlangt Titel
    // **und** Autor; die 80 px kosten am Abstand in der Tabelle nichts Sichtbares.
    readonly property int tableWidth: Math.min(width - margin * 2, 880)
    readonly property int tableMargin: Math.round((width - tableWidth) / 2)

    Rectangle { anchors.fill: parent; color: Theme.ground }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Kopf: Titel und Autor aus den EPUB-Metadaten ────────────────────────────
        // Prüfzeile 2.1: Titel und Autor, nicht der Dateiname. Beides ist Sprachmaterial
        // und steht in der Buchschrift.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.headerFor(screen.width) + Theme.space.m

            Text {
                objectName: "listTitle"
                anchors.left: parent.left
                anchors.leftMargin: screen.tableMargin
                anchors.right: openButton.left
                anchors.rightMargin: Theme.space.l
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Theme.space.xs
                text: "<font color=\"" + Theme.ink + "\">" + Content.listBookTitle + "</font>"
                      + "<font color=\"" + Theme.inkSoft + "\"> · " + Content.listBookAuthor
                      + "</font>"
                textFormat: Text.StyledText
                font.family: Theme.fonts.book
                font.pixelSize: Theme.size.title
                elide: Text.ElideRight
            }

            ActionButton {
                id: openButton
                anchors.right: parent.right
                anchors.rightMargin: screen.tableMargin
                anchors.bottom: parent.bottom
                label: "Buch öffnen"
            }
        }

        // Der Hinweis auf die fehlende Navigation steht **über** der Liste und nicht in
        // einer Statuszeile (Prüfzeile 2.6). Er ist kein Fehlschlag, sondern eine
        // Einschränkung — deshalb die Tonlage `hinweis` und nicht `warn`.
        MessageBox {
            Layout.fillWidth: true
            Layout.leftMargin: screen.tableMargin
            Layout.rightMargin: screen.tableMargin
            Layout.bottomMargin: Theme.space.m
            visible: screen.hasNotice
            tone: "hinweis"
            text: Content.structureNotice
        }

        // ── Spaltenköpfe ────────────────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.leftMargin: screen.tableMargin
            Layout.rightMargin: screen.tableMargin
            Layout.preferredHeight: Theme.space.l

            Text {
                anchors.left: parent.left
                anchors.leftMargin: Theme.space.m
                anchors.bottom: parent.bottom
                width: screen.numberColumn
                horizontalAlignment: Text.AlignRight
                text: "NR"
                color: Theme.inkFaint
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.tag
                font.weight: Theme.strong
                font.letterSpacing: 0.8
            }

            Text {
                anchors.left: parent.left
                anchors.leftMargin: Theme.space.m + screen.numberColumn + screen.gutter
                anchors.bottom: parent.bottom
                text: "KAPITEL"
                color: Theme.inkFaint
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.tag
                font.weight: Theme.strong
                font.letterSpacing: 0.8
            }

            Text {
                anchors.right: parent.right
                anchors.rightMargin: Theme.space.m
                anchors.bottom: parent.bottom
                text: "WÖRTER"
                color: Theme.inkFaint
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.tag
                font.weight: Theme.strong
                font.letterSpacing: 0.8
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: screen.tableMargin
            Layout.rightMargin: screen.tableMargin
            Layout.topMargin: Theme.space.xs
            Layout.preferredHeight: Theme.borderWidth
            color: Theme.hairline
        }

        // ── Die Liste ───────────────────────────────────────────────────────────────
        Sheet {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: screen.tableMargin
            Layout.rightMargin: screen.tableMargin
            Layout.topMargin: Theme.space.s
            outlined: false

            ListView {
                id: list

                anchors.fill: parent
                anchors.topMargin: Theme.space.s
                anchors.bottomMargin: Theme.space.s
                anchors.rightMargin: Theme.space.m
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                model: Content.chapters
                currentIndex: -1

                delegate: ChapterRow {
                    required property var modelData
                    required property int index
                    width: list.width
                    number: modelData[0]
                    title: modelData[1]
                    level: modelData[2]
                    words: modelData[3]
                    skipReason: modelData[4]
                    selected: modelData[0] === screen.chosen

                    // Der Ring sagt „hier wirkt der nächste Tastendruck", die Füllung sagt
                    // „das ist gewählt". Zwei Aussagen, zwei Zeichen — im alten Entwurf
                    // gab es für beides nichts (B13).
                    FocusRing {
                        shown: modelData[0] === screen.cursorRow
                        inset: 0
                    }
                }
            }

            ScrollTrack {
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.margins: Theme.space.xs
                view: list
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: screen.tableMargin
            Layout.rightMargin: screen.tableMargin
            Layout.preferredHeight: Theme.borderWidth
            color: Theme.hairline
        }

        // ── Fuß: was gewählt ist und was man damit tun kann ─────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.footerFor(screen.width) + Theme.space.m

            Text {
                anchors.left: parent.left
                anchors.leftMargin: screen.tableMargin + Theme.space.m
                anchors.verticalCenter: parent.verticalCenter
                // Ohne Auswahl steht da nicht nichts, sondern der Grund, warum
                // „Vorbereiten" nicht geht. Eine graue Schaltfläche ohne Erklärung ist
                // eine Sackgasse.
                text: screen.chosen > 0
                      ? "Gewählt: Kapitel " + screen.chosen
                      : "Kein Kapitel gewählt — zum Vorbereiten eines auswählen"
                color: screen.chosen > 0 ? Theme.ink : Theme.inkSoft
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.small
            }

            RowLayout {
                anchors.right: parent.right
                anchors.rightMargin: screen.tableMargin
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space.m

                // „Buch prüfen" geht auch ohne gewähltes Kapitel (Prüfzeile 2.7) — es
                // prüft das Buch, nicht das Kapitel.
                ActionButton {
                    label: "Buch prüfen"
                }

                ActionButton {
                    label: "Vorbereiten"
                    primary: true
                    enabled: screen.chosen > 0
                }
            }
        }
    }
}
