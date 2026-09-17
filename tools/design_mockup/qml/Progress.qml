import QtQuick
import QtQuick.Layouts
import Mock

// Bildschirm 3 — Fortschritt.
//
// Dieser Bildschirm ist Wartezeit. Er ist der einzige Ort des Programms, an dem nichts zu
// entscheiden ist, und deshalb der einzige, an dem Charakter nicht im Weg steht: Hier
// steht der Roboter.
//
// Gerendert wird der **Anfangszustand** — eine Etappe läuft, fünf sind offen. Genau den
// sieht der Nutzer zuerst, und genau der war in Runde 1 nie gerendert: Das alte Mockup
// zeigte fünf von sechs Etappen als erledigt (review_round1.md B24) und fiel im offenen Zustand mit
// 2,41:1 durch. `--fall lauf` zeigt den Lauf mit Zählern, `--fall fehler` den Fehlschlag.
//
// **Die Komposition** (review_round3.md C2). Bis Runde 2 stand die Überschrift oben links,
// darunter ein Loch, dann eine breite halbhohe Karte, darunter ein Loch, dann unten rechts
// die einzige Schaltfläche — drei Ecken ohne Zusammenhang, und der Roboter in die rechte
// Kartenhälfte geschoben, wo er nichts bedeutete. Der verworfene Vorentwurf „Glashaus" war
// hier handwerklich schlechter und **kompositorisch besser**, und zwar aus einem Grund:
// Er war **eine Spalte**.
//
// Also eine Spalte, 640 px breit, mittig, von oben nach unten: der Roboter als Bekrönung,
// die Überschrift, die Karte mit den Etappen, die Schaltfläche. Was man sieht, während man
// wartet, steht auf einer Achse und hat eine Reihenfolge.
//
// Und der Roboter darf hier **groß** sein. Das ist der einzige Bildschirm des Programms,
// auf dem nichts zu entscheiden ist; er steht Minuten, und die Figur ist das Einzige, was
// es hier zu sehen gibt. Sie ist die Wärme, die „Glashaus" aus seinem Material bezog —
// nur kostet sie hier keine einzige Glasscheibe.
//
// **Warum die Karte eine Höhe hat und nicht das Fenster füllt.** Auf diesem Bildschirm ist
// nichts dehnbar: Die Etappen sind sechs, der Satz ist so lang, wie er ist. Eine Karte,
// die trotzdem die ganze Fensterhöhe nimmt, ist zu drei Vierteln leer und sieht nach
// vergessenem Inhalt aus. Sie bekommt deshalb die Höhe ihres Inhalts — **gedeckelt auf
// die verfügbare Höhe**, und `Sheet` schneidet ab. Das ist ausdrücklich nicht der Fall
// B2 aus Runde 1: Dort war der Deckel da, aber der Inhalt hing mit `anchors.fill` darin
// und lief lautlos darüber hinaus. Hier ist der Deckel die letzte Instanz, das Abschneiden
// sichtbar, und `layout_check.py` meldet beides.
Item {
    id: screen

    readonly property bool narrow: width < Theme.narrowWidth
    readonly property int margin: Theme.pageMargin(width)
    // Die Karte hat hier ein eigenes, engeres Polster als die breiten Blätter der anderen
    // Bildschirme: Sie ist nur 640 px breit, und 32 px Rand sähen darin nach Formular aus.
    readonly property int pad: narrow ? Theme.space.m : Theme.space.l
    readonly property bool failed: Content.variant === "fehler"

    // Das Maß der Spalte. Dasselbe wie das Zeilenmaß des Triage-Belegs plus seiner
    // Einrückung — die beiden Bildschirme, auf denen etwas mittig steht, stehen damit
    // auf demselben Maß.
    readonly property int columnWidth: Math.min(width - margin * 2, 640)

    // Der Abstand der Spalte zur unteren Fensterkante.
    readonly property int bottomBand: narrow ? Theme.space.m : Theme.space.l

    // Wo die Spalte steht. Zwei Fälle, eine Zeile:
    //
    // - **Es läuft.** Die Spalte sitzt unten auf, und die ganze Resthöhe steht über ihr —
    //   dort steht der Roboter darin. Die Luft sammelt sich an **einer** Stelle.
    // - **Es ist fehlgeschlagen.** Dann ist keine Figur da, die die Resthöhe tragen
    //   könnte, und die Spalte stünde unten am Rand, mit 440 px Nichts darüber. Sie rückt
    //   deshalb in die Mitte.
    //
    // Ausgerechnet und nicht zwei gleichen Federn überlassen: Zwei `fillHeight`-Felder
    // mit gleicher Wunschhöhe teilen sich die Resthöhe **nicht** gleichmäßig auf — das
    // obere bekam sie ganz und die Karte klebte unten am Fuß. Am Bild gesehen.
    readonly property int stackTop: failed
        ? Math.max(Theme.space.m, Math.round((height - stack.height) / 2))
        : height - bottomBand - stack.height

    // Was die Karte höchstens hoch sein darf: was Überschrift, Schaltfläche, unterer Rand
    // und das Mindestfeld für die Figur übrig lassen. Der Deckel ist die letzte Instanz
    // gegen den stillen Überlauf und hängt deshalb an den **gemessenen** Höhen der
    // Nachbarn, nicht an einer zweiten Rechnung derselben Zahlen.
    readonly property int sheetLimit: height - bottomBand - Theme.space.m
                                      - headline.height - headline.Layout.bottomMargin
                                      - cancel.height - cancel.Layout.topMargin

    Rectangle { anchors.fill: parent; color: Theme.ground }

    // ── Der Roboter als Bekrönung ───────────────────────────────────────────────────
    // Er hängt an der **Oberkante der Spalte** und steht damit unmittelbar über der
    // Überschrift. Seine Größe ist gedeckelt, nicht gesetzt: Beim kleinen Fenster bleibt
    // über der Spalte weniger übrig, und dann wird die Figur kleiner, statt die Karte zu
    // verdrängen. Über ihr bleibt immer eine Rastereinheit Luft stehen — ohne den Abzug
    // wuchs sie bis an die Fensterkante und die Lampe auf ihrer Antenne saß auf dem Rand.
    Robot {
        id: robot

        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: stack.top
        anchors.bottomMargin: Theme.space.m
        height: Math.min(screen.stackTop - (screen.narrow ? Theme.space.m : Theme.space.xxl),
                         screen.narrow ? 184 : 288)
        width: height * 0.78
        visible: !screen.failed && height > 96
        working: true
    }

    // ── Die Spalte ──────────────────────────────────────────────────────────────────
    // Überschrift, Karte und Schaltfläche sind **ein** Gegenstand, nicht drei Ecken. Die
    // Schaltfläche steht damit auch im Fehlerfall dort, wo sie im Lauf steht: unter der
    // Karte, auf der Achse.
    ColumnLayout {
        id: stack

        x: (screen.width - width) / 2
        y: screen.stackTop
        width: screen.columnWidth
        height: implicitHeight
        spacing: 0

        // Die Kapitelnummer steht in der Überschrift (review_round1.md B22: der alte
        // Entwurf nannte sie nicht). Deutscher Satz in der Programmschrift, der englische
        // Kapiteltitel in der Buchschrift — die Trennung ist hier in einer Zeile zu sehen.
        Text {
            id: headline
            objectName: "bookLine"
            Layout.alignment: Qt.AlignHCenter
            Layout.maximumWidth: stack.width
            Layout.bottomMargin: screen.narrow ? Theme.space.m : Theme.space.l
            horizontalAlignment: Text.AlignHCenter
            text: "<font face=\"" + Theme.fonts.ui + "\"><b>Kapitel "
                  + Content.chapterNumber + " wird vorbereitet</b></font>"
                  + "<font face=\"" + Theme.fonts.book + "\" color=\"" + Theme.inkSoft
                  + "\"> — " + Content.chapterTitle + "</font>"
            textFormat: Text.StyledText
            color: Theme.ink
            font.pixelSize: Theme.size.title
            elide: Text.ElideRight
        }

        // ── Die Karte: die Etappen ──────────────────────────────────────────────────
        Sheet {
            id: sheet

            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(screen.sheetLimit,
                                             body.implicitHeight + screen.pad * 2)

            ColumnLayout {
                id: body

                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: screen.pad
                spacing: 0

                // Der Fehlschlag **ersetzt** die Liste und steht im Wortlaut da
                // (Prüfzeile 3.7, Regel 13). Der Bildschirm bleibt nicht auf einer
                // Etappe stehen und tut so, als liefe er weiter.
                MessageBox {
                    Layout.fillWidth: true
                    visible: screen.failed
                    text: "Das Kapitel ließ sich nicht vorbereiten:\n" + Content.stageError
                }

                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.space.m
                    visible: screen.failed
                    text: "Es wurde nichts ins Profil geschrieben. Das Kapitel kann nach "
                          + "dem Beheben der Ursache erneut vorbereitet werden."
                    color: Theme.inkSoft
                    wrapMode: Text.WordWrap
                    font.family: Theme.fonts.ui
                    font.pixelSize: Theme.size.small
                    lineHeight: 1.35
                }

                Repeater {
                    model: screen.failed ? [] : Content.stages
                    delegate: StageRow {
                        required property var modelData
                        Layout.fillWidth: true
                        label: modelData[0]
                        phase: modelData[1]
                        counter: modelData[2] === ""
                                 ? ""
                                 : modelData[2] + (modelData[3] === "" ? "" : " " + modelData[3])
                        // Etwas mehr als die Hälfte der Karte: Der längste Etappenname
                        // („Kapitelwortschatz ermitteln") endet davor, und der längste
                        // Zähler („9 von 13 Kapiteln mit Text") passt dahinter.
                        counterColumn: Math.round(body.width * 0.54)
                        windowWidth: screen.width
                    }
                }

                // Der eine Satz, der die Wartezeit trägt. Er steht da, weil der Nutzer
                // sonst aus sechs Etappen selbst schließen müsste, ob Minuten normal
                // sind — und weil ein Wartebildschirm ohne Auskunft die häufigste
                // Ursache für einen Abbruch ist, der keiner sein müsste.
                Text {
                    Layout.fillWidth: true
                    Layout.topMargin: Theme.space.m
                    visible: !screen.failed
                    text: "Das dauert beim ersten Kapitel eines Buchs ein paar Minuten. Danach "
                          + "ist das Buch analysiert, und jedes weitere Kapitel geht schnell."
                    color: Theme.inkSoft
                    wrapMode: Text.WordWrap
                    font.family: Theme.fonts.ui
                    font.pixelSize: Theme.size.small
                    lineHeight: 1.35
                }
            }
        }

        // „Abbrechen" muss während des spaCy-Laufs bedienbar sein (Prüfzeile 3.6) und ist
        // deshalb nie ausgegraut.
        // Nach dem Fehlschlag heißt die Schaltfläche nicht mehr „Abbrechen": Es läuft
        // nichts mehr, was man abbrechen könnte. Sie sagt dann, wohin sie führt. Eine
        // Beschriftung, die den Zustand des Programms nicht kennt, ist die billigste Art
        // von Unwahrheit.
        //
        // Sie steht **auf der Achse** unter der Karte und nicht in der rechten unteren
        // Ecke: Sie ist das letzte Glied der Spalte, nicht der Rest einer Werkzeugleiste.
        // In der Ecke war sie die dritte der „drei Ecken ohne Zusammenhang" (C2).
        //
        // **Kein Fokusring** (review_round3.md C4). Er war hier ein 2 px starkes Rechteck
        // in `accent` um eine ohnehin umrandete Schaltfläche und damit das größte
        // Akzentgebilde des Bildes: Der Akzent zeigte auf *Abbrechen* statt auf *was
        // gerade läuft*. Auf einem Wartebildschirm mit genau einem Bedienelement sagt der
        // Ring nichts, was die Tastenkappe „Esc" nicht schon sagt. Das stärkste
        // Akzentgebilde ist jetzt die laufende Etappe — die einzige Bedeutung, die
        // `accent` haben darf.
        ActionButton {
            id: cancel
            Layout.alignment: Qt.AlignHCenter
            Layout.topMargin: screen.narrow ? Theme.space.m : Theme.space.l
            label: screen.failed ? "Zurück zur Kapitelwahl" : "Abbrechen"
            shortcut: "Esc"
        }
    }
}
