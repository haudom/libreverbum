pragma Singleton
import QtQuick

// Gestaltungssystem der Richtung „Lesetisch" — die einzige Quelle für Farbe, Schrift und
// Maß. Keine Zahl in einem Bildschirm steht für sich: Sie ist ein Token von hier oder ein
// Vielfaches von `unit`. Warum diese Richtung und keine andere: technik.md §14, E11.
//
// Haltung: Das Programm wird vor dem Lesen benutzt, regelmäßig, über Jahre. Es soll
// aussehen wie eine gut gesetzte Seite auf einem Tisch — nicht wie eine Oberfläche, die
// sich vorstellt. Nichts glänzt, nichts spiegelt, nichts schwebt; Rang entsteht aus
// Flächenhelligkeit, Weißraum, Schriftgröße und **einer** Akzentfarbe.
//
// Zwei Stimmen, eine Regel, die man in einem Satz sagen kann (siehe `fonts`):
// **Serif ist Sprachmaterial, Sans ist Programmstimme.**
//
// **`B…` und `C…` in den Kommentaren sind Herkunftsangaben, keine Verweise** — wie
// `bauplan.md T13` (CLAUDE.md, „Die Dokumente und ihre Zuständigkeit"). Sie nennen den
// Befund der Durchsicht, aus dem eine Festlegung stammt, und stehen in
// `tools/design_mockup/review_round1.md` (B1 bis B24) beziehungsweise `review_round3.md`
// (C1 bis C11). Was **gilt**, steht dagegen hier und in technik.md §14 — die beiden
// Dateien fallen mit dem Mockup weg, diese Datei bleibt.
//
// Anzusehen ist das System nicht als Zahlenliste, sondern gerendert:
//     .venv/Scripts/python.exe tools/design_mockup/render_all.py
// rendert vier Bildschirme in zwei Themen und zwei Größen gegen **diese** Datei und misst
// jedes Bild (technik.md §14, „Der Mockup rendert gegen den Bestand").
QtObject {
    id: theme

    readonly property bool dark: typeof appDark !== "undefined" ? appDark : false

    // ── Ebenen ───────────────────────────────────────────────────────────────────────
    // Drei Ebenen, alle **deckend**. Keine Verläufe, keine Durchsichtigkeit, keine
    // Schlagschatten: Eine Fläche sieht überall gleich aus, unabhängig davon, worüber sie
    // gerade liegt. Zugesichert und in `token_check.py` gerechnet, in `contrast_check.py` am
    // gerenderten Bild nachgewiesen: L1 zu L0 ≥ 1,25:1, damit eine Fläche auch ohne
    // Schatten eine Fläche ist. Gemessen 1,30:1 in **beiden** Themen — hell und dunkel
    // sind ein Entwurf, nicht zwei (review_round1.md B16).
    //
    // **Und dieselbe Stimmung, nicht nur dasselbe Verhältnis** (review_round3.md C5). Das
    // dunkle Thema war bis Runde 2 in den Farben einer Entwicklungsumgebung gesetzt:
    // Blauschwarz, Blaugrau, Stahlgrau. Strukturell war das ein Entwurf mit dem hellen, in
    // der Stimmung waren es zwei — „warmes Papier auf einem beigen Tisch" gegen „kühles
    // Blaugrau", und wer abends vor dem Lesen arbeitet, bekam das charakterlose der
    // beiden. Vier Token sind deshalb ins Warme gezogen (`ground`, `surface`, `hairline`
    // und weiter unten `robotShell`); die Akzentfarben bleiben unangetastet, die sind
    // kontrastrichtig gewählt.
    //
    // Nachgerechnet und in `contrast_check.py` am Bild bestätigt: L1 zu L0 ist **1,300 statt
    // 1,304**, Haarlinie und Gehäuse liegen auf 0,01 genau auf ihren alten Verhältnissen,
    // und jede Schriftfarbe steht auf jeder Ebene etwas besser da als vorher. Der Farbton
    // hat sich geändert, die Ordnung nicht.
    readonly property color ground: dark ? "#0E0C08" : "#E3DFD6"   // L0 — der Tisch
    readonly property color surface: dark ? "#2B261C" : "#FDFCFA"  // L1 — das Blatt
    readonly property color marked: dark ? "#372B19" : "#F6E9D2"   // L2 — die laufende Zeile
    readonly property color hairline: dark ? "#4A4339" : "#CFCABF" // Trennlinie, 1 px

    // ── Schriftfarben: drei Ränge, kein `opacity` ────────────────────────────────────
    // REGEL (review_round1.md B3): `opacity` kommt nie auf Text. Der alte Entwurf hatte
    // zwei Textfarben und drei nötige Ränge — also griff jeder Bildschirm zu `opacity`
    // und fiel dabei unbemerkt unter 4,5:1 (gemessen bis hinunter zu 2,41:1). Wer einen
    // schwächeren Rang braucht, nimmt das dritte Token. Alle drei sind auf **allen drei
    // Ebenen** über 4,5:1, nicht nur auf der hellsten.
    readonly property color ink: dark ? "#F2F4F7" : "#1A1F26"      // Kopfwort, Buchtext, Zeilen
    readonly property color inkSoft: dark ? "#B7C0CB" : "#4A545F"  // Beschriftungen, Metazeile
    readonly property color inkFaint: dark ? "#94A0AD" : "#56606A" // Nummern, Spaltenköpfe, Ruhendes

    // ── Zustandsfarben: je Farbe genau eine Aufgabe ──────────────────────────────────
    // REGEL (review_round1.md B8): Bernstein trug im alten Entwurf sechs Bedeutungen
    // gleichzeitig und für „Achtung" blieb keine übrig. Hier bedeutet `accent` genau
    // eines: **hier bist du gerade / das ist die Antwort**. Laufende Zeile, laufende
    // Etappe, Fokusring, die Wortform im Belegsatz, die Übersetzung. Sonst nichts.
    readonly property color accent: dark ? "#F0A852" : "#8F4906"       // als Schrift und Linie
    readonly property color accentFill: dark ? "#E08C2E" : "#A65509"   // als Fläche
    readonly property color inkOnAccent: dark ? "#1A1206" : "#FFFFFF"  // Schrift auf accentFill
    readonly property color chosen: dark ? "#78C994" : "#1F6B3C"       // „zum Lernen gewählt"
    readonly property color warn: dark ? "#FF9184" : "#A32019"         // Fehlschlag im Wortlaut
    readonly property color warnFill: dark ? "#3A211E" : "#F7E3E0"     // Fläche des Meldungsfelds

    // ── Der Roboter ──────────────────────────────────────────────────────────────────
    // Die Figur steht auf genau zwei Bildschirmen (Fortschritt, Abschluss) und braucht
    // zwei Flächen, die keine andere Aufgabe im System haben: ihr Gehäuse und ihr Visier.
    // Sie stehen hier und nicht im Bauteil, weil die gemeinsame Prüfzeile verlangt, dass
    // **jede** Farbe des Screenshots aus den Token stammt — eine Zeichnung, die sich ihre
    // Töne selbst mischt, ist genau die Ausnahme, die diese Zeile verhindern soll.
    //
    // Das Gehäuse liegt in beiden Themen eine Stufe **neben** dem Blatt, nicht darüber:
    // hell etwas dunkler, dunkel etwas heller. Damit ist die Figur eine Fläche und kein
    // Loch. Das Visier ist in beiden Themen dunkel — es ist ein Fenster, hinter dem die
    // Augen leuchten, und `accentFill` ist dort das einzige Licht.
    //
    // Das Gehäuse ist das vierte gewärmte Token (C5): Hell war die Figur eine
    // Elfenbeinfigur mit Gesicht, dunkel ein Stahlklotz. Jetzt ist sie in beiden Themen
    // aus demselben Material. Das Visier bleibt, wie es war — bei dieser Dunkelheit ist
    // kein Farbton mehr zu sehen, und es soll auch keiner zu sehen sein: Es ist ein
    // Fenster, kein Material.
    readonly property color robotShell: dark ? "#474034" : "#ECE7DE"
    readonly property color robotVisor: dark ? "#0E131A" : "#1A1F26"

    // ── Schrift ──────────────────────────────────────────────────────────────────────
    // **Serif ist Sprachmaterial, Sans ist Programmstimme.** Literata trägt alles, was
    // Sprache *ist* — die englische Wortform, den Belegsatz aus dem Buch, die Wörter der
    // Liste, die deutsche Übersetzung, Buch- und Kapiteltitel. Inter trägt alles, was das
    // Programm *sagt* — Beschriftungen, Zähler, Spaltenköpfe, Schaltflächen, Meldungen.
    // Damit ist die Schriftmischung eine Regel und keine Laune (review_round1.md B15: im
    // alten Entwurf standen „7 von 25" und der Buchtitel ohne Grund in verschiedenen
    // Familien).
    //
    // Literata ist eine Lesetype für Bildschirme (Google/TypeTogether, SIL OFL 1.1),
    // Inter eine Oberflächentype mit Tabellenziffern (rsms, SIL OFL 1.1). Die Dateien und
    // beide Lizenztexte liegen in `gui/fonts/`, die Namensnennung in `NOTICE` (Regel 15).
    // Cabin und Quicksand aus Runde 1 sind ersetzt: Quicksand
    // ist geometrisch-rund und hat keine Kursive, Cabin unterscheidet sich bei 12–15 px
    // von Quicksand nicht lesbar — die Mischung sagte deshalb nichts.
    readonly property QtObject fonts: QtObject {
        readonly property string book: "Literata"   // Sprachmaterial
        readonly property string ui: "Inter"        // Programmstimme
    }

    // Sechs Stufen, jede mit einer benannten Aufgabe. Wer eine siebte braucht, hat eine
    // Aufgabe übersehen — nicht eine Größe.
    readonly property QtObject size: QtObject {
        readonly property int tag: 12      // Versalienmarken, Spaltenköpfe
        readonly property int small: 14    // Zähler, Häufigkeit, Metazeile, Schaltflächen
        readonly property int normal: 16   // Listenzeilen, Formulartext, Etappen
        readonly property int reading: 18  // Belegsatz — der einzige Fließtext
        readonly property int title: 24    // Bildschirmüberschrift, Übersetzung
        readonly property int display: 60  // nur die Wortform, eine Größe für jedes Fenster
    }

    // Zwei Gewichte. Betonung durch Gewicht und Farbe, nie durch Deckung.
    readonly property int regular: Font.Normal
    readonly property int strong: Font.DemiBold

    // ── Maß ──────────────────────────────────────────────────────────────────────────
    // Rastereinheit 8. `xs` ist die halbe Einheit und ausdrücklich die einzige Ausnahme —
    // sie richtet Text gegen eine 1-px-Linie aus, sonst nichts.
    readonly property int unit: 8
    readonly property QtObject space: QtObject {
        readonly property int xs: 4
        readonly property int s: 8
        readonly property int m: 16
        readonly property int l: 24
        readonly property int xl: 32
        readonly property int xxl: 48
    }

    // Feste Höhen. REGEL (review_round1.md B1/B2): Auf jedem Bildschirm bekommt **das
    // dehnbare Element** die Resthöhe und alles andere eine feste Höhe — nie umgekehrt.
    // Diese Zahlen sind das „alles andere".
    readonly property int headerHeight: 56
    readonly property int footerHeight: 56
    // Beim schmalen Fenster geben Kopf und Fuss je eine Rastereinheit ab. Das ist
    // dasselbe Zugestaendnis wie der kleinere Seitenrand: Es schrumpft der Rand, nie der
    // Satz (review_round1.md B21).
    function headerFor(w) { return w < narrowWidth ? 40 : 56 }
    function footerFor(w) { return w < narrowWidth ? 40 : 56 }
    readonly property int rowHeight: 32       // Wortliste
    readonly property int tableRowHeight: 36  // Kapitelliste (zweizeilig bei Grund)
    readonly property int controlHeight: 32   // Schaltfläche, Textzeile
    // Etappenzeile des Fortschritts. Sie war 48 und ist 40 (schmal 36): Sechs Etappen mal
    // acht Pixel sind genau der Platz, den der Roboter über der Liste braucht, damit er
    // dort **groß** stehen kann (review_round3.md C2). Eine 16-px-Zeile mit einem
    // 24-px-Zeichen hat in 40 px zwölf Pixel Luft nach oben und unten — das ist die
    // Zierde, die hier abgegeben wird, nicht die Lesbarkeit.
    function stageHeight(w) { return w < narrowWidth ? 36 : 40 }

    readonly property int radius: 8       // Flächen
    readonly property int radiusTag: 4    // Marken
    readonly property int radiusKey: 6    // Tastenkappe
    readonly property int borderWidth: 1
    readonly property int focusWidth: 2   // Fokusring
    readonly property int markerWidth: 3  // Akzentbalken der laufenden Zeile

    // ── Fenstergrößen ────────────────────────────────────────────────────────────────
    // Unter dieser Breite schrumpft der **Rand**, nie der Satz (review_round1.md B21).
    // Schriftgrößen sind von der Fenstergröße unabhängig — alle sechs Stufen gelten
    // überall.
    readonly property int narrowWidth: 1000
    function pageMargin(w) { return w < narrowWidth ? space.m : space.l }
    function cardPadding(w) { return w < narrowWidth ? space.m : space.xl }
    // Die Seitenliste bleibt beim schmalen Fenster bei 248 px. Sie war kurzzeitig 264,
    // damit die längste Wortform in ihre Spalte passt — und prompt lief der Belegsatz
    // rechts um 22 px über. Die 16 px holt sich die Spalte deshalb **innen**, aus den
    // Rändern der Zeile (`WordRow.compact`), nicht aus dem Nachbarn.
    function sidebarWidth(w) { return w < narrowWidth ? 248 : 288 }
    // Die eine Ausnahme von „alle sechs Stufen gelten ueberall": Beim kleinsten Fenster
    // gibt das Kopfwort 12 px ab. Begruendung — Pruefzeile 5.10 stellt **den Belegsatz**
    // unter Schutz, nicht die Zierde; Pruefzeile 5.1 verlangt vom Kopfwort nur, das
    // groesste Element zu sein, und mit 48 px ist es das dreifache der naechsten Stufe.
    // Genau umgekehrt lag der alte Entwurf: Dort schrumpfte der Satz (18 -> 16) und das
    // Kopfwort gleich mit (review_round1.md B21).
    function displayFor(w) { return w < narrowWidth ? 48 : 60 }

    // Deutsche Anzeige der Wortart. `token.pos_` bleibt englisch (Sprachregel: Namen aus
    // Fremdquellen werden nicht übersetzt), die **Anzeige** ist es nicht.
    function posLabel(pos) {
        if (pos === "VERB") return "Verb"
        if (pos === "NOUN") return "Substantiv"
        if (pos === "PROPN") return "Eigenname"
        if (pos === "ADJ") return "Adjektiv"
        if (pos === "ADV") return "Adverb"
        return pos
    }
}
