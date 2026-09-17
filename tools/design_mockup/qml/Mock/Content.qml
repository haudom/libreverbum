pragma Singleton
import QtQuick

// Echte Inhalte — erzeugt von `build_content.py`, Herkunft jeder Zeichenkette in dessen Kopf.
// Nicht von Hand ändern.
QtObject {
    readonly property string bookTitle: "The Adventures of Sherlock Holmes"
    readonly property string bookAuthor: "Arthur Conan Doyle"
    readonly property string chapterTitle: "I. A SCANDAL IN BOHEMIA"
    readonly property int chapterNumber: 2

    // Welcher Fall gerendert wird. Gesetzt von `shot.py --fall`; ohne Angabe der erste.
    readonly property string variant: typeof appCase !== "undefined" && appCase !== ""
                                      ? appCase : "lang"

    // ── Triage ───────────────────────────────────────────────────────────────────────
    readonly property bool longSentence: variant !== "kette"
    readonly property int blockNumber: longSentence ? 2 : 1
    readonly property int blockSize: 25
    readonly property int position: 8
    readonly property int chosenCount: 3

    readonly property string wordForm: longSentence ? "Bohemian" : "clergyman"
    readonly property string lemma: longSentence ? "bohemian" : "clergyman"
    readonly property string pos: longSentence ? "ADJ" : "NOUN"
    readonly property int frequency: longSentence ? 3 : 5

    // Von Hand: welche der Kandidatenbedeutungen im Satz gemeint ist. Das entscheidet
    // sonst `translation.choose_sense`; ein Modellserver lief für diese Vorlage nicht.
    readonly property string translation: longSentence
        ? "unkonventionell"
        : "Kleriker · Geistlicher · Pastor · Pfarrer · Seelenhirt · Seelenhirte"
    readonly property string senseLabel: longSentence
        ? "unconventional"
        : "ordained (male) Christian minister, male member of the clergy"

    // Von Hand: die Marke kommt aus dem Profil, nicht aus dem Kapitel. Gezeigt wird sie am
    // Fall B, damit Prüfzeile 5.8 an einem Bild nachweisbar ist.
    readonly property bool newMeaning: !longSentence

    readonly property string sentenceBefore: longSentence ? "My own complete happiness, and the home-centred interests which rise up around the man who first finds himself master of his own establishment, were sufficient to absorb all my attention, while Holmes, who loathed every form of society with his whole " : "There was not a soul there save the two whom I had followed and a surpliced "
    readonly property string sentenceWord: longSentence ? "Bohemian" : "clergyman"
    readonly property string sentenceAfter: longSentence ? " soul, remained in our lodgings in Baker Street, buried among his old books, and alternating from week to week between cocaine and ambition, the drowsiness of the drug, and the fierce energy of his own keen nature." : ", who seemed to be expostulating with them."
    readonly property int sentenceLength: longSentence ? 473 : 128

    readonly property string uncertainLabel: "kein Wörterbucheintrag — unsicher"
    readonly property string noSenseLabel: "Hauptbedeutung, ohne nähere Angabe"

    // [Nummer im Block, Wortart, Wortform, Häufigkeit]
    readonly property var blockTwo: [
        [1, "ADV", "Precisely", 4],
        [2, "NOUN", "rocket", 4],
        [3, "VERB", "shouted", 4],
        [4, "NOUN", "sitting", 4],
        [5, "NOUN", "wheels", 4],
        [6, "NOUN", "altar", 3],
        [7, "NOUN", "bedroom", 3],
        [8, "ADJ", "Bohemian", 3],
        [9, "ADJ", "broad", 3],
        [10, "NOUN", "brougham", 3],
        [11, "NOUN", "carriage", 3],
        [12, "NOUN", "cigars", 3],
        [13, "NOUN", "coachman", 3],
        [14, "NOUN", "companion", 3],
        [15, "VERB", "compromise", 3],
        [16, "VERB", "consult", 3],
        [17, "NOUN", "couch", 3],
        [18, "VERB", "deduce", 3],
        [19, "ADJ", "delicate", 3],
        [20, "NOUN", "emotion", 3],
        [21, "NOUN", "guardsmen", 3],
        [22, "NOUN", "habit", 3],
        [23, "ADV", "hardly", 3],
        [24, "NOUN", "hat", 3],
        [25, "NOUN", "honour", 3]
    ]
    readonly property var blockOne: [
        [1, "NOUN", "photograph", 21],
        [2, "VERB", "rushing", 10],
        [3, "NOUN", "gentleman", 9],
        [4, "VERB", "remarked", 8],
        [5, "VERB", "observing", 7],
        [6, "NOUN", "client", 6],
        [7, "NOUN", "cab", 5],
        [8, "NOUN", "clergyman", 5],
        [9, "NOUN", "mask", 5],
        [10, "VERB", "pacing", 5],
        [11, "NOUN", "visitor", 5],
        [12, "NOUN", "alarm", 4],
        [13, "NOUN", "armchair", 4],
        [14, "NOUN", "chamber", 4],
        [15, "VERB", "employing", 4],
        [16, "VERB", "glancing", 4],
        [17, "NOUN", "glimpses", 4],
        [18, "VERB", "hurried", 4],
        [19, "NOUN", "importance", 4],
        [20, "NOUN", "instant", 4],
        [21, "NOUN", "landau", 4],
        [22, "VERB", "lounging", 4],
        [23, "NOUN", "mysteries", 4],
        [24, "NOUN", "object", 4],
        [25, "NOUN", "pockets", 4]
    ]
    readonly property var blockEntries: longSentence ? blockTwo : blockOne

    readonly property var actions: [
        ["K", "kenne ich"], ["L", "will ich lernen"], ["S", "überspringen"]
    ]
    readonly property var quitAction: ["Q", "beenden"]

    // ── Fortschritt ──────────────────────────────────────────────────────────────────
    // Sechs Etappen nach Wireframe 3. Die deutschen Sätze folgen `cli/main.py`; zwei der
    // sechs haben heute keine Entsprechung in `pipeline.ChapterStage` — siehe
    // entscheidungen.md, „Was ich nicht gelöst habe".
    // [Satz, Zustand (0 offen, 1 läuft, 2 fertig), Zähler, Nennerbeschriftung]
    // Anfangszustand: eine Etappe läuft, fünf sind offen. Kein Zähler steht da, weil
    // keiner etwas sagt (Prüfzeile 3.3).
    readonly property var stagesStart: [
        ["Sprachmodell laden", 1, "", ""],
        ["Buch lesen", 0, "", ""],
        ["Buch analysieren", 0, "", ""],
        ["Kapitelwortschatz ermitteln", 0, "", ""],
        ["Im Wörterbuch nachschlagen", 0, "", ""],
        ["Bedeutungen auflösen", 0, "", ""]
    ]
    // Mitten im Lauf. Die Nenner sind echt: `tools/sherlock.epub` hat 14 Kapitel, davon
    // 13 mit Fließtext — der zweite Nenner ist kleiner als der erste und ausdrücklich als
    // „Kapitel mit Text" beschriftet (Prüfzeile 3.4).
    readonly property var stagesRunning: [
        ["Sprachmodell laden", 2, "", ""],
        ["Buch lesen", 2, "14 von 14", "Kapiteln"],
        ["Buch analysieren", 1, "9 von 13", "Kapiteln mit Text"],
        ["Kapitelwortschatz ermitteln", 0, "", ""],
        ["Im Wörterbuch nachschlagen", 0, "", ""],
        ["Bedeutungen auflösen", 0, "", ""]
    ]
    readonly property var stages: variant === "lauf" ? stagesRunning : stagesStart
    readonly property string stageError:
        "Bezug von https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3 " +
        "fehlgeschlagen: <urlopen error [Errno 11001] getaddrinfo failed>"

    // ── Einrichtung ──────────────────────────────────────────────────────────────────
    readonly property string dataPath: "C:\\Users\\Domin\\Documents\\libreverbum\\data"
    readonly property string sourceNotice: "Wörterbuch: WikDict, Sprachpaar Englisch-Deutsch, aus Wiktionary erzeugt über das DBnary-Projekt (https://wikdict.com). Lizenz: Creative Commons BY-SA. Bezug von https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3."
    readonly property string downloadError:
        "Bezug von https://download.wikdict.com/dictionaries/sqlite/2/en-de.sqlite3 " +
        "fehlgeschlagen: <urlopen error [Errno 11001] getaddrinfo failed>"
    readonly property real loadedMegabytes: 8.4
    readonly property real totalMegabytes: 20.1

    // Zahlen aus `pipeline.PRESET_WORD_COUNT`; C2 kommt nicht vor (technik.md §11).
    readonly property var levels: [
        ["A1", "500 Grundformen"], ["A2", "1000 Grundformen"], ["B1", "2000 Grundformen"],
        ["B2", "3500 Grundformen"], ["C1", "5000 Grundformen"], ["keine Angabe", "nichts vorbelegt"]
    ]
    readonly property int chosenLevel: 2

    // ── Buch und Kapitel ─────────────────────────────────────────────────────────────
    // [Nummer, Titel, Ebene, Wortzahl (-1 = unlesbar), skip_reason]
    readonly property var sherlockChapters: [
        [1, "The Adventures of Sherlock Holmes", 0, 97, ""],
        [2, "I. A SCANDAL IN BOHEMIA", 0, 8580, ""],
        [3, "II. THE RED-HEADED LEAGUE", 0, 9176, ""],
        [4, "III. A CASE OF IDENTITY", 0, 7035, ""],
        [5, "IV. THE BOSCOMBE VALLEY MYSTERY", 0, 9662, ""],
        [6, "V. THE FIVE ORANGE PIPS", 0, 7338, ""],
        [7, "VI. THE MAN WITH THE TWISTED LIP", 0, 9258, ""],
        [8, "VII. THE ADVENTURE OF THE BLUE CARBUNCLE", 0, 7892, ""],
        [9, "VIII. THE ADVENTURE OF THE SPECKLED BAND", 0, 9865, ""],
        [10, "IX. THE ADVENTURE OF THE ENGINEER’S THUMB", 0, 8327, ""],
        [11, "X. THE ADVENTURE OF THE NOBLE BACHELOR", 0, 8178, ""],
        [12, "XI. THE ADVENTURE OF THE BERYL CORONET", 0, 9711, ""],
        [13, "XII. THE ADVENTURE OF THE COPPER BEECHES", 0, 10005, ""],
        [14, "THE FULL PROJECT GUTENBERG™ LICENSE", 0, 0, "besteht nur aus Vorspann bzw. Impressum"]
    ]
    readonly property var dorianChapters: [
        [1, "The Picture of Dorian Gray", 0, 51, ""],
        [2, "THE PREFACE", 1, 385, ""],
        [3, "CHAPTER I.", 1, 5003, ""],
        [4, "CHAPTER II.", 1, 5681, ""],
        [5, "CHAPTER III.", 1, 4466, ""],
        [6, "CHAPTER IV.", 1, 5636, ""],
        [7, "CHAPTER V.", 1, 4425, ""],
        [8, "CHAPTER VI.", 1, 2863, ""],
        [9, "CHAPTER VII.", 1, 4466, ""],
        [10, "CHAPTER VIII.", 1, 5343, ""],
        [11, "CHAPTER IX.", 1, 3960, ""],
        [12, "CHAPTER X.", 1, 3263, ""],
        [13, "CHAPTER XI.", 1, 7387, ""],
        [14, "CHAPTER XII.", 1, 2812, ""],
        [15, "CHAPTER XIII.", 1, 2518, ""],
        [16, "CHAPTER XIV.", 1, 4587, ""],
        [17, "CHAPTER XV.", 1, 3174, ""],
        [18, "CHAPTER XVI.", 1, 3142, ""],
        [19, "CHAPTER XVII.", 1, 1807, ""],
        [20, "CHAPTER XVIII.", 1, 3353, ""],
        [21, "CHAPTER XIX.", 1, 3631, ""],
        [22, "CHAPTER XX.", 1, 1936, ""]
    ]
    readonly property bool longBook: variant === "lang"
    readonly property var chapters: longBook ? dorianChapters : sherlockChapters
    readonly property string listBookTitle: longBook
        ? "The Picture of Dorian Gray" : "The Adventures of Sherlock Holmes"
    readonly property string listBookAuthor: longBook ? "Oscar Wilde" : "Arthur Conan Doyle"
    readonly property int selectedChapter: longBook ? 0 : 2
    readonly property string structureNotice: longBook
        ? "Die Datei nennt keine Navigation. Die Kapitel stammen aus der Lesereihenfolge " +
          "des Archivs; Titel und Grenzen können von der Buchgliederung abweichen."
        : ""
}
