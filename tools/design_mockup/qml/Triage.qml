import QtQuick
import QtQuick.Layouts
import Mock

// Bildschirm 5 — Triage-Eintrag, zusammengelegt mit Bildschirm 4 (Blockliste).
//
// Die Zusammenlegung stammt aus Runde 1 und bleibt (review_round1.md 2.1): Die Blockliste steht
// dauerhaft links, der Eintrag rechts — ein Bildschirm statt zweier Modi. Wer
// dreihundertmal hintereinander entscheidet, muss jederzeit sehen, wo im Block er steht,
// ohne umzuschalten.
//
// **Die Layoutregel dieses Bildschirms**, die Antwort auf B1/B2: Kopf und Fuß haben feste
// Höhen aus Token, die beiden Blätter füllen den Rest, und **im Eintragsblatt ist genau
// ein Element dehnbar** — der Belegsatz. Alles darüber hat seine natürliche Höhe, der
// Satz bekommt, was übrig bleibt, und das Blatt schneidet ab (`Sheet.clip`). Damit kann
// kein Satz mehr aus dem Fenster laufen, egal wie lang er ist.
Item {
    id: screen

    readonly property bool narrow: width < Theme.narrowWidth
    readonly property int margin: Theme.pageMargin(width)
    readonly property int pad: Theme.cardPadding(width)

    Rectangle { anchors.fill: parent; color: Theme.ground }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Kopf: woran arbeite ich ──────────────────────────────────────────────────
        // **Eine** Zeile, linksbündig, nicht zwei an den beiden Enden des Fensters
        // (review_round3.md C1: „zwischen Buchtitel links und Kapitelangabe rechts liegen
        // rund 700 px Kopfzeile"). Vorn steht, woran gearbeitet wird, dahinter blasser,
        // woraus es stammt — dieselbe Form wie die Überschrift des Fortschritts, und die
        // rechte Fensterkante begrenzt damit nichts mehr, was nicht begrenzt sein will.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.headerFor(screen.width)

            Text {
                objectName: "bookLine"
                anchors.left: parent.left
                anchors.leftMargin: screen.margin
                anchors.right: parent.right
                anchors.rightMargin: screen.margin
                anchors.verticalCenter: parent.verticalCenter
                text: "<font color=\"" + Theme.ink + "\">Kapitel " + Content.chapterNumber
                      + " · " + Content.chapterTitle + "</font>"
                      + "<font color=\"" + Theme.inkSoft + "\">  —  " + Content.bookTitle
                      + " · " + Content.bookAuthor + "</font>"
                textFormat: Text.StyledText
                font.family: Theme.fonts.book
                font.pixelSize: Theme.size.small
                elide: Text.ElideRight
            }
        }

        // ── Mitte: Liste und Eintrag, beide dehnbar in der Höhe ──────────────────────
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: screen.margin
            Layout.rightMargin: screen.margin
            spacing: Theme.space.m

            // ── Blockliste ───────────────────────────────────────────────────────────
            Sheet {
                id: listSheet
                Layout.preferredWidth: Theme.sidebarWidth(screen.width)
                Layout.fillHeight: true

                ColumnLayout {
                    anchors.fill: parent
                    spacing: 0

                    // Der Zähler trägt drei Angaben: Position, Blockgröße und „N zum
                    // Lernen" — der Stand **vor** der anstehenden Entscheidung
                    // (Prüfzeile 5.7, technik.md §13).
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Theme.headerHeight

                        Text {
                            id: blockLabel
                            anchors.left: parent.left
                            anchors.leftMargin: screen.narrow ? Theme.space.s : Theme.space.m
                            anchors.top: parent.top
                            anchors.topMargin: Theme.space.s + Theme.space.xs
                            text: "BLOCK " + Content.blockNumber
                            color: Theme.inkFaint
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.tag
                            font.weight: Theme.strong
                            font.letterSpacing: 0.8
                        }

                        Text {
                            anchors.left: parent.left
                            anchors.leftMargin: screen.narrow ? Theme.space.s : Theme.space.m
                            anchors.top: blockLabel.bottom
                            anchors.topMargin: Theme.space.xs
                            text: Content.position + " / " + Content.blockSize
                            color: Theme.ink
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.small
                            font.weight: Theme.strong
                        }

                        Text {
                            anchors.right: parent.right
                            anchors.rightMargin: screen.narrow ? Theme.space.s : Theme.space.m
                            anchors.top: blockLabel.bottom
                            anchors.topMargin: Theme.space.xs
                            text: Content.chosenCount + " zum Lernen"
                            color: Theme.chosen
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.small
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: Theme.borderWidth
                        color: Theme.hairline
                    }

                    // Eine echte ListView mit Bildlauf. Sie zeigt **alle** Einträge des
                    // Blocks, durchnummeriert ab 1 (Prüfzeile 4.1) — nicht so viele, wie
                    // gerade in die Panelhöhe passen.
                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        ListView {
                            id: blockList
                            anchors.fill: parent
                            anchors.topMargin: Theme.space.s
                            anchors.bottomMargin: Theme.space.s
                            anchors.rightMargin: Theme.space.s
                            clip: true
                            model: Content.blockEntries
                            currentIndex: Content.position - 1
                            // Der laufende Eintrag steht im Bild, auch wenn der Block
                            // länger ist als das Panel — und zwar immer an derselben
                            // Stelle, zwei Zeilen unter der Oberkante. Ein Vielfaches der
                            // Zeilenhöhe, damit oben keine halbe Zeile stehen bleibt: Ein
                            // angeschnittener Buchstabe unter der Trennlinie sieht aus wie
                            // ein Zeichenfehler, nicht wie „hier geht es weiter".
                            highlightRangeMode: ListView.StrictlyEnforceRange
                            preferredHighlightBegin: Theme.rowHeight * 2
                            preferredHighlightEnd: Theme.rowHeight * 2
                            boundsBehavior: Flickable.StopAtBounds

                            delegate: WordRow {
                                required property var modelData
                                required property int index
                                width: blockList.width
                                number: modelData[0]
                                pos: modelData[1]
                                word: modelData[2]
                                frequency: modelData[3]
                                current: index === blockList.currentIndex
                                compact: screen.narrow
                            }
                        }

                        ScrollTrack {
                            view: blockList
                            anchors.right: parent.right
                            anchors.rightMargin: Theme.space.xs
                            anchors.top: parent.top
                            anchors.bottom: parent.bottom
                            anchors.topMargin: Theme.space.s
                            anchors.bottomMargin: Theme.space.s
                        }
                    }
                }

                // Der Tastaturfokus liegt auf der Liste: Sie beantwortet ↑ und ↓. Er
                // liegt nicht auf einer der vier Tasten — eine hervorgehobene Antwort
                // wäre eine Vorauswahl, und die darf die Oberfläche nicht treffen
                // (review_round1.md B12).
                FocusRing { shown: true; inset: 0 }
            }

            // ── Eintrag ──────────────────────────────────────────────────────────────
            //
            // **Die Komposition des Blatts** (review_round3.md C1). Bis Runde 2 war hier
            // ein einziger Stapel, der oben bündig anfing und dessen letztes Element die
            // Resthöhe *einnehmen durfte*, ohne sie zu füllen: Bei 1280×800 stand der
            // ganze Eintrag im oberen Drittel und darunter ein leeres halbes Blatt
            // (gemessen 40 bis 51 %). Jetzt sind es **zwei Gruppen an zwei Kanten** —
            // oben Wortform, Übersetzung, Angaben und Marke, unten der Beleg. Der Abstand
            // dazwischen ist damit ein gesetzter Abstand zwischen zwei Gruppen und kein
            // übrig gebliebenes Ende; die Unterkante des Belegs liegt bei jedem der
            // dreihundert Einträge an derselben Stelle.
            //
            // Der Preis, offen genannt: Die Zeile „SO STEHT ES IM KAPITEL" wandert mit
            // der Satzlänge (bei einer Zeile Unterschied rund 25 px). Sie ist eine
            // 12-px-Versalzeile in `inkFaint` und kein Blickfang — die beiden Kanten, an
            // denen das Auge misst, sind das Kopfwort oben und der Blattfuß unten, und
            // die stehen beide fest.
            Sheet {
                id: entrySheet

                Layout.fillWidth: true
                Layout.fillHeight: true

                // Das **Zeilenmaß** des Blatts. Bei 1280 liefen vorher rund 90 Zeichen je
                // Zeile (C1), und deshalb las sich das kleine Fenster besser als das
                // große — bei einem Fließtext, den jemand dreihundertmal am Stück liest,
                // ist das der teuerste Fehler des Bildschirms. Das Maß begrenzt, es dehnt
                // nicht: Bei 900×600 wird es nie erreicht, dort ändert sich durch diese
                // Zeile nichts.
                //
                // 600 und nicht die vorgeschlagenen 640: **Am Bild nachgezählt** trägt
                // Literata bei 18 px rund 8,9 px je Zeichen, 640 px sind damit 71 Zeichen
                // und liegen über dem Zielband von 60 bis 70. 600 px sind 67.
                //
                // `column` ist dasselbe Maß plus der Einrückung des Belegs. Damit enden
                // Übersetzung, Angabenzeile und Belegsatz rechts auf **einer** Linie; der
                // Streifen rechts daneben ist Rand und nicht Rest.
                readonly property int measure: 600
                readonly property int column: measure + Theme.markerWidth + Theme.space.m

                // ── Gruppe oben: das Wort und was über es bekannt ist ────────────────
                ColumnLayout {
                    id: headGroup

                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.top: parent.top
                    anchors.margins: screen.pad
                    spacing: 0

                    // 1. Die Wortform — das größte Element des Bildschirms (Prüfzeile
                    //    5.1), in der Buchschrift, in **einer** Größe für jedes Fenster.
                    //    Sie hält sich als einzige nicht an das Zeilenmaß: Ein Wort wird
                    //    nicht gelesen, es wird gesehen.
                    Text {
                        Layout.fillWidth: true
                        text: Content.wordForm
                        color: Theme.ink
                        font.family: Theme.fonts.book
                        font.pixelSize: Theme.displayFor(screen.width)
                        font.weight: Theme.regular
                        // Der Zeilenkasten einer 60-px-Lesetype ist hoeher als das Wort
                        // darin. Enger gesetzt spart er Platz, **ohne** die Schriftgroesse
                        // anzutasten — die bleibt in jedem Fenster gleich.
                        lineHeight: 0.92
                        elide: Text.ElideRight
                    }

                    // 2. Die Übersetzung — **unmittelbar** darunter, in der Akzentfarbe,
                    //    ohne dass etwas dazwischen steht (Prüfzeile 5.2). Hier stand in
                    //    Runde 1 die Spiegelung, ein Abstandselement und der Roboter.
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: entrySheet.column
                        Layout.topMargin: Theme.space.s
                        // Das schmale geschützte Leerzeichen vor dem Trennpunkt (Kritik
                        // Runde 3, C9). Ohne es begann die umbrechende Kette mit
                        // „· Seelenhirte" — ein Trennzeichen am Zeilenanfang trennt
                        // nichts. Seit das Zeilenmaß gilt, bricht die Kette häufiger um,
                        // und aus der Kleinigkeit wäre der Normalfall geworden.
                        text: Content.translation.replace(/ · /g, " · ")
                        color: Theme.accent
                        font.family: Theme.fonts.book
                        font.pixelSize: Theme.size.title
                        wrapMode: Text.WordWrap
                    }

                    // 3. Wortart · Häufigkeit · Bedeutungsangabe — **eine** Zeile, ein
                    //    Trennzeichen, genau drei Angaben (Prüfzeile 5.3). Sie bricht um
                    //    statt zu kürzen: Regel 1, nichts fällt weg (B20).
                    Text {
                        Layout.fillWidth: true
                        Layout.maximumWidth: entrySheet.column
                        Layout.topMargin: Theme.space.s
                        text: Theme.posLabel(Content.pos) + "  ·  " + Content.frequency
                              + "× im Kapitel  ·  " + Content.senseLabel
                        color: Theme.inkSoft
                        font.family: Theme.fonts.ui
                        font.pixelSize: Theme.size.small
                        wrapMode: Text.WordWrap
                    }

                    // 4. Die Marke auf einer **eigenen** Zeile (Prüfzeile 5.8) — und nur,
                    //    wenn sie zutrifft.
                    Tag {
                        Layout.topMargin: Theme.space.m
                        Layout.maximumWidth: entrySheet.column
                        visible: Content.newMeaning
                        text: "neue Bedeutung eines bekannten Wortes"
                    }

                    // Der Mindestabstand zur unteren Gruppe gehört zur oberen: Wird das
                    // Blatt eng (langer Satz, kleines Fenster), schrumpft der Abstand bis
                    // hierher und nicht weiter. Der Belegsatz bekommt in jedem Fall
                    // dieselbe Höhe wie vor dieser Änderung — Prüfzeile 5.10 steht über
                    // der Komposition.
                    Item {
                        Layout.fillWidth: true
                        Layout.preferredHeight: screen.narrow ? Theme.space.s : Theme.space.l
                    }
                }

                // ── Gruppe unten: so steht es im Kapitel ─────────────────────────────
                // An die **Blattunterkante** verankert. Der Satz wächst nach oben in den
                // Abstand hinein; seine letzte Zeile steht immer gleich hoch.
                Item {
                    id: quoteGroup

                    // Was unterhalb der oberen Gruppe überhaupt frei ist. Deckel und
                    // nicht Vorgabe: Reicht es nicht, schneidet `Sheet.clip` sichtbar ab
                    // und `layout_check.py` meldet es — dieselbe letzte Instanz wie
                    // bisher (B1/B2).
                    readonly property int free: entrySheet.height - screen.pad * 2
                                                - headGroup.height
                    // `Math.ceil` und nicht die Zuweisung an ein `int`: Die Höhe einer
                    // umgebrochenen Textzeile ist gebrochen, das Abschneiden der
                    // Nachkommastelle kostete genau ein Pixel, und `layout_check.py`
                    // meldete es als abgeschnittenen Belegsatz. Ein Pixel ist im Bild
                    // nicht zu sehen — die Prüfung sieht es, und deshalb wird es behoben
                    // und nicht geduldet.
                    readonly property int wanted: Math.ceil(quoteCaption.height
                                                            + Theme.space.s
                                                            + quote.implicitHeight)

                    anchors.left: parent.left
                    anchors.leftMargin: screen.pad
                    anchors.right: parent.right
                    anchors.rightMargin: screen.pad
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: screen.pad
                    height: Math.min(wanted, free)
                    clip: true

                    Text {
                        id: quoteCaption
                        anchors.left: parent.left
                        anchors.top: parent.top
                        text: "SO STEHT ES IM KAPITEL"
                        color: Theme.inkFaint
                        font.family: Theme.fonts.ui
                        font.pixelSize: Theme.size.tag
                        font.weight: Theme.strong
                        font.letterSpacing: 0.8
                    }

                    // 5. Der Belegsatz — er bricht um und wird nie gekürzt
                    //    (Prüfzeilen 5.5 und 5.10), jetzt auf dem Zeilenmaß des Blatts.
                    Rectangle {
                        id: quoteRule
                        anchors.left: parent.left
                        anchors.top: quoteCaption.bottom
                        anchors.topMargin: Theme.space.s
                        width: Theme.markerWidth
                        height: Math.min(parent.height - quoteCaption.height - Theme.space.s,
                                         quote.implicitHeight)
                        color: Theme.hairline
                    }

                    Text {
                        id: quote
                        anchors.left: quoteRule.right
                        anchors.leftMargin: Theme.space.m
                        anchors.top: quoteRule.top
                        width: Math.min(parent.width - Theme.markerWidth - Theme.space.m,
                                        entrySheet.measure)
                        // Die Wortform ist im Satz hervorgehoben, und zwar in
                        // **derselben Beugungsform** wie in der Kopfzeile
                        // (Prüfzeile 5.6). Das ist die einzige Stelle neben der
                        // Übersetzung, an der der Akzent etwas sagt.
                        text: Content.sentenceBefore
                              + "<b><font color=\"" + Theme.accent + "\">"
                              + Content.sentenceWord + "</font></b>"
                              + Content.sentenceAfter
                        textFormat: Text.StyledText
                        color: Theme.ink
                        font.family: Theme.fonts.book
                        font.pixelSize: Theme.size.reading
                        lineHeight: 1.4
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }

        // ── Fuß: die drei Entscheidungen, und abgesetzt das Beenden ──────────────────
        // 56 px statt 96 (review_round1.md B14: „16 % der Fensterhöhe bei 900×600 — genau
        // der Platz, der dem Belegsatz dort fehlt"). „beenden" steht rechts abgesetzt und
        // in der schwächeren Schriftfarbe: Die eine Taste, die den Durchgang abbricht,
        // steht nicht in der Reihe der Tasten, die man dreihundertmal drückt.
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.footerFor(screen.width)

            Row {
                anchors.left: parent.left
                anchors.leftMargin: screen.margin
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space.l

                Repeater {
                    model: Content.actions
                    delegate: Row {
                        required property var modelData
                        spacing: Theme.space.s

                        KeyCap {
                            key: modelData[0]
                            tone: Theme.ink
                            anchors.verticalCenter: parent.verticalCenter
                        }

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            text: modelData[1]
                            color: Theme.ink
                            font.family: Theme.fonts.ui
                            font.pixelSize: Theme.size.small
                        }
                    }
                }
            }

            Row {
                anchors.right: parent.right
                anchors.rightMargin: screen.margin
                anchors.verticalCenter: parent.verticalCenter
                spacing: Theme.space.s

                KeyCap {
                    key: Content.quitAction[0]
                    tone: Theme.inkFaint
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: Content.quitAction[1]
                    color: Theme.inkFaint
                    font.family: Theme.fonts.ui
                    font.pixelSize: Theme.size.small
                }
            }
        }
    }
}
