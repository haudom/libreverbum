import QtQuick
import QtQuick.Layouts
import Mock

// Bildschirm 1 — Einrichtung.
//
// Er ist hier, weil er der Beweis ist, dass die Richtung ein **Formular** trägt: Textzeile
// mit Pfad, Auswahlknöpfe, Fortschrittsbalken mit zwei Zahlen, Schaltflächen in zwei
// Rängen — und ein sichtbares Meldungsfeld. Von all dem existierte in Runde 1 kein
// einziges Bauteil (review_round1.md B5).
//
// Gerendert wird der **Fehlerfall**: Der Bezug des Wörterbuchs ist gescheitert, die
// Meldung steht im Wortlaut im Fenster, der Balken bleibt stehen, wo er stehen blieb, und
// „Herunterladen" ist wieder bedienbar (Prüfzeile 1.5, Regel 13). Das ist der ungünstigste
// Datenfall dieses Bildschirms: die längste Meldung, der längste Quellenhinweis und alle
// drei Schritte gleichzeitig sichtbar. `--fall laeuft` zeigt stattdessen den laufenden
// Bezug (Prüfzeile 1.4).
//
// Die Liste der Schritte ist das **dehnbare** Element und rollt; Kopfzeile und Fußleiste
// stehen fest. Damit ist „Weiter" bei 900×600 ohne Rollen erreichbar (Prüfzeile 1.8) —
// ohne dass irgendetwas aus dem Fenster laufen kann (B1/B2).
Item {
    id: screen

    readonly property bool narrow: width < Theme.narrowWidth
    readonly property int margin: Theme.pageMargin(width)
    readonly property int pad: Theme.cardPadding(width)
    readonly property bool running: Content.variant === "laeuft"

    Rectangle { anchors.fill: parent; color: Theme.ground }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Kopf: Name und Datenverzeichnis ─────────────────────────────────────────
        // Der vollständige Pfad steht sichtbar im Fenster, nicht nur auf `stderr`
        // (Prüfzeile 1.1, technik.md §9). Er steht in der Programmschrift und in `ink`:
        // Er ist eine Angabe, die man abliest und abtippt, kein Beiwerk.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.headerFor(screen.width) + Theme.space.m

            Text {
                anchors.left: parent.left
                anchors.leftMargin: screen.margin
                anchors.bottom: parent.bottom
                text: "LibreVerbum"
                color: Theme.ink
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.title
                font.weight: Theme.strong
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: screen.margin
            Layout.rightMargin: screen.margin
            Layout.topMargin: Theme.space.s
            Layout.preferredHeight: Theme.controlHeight
            spacing: Theme.space.m

            Text {
                text: "Daten liegen in"
                color: Theme.inkSoft
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.small
            }

            Text {
                Layout.fillWidth: true
                text: Content.dataPath
                color: Theme.ink
                font.family: Theme.fonts.ui
                font.pixelSize: Theme.size.small
                elide: Text.ElideMiddle
            }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.leftMargin: screen.margin
            Layout.rightMargin: screen.margin
            Layout.preferredHeight: Theme.borderWidth
            color: Theme.hairline
        }

        // ── Das Blatt: die drei Schritte ────────────────────────────────────────────
        Sheet {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: screen.margin
            Layout.rightMargin: screen.margin
            Layout.topMargin: Theme.space.m

            Flickable {
                id: flick

                anchors.fill: parent
                anchors.margins: screen.pad
                anchors.rightMargin: screen.pad + Theme.space.s
                contentWidth: width
                contentHeight: steps.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds

                ColumnLayout {
                    id: steps

                    objectName: "listContent"
                    width: flick.width
                    spacing: Theme.space.xl

                    SetupStep {
                        Layout.fillWidth: true
                        number: 1
                        title: "Einstellungen"
                        detail: "config.toml"
                        phase: 2
                    }

                    SetupStep {
                        Layout.fillWidth: true
                        number: 2
                        title: "Wörterbuch"
                        detail: "fehlt — " + Content.totalMegabytes.toLocaleString(
                                    Qt.locale("de_DE"), "f", 1) + " MB werden geladen"
                        phase: 1

                        // Der Quellenhinweis steht **im Wortlaut** und wird nicht gekürzt
                        // (Prüfzeile 1.3): Er ist die Lizenzauflage von WikDict, kein
                        // Beipackzettel. Deshalb bricht er um, statt mit „…" zu enden.
                        Text {
                            Layout.fillWidth: true
                            text: Content.sourceNotice
                            color: Theme.inkSoft
                            wrapMode: Text.WordWrap
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.small
                            lineHeight: 1.35
                        }

                        MessageBox {
                            Layout.fillWidth: true
                            visible: !screen.running
                            text: Content.downloadError
                        }

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: Theme.space.m

                            // Nach dem Fehlschlag ist „Herunterladen" wieder bedienbar und
                            // trägt den Fokus — der nächste Tastendruck gehört dorthin,
                            // wo der Lauf abgebrochen ist.
                            ActionButton {
                                label: screen.running ? "Bezug läuft …" : "Herunterladen"
                                primary: true
                                enabled: !screen.running
                                focused: !screen.running
                            }

                            // Der Fokus liegt immer auf der Schaltfläche, die gerade
                            // etwas tun kann: läuft der Bezug, ist das „Abbrechen", sonst
                            // „Herunterladen". Ein Fokusring auf einem unbedienbaren
                            // Element wäre ein Versprechen, das der nächste Tastendruck
                            // nicht einlöst.
                            ActionButton {
                                label: "Abbrechen"
                                enabled: screen.running
                                focused: screen.running
                            }

                            MeterBar {
                                Layout.fillWidth: true
                                Layout.minimumWidth: Theme.space.xxl * 3
                                value: Content.loadedMegabytes
                                maximum: Content.totalMegabytes
                                stopped: !screen.running
                                caption: Content.loadedMegabytes.toLocaleString(
                                             Qt.locale("de_DE"), "f", 1) + " von "
                                         + Content.totalMegabytes.toLocaleString(
                                             Qt.locale("de_DE"), "f", 1) + " MB"
                            }
                        }
                    }

                    SetupStep {
                        Layout.fillWidth: true
                        number: 3
                        title: "Profil"
                        detail: "profil.sqlite3 wird neu angelegt"
                        phase: 0

                        Text {
                            Layout.fillWidth: true
                            text: "Sprachniveau"
                            color: Theme.inkSoft
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.small
                        }

                        // Sechs Stufen mit der Zahl vorbelegter Grundformen aus
                        // `pipeline.PRESET_WORD_COUNT`; C2 kommt nicht vor (Prüfzeile 1.6,
                        // technik.md §11). Drei Spalten, damit die sechste Stufe nicht in
                        // eine eigene Zeile rutscht und dort wie ein Nachtrag aussieht.
                        GridLayout {
                            Layout.fillWidth: true
                            columns: screen.narrow ? 2 : 3
                            columnSpacing: Theme.space.xl
                            rowSpacing: Theme.space.s

                            Repeater {
                                model: Content.levels
                                delegate: RadioOption {
                                    required property var modelData
                                    required property int index
                                    label: modelData[0]
                                    detail: modelData[1]
                                    selected: index === Content.chosenLevel
                                }
                            }
                        }

                        // Prüfzeile 1.7: Der Satz steht über „Weiter", nicht in einem
                        // aufklappbaren Hinweis. Er ist die einzige nicht zurücknehmbare
                        // Entscheidung dieses Bildschirms und steht deshalb im Klartext da.
                        Text {
                            Layout.fillWidth: true
                            text: "Die Vorbelegung ist einmalig und nicht zurücknehmbar."
                            color: Theme.inkSoft
                            wrapMode: Text.WordWrap
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.small
                        }
                    }
                }
            }

            ScrollTrack {
                anchors.right: parent.right
                anchors.rightMargin: Theme.space.s
                anchors.top: parent.top
                anchors.bottom: parent.bottom
                anchors.margins: Theme.space.s
                view: flick
            }
        }

        // ── Fuß ─────────────────────────────────────────────────────────────────────
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.footerFor(screen.width) + Theme.space.m

            // „Weiter" ist unbedienbar, solange das Wörterbuch fehlt — ohne es kann
            // kein Kapitel vorbereitet werden. Eine Schaltfläche, die man drücken darf
            // und die dann nichts kann, wäre die freundlichere Lüge; unbedienbar ist die
            // Auskunft. Prüfzeile 1.8 verlangt nur, dass sie ohne Rollen **erreichbar**
            // ist, und das ist sie: Sie steht in der festen Fußleiste.
            ActionButton {
                anchors.right: parent.right
                anchors.rightMargin: screen.margin
                anchors.verticalCenter: parent.verticalCenter
                label: "Weiter"
                primary: true
                enabled: false
            }
        }
    }
}
