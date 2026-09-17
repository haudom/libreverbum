"""Erzeugt `qml/Mock/Content.qml` aus `data.json` und `chapter.json`.

Woher jede Zeichenkette stammt — und was **nicht** aus einem Lauf stammt:

* Wortformen, Wortarten, Häufigkeiten, Belegsätze: `extraction.extract_vocabulary` über
  `tools/sherlock.epub`, Kapitel 2, mit buchweiter Eigennamenstatistik (`collect_data.py`).
* Übersetzungsketten und Bedeutungsangaben: `dictionary.candidate_lists` gegen
  `tools/en-de.sqlite3`; `UNCERTAIN_LABEL`/`NO_SENSE_LABEL` im Wortlaut aus `dictionary`.
* Die Blöcke: die nach Häufigkeit sortierte Liste, gefiltert gegen die ersten 2000
  Grundformen von `wordfreq_en_5000.txt` (die B1-Vorbelegung, `PRESET_WORD_COUNT`), in
  Portionen zu `cli.interaction.WORD_BLOCK_SIZE` = 25.
* Kapitellisten: `pipeline.list_chapters` über `tools/sherlock.epub` und
  `tools/dorian_gray.epub`, samt echtem `skip_reason`.
* Die Stufenzahlen der Einrichtung: `pipeline.PRESET_WORD_COUNT`.

Von Hand gesetzt, weil kein Modellserver lief: **welche** Kandidatenbedeutung im Belegsatz
gemeint ist (sonst `translation.choose_sense`). Ebenso die Marke „neue Bedeutung eines
bekannten Wortes" — sie kommt aus dem Profil, nicht aus dem Kapitel. Beides ist unten am
Ort vermerkt.

Der Mockup zeigt durchweg den **ungünstigsten** Datenfall (review_round1.md B24): den
längsten Belegsatz des Kapitels (473 Zeichen), die längste Übersetzungskette und die
längste Bedeutungsangabe des Blocks, den Fortschritt im Anfangszustand, die Einrichtung
mit sichtbarer Fehlermeldung.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "qml" / "Mock" / "Content.qml"
BLOCK_SIZE = 25


def q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def collapse(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def split_sentence(sentence: str, form: str) -> tuple[str, str, str]:
    """Zerlegt den Belegsatz an der Wortform — in **derselben Beugungsform** wie in der
    Kopfzeile (Prüfzeile 5.6), deshalb ohne Rückgriff auf die Grundform."""
    text = collapse(sentence)
    index = text.find(form)
    if index < 0:
        raise SystemExit(f"Wortform {form!r} steht nicht im Belegsatz")
    return text[:index], form, text[index + len(form) :]


def main() -> None:
    # Wie in den übrigen tools/-Skripten: Ohne diese Zeile bricht jede deutsche
    # Ausgabe auf einer cp1252-Konsole mit UnicodeEncodeError ab.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    data = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
    chapters = json.loads((HERE / "chapter.json").read_text(encoding="utf-8"))
    rows = data["rows"]
    by_form = {r["form"]: r for r in rows}

    blocks = [rows[i : i + BLOCK_SIZE] for i in range(0, len(rows), BLOCK_SIZE)]

    def block_qml(block_index: int) -> str:
        lines = []
        for position, row in enumerate(blocks[block_index], 1):
            zelle = (q(row["pos"]), q(row["form"]), row["frequency"])
            lines.append(f"        [{position}, {zelle[0]}, {zelle[1]}, {zelle[2]}]")
        return ",\n".join(lines)

    def chapter_qml(name: str, *, constructed_levels: bool = False) -> str:
        """`constructed_levels` ist der einzige konstruierte Zug in dieser Datei: Keines
        der drei vorhandenen Bücher führt ein Kapitel mit `level > 0`, und Prüfzeile 2.5
        verlangt die Einrückung. Im langen Fall (Dorian Gray) werden die Kapitel deshalb
        eine Ebene unter den Buchtitel gehängt — ausgewiesen, nicht untergeschoben."""
        lines = []
        for chapter in chapters[name]["chapters"]:
            level = 1 if constructed_levels and chapter["n"] > 1 else chapter["lvl"]
            words = -1 if chapter["w"] is None else chapter["w"]
            skip = chapter["skip"] or ""
            nummer, titel = chapter["n"], q(chapter["t"])
            lines.append(f"        [{nummer}, {titel}, {level}, {words}, {q(skip)}]")
        return ",\n".join(lines)

    # ── Der Eintrag: zwei echte Fälle, beide der jeweils ungünstigste ────────────────
    # A „Bohemian": der längste Belegsatz des ganzen Kapitels, 473 Zeichen (Prüfzeile 5.5
    #   verlangt 400). Block 2, Position 8.
    # B „clergyman": die längste Übersetzungskette **und** die längste Bedeutungsangabe des
    #   Blocks — sechs Glieder, 58 Zeichen Angabe. Block 1, Position 8.
    bohemian = by_form["Bohemian"]
    clergyman = by_form["clergyman"]
    # Kurznamen nur fuer die Vorlage unten: Eine QML-Zeile soll dort in eine Zeile passen,
    # und `{q(bohemian["lemma"])} : {q(clergyman["lemma"])}` sprengt jede Breite.
    lemma_a, lemma_b = q(bohemian["lemma"]), q(clergyman["lemma"])
    freq_a, freq_b = bohemian["frequency"], clergyman["frequency"]
    len_a, len_b = bohemian["sentence_len"], clergyman["sentence_len"]
    autor_a = q(chapters["dorian_gray"]["book"]["author"])
    autor_b = q(chapters["sherlock"]["book"]["author"])
    b_before, b_word, b_after = split_sentence(bohemian["sentence"], "Bohemian")
    c_before, c_word, c_after = split_sentence(clergyman["sentence"], "clergyman")

    text = f"""pragma Singleton
import QtQuick

// Echte Inhalte — erzeugt von `build_content.py`, Herkunft jeder Zeichenkette in dessen Kopf.
// Nicht von Hand ändern.
QtObject {{
    readonly property string bookTitle: {q(data["book"]["title"])}
    readonly property string bookAuthor: {q(data["book"]["author"])}
    readonly property string chapterTitle: {q(data["chapter"]["title"])}
    readonly property int chapterNumber: {data["chapter"]["number"]}

    // Welcher Fall gerendert wird. Gesetzt von `shot.py --fall`; ohne Angabe der erste.
    readonly property string variant: typeof appCase !== "undefined" && appCase !== ""
                                      ? appCase : "lang"

    // ── Triage ───────────────────────────────────────────────────────────────────────
    readonly property bool longSentence: variant !== "kette"
    readonly property int blockNumber: longSentence ? 2 : 1
    readonly property int blockSize: {BLOCK_SIZE}
    readonly property int position: 8
    readonly property int chosenCount: 3

    readonly property string wordForm: longSentence ? {q(bohemian["form"])} : {q(clergyman["form"])}
    readonly property string lemma: longSentence ? {lemma_a} : {lemma_b}
    readonly property string pos: longSentence ? {q(bohemian["pos"])} : {q(clergyman["pos"])}
    readonly property int frequency: longSentence ? {freq_a} : {freq_b}

    // Von Hand: welche der Kandidatenbedeutungen im Satz gemeint ist. Das entscheidet
    // sonst `translation.choose_sense`; ein Modellserver lief für diese Vorlage nicht.
    readonly property string translation: longSentence
        ? {q(bohemian["senses"][0]["trans"].replace(" | ", " · "))}
        : {q(clergyman["senses"][0]["trans"].replace(" | ", " · "))}
    readonly property string senseLabel: longSentence
        ? {q(bohemian["senses"][0]["sense"])}
        : {q(clergyman["senses"][0]["sense"])}

    // Von Hand: die Marke kommt aus dem Profil, nicht aus dem Kapitel. Gezeigt wird sie am
    // Fall B, damit Prüfzeile 5.8 an einem Bild nachweisbar ist.
    readonly property bool newMeaning: !longSentence

    readonly property string sentenceBefore: longSentence ? {q(b_before)} : {q(c_before)}
    readonly property string sentenceWord: longSentence ? {q(b_word)} : {q(c_word)}
    readonly property string sentenceAfter: longSentence ? {q(b_after)} : {q(c_after)}
    readonly property int sentenceLength: longSentence ? {len_a} : {len_b}

    readonly property string uncertainLabel: {q(data["labels"]["uncertain"])}
    readonly property string noSenseLabel: {q(data["labels"]["no_sense"])}

    // [Nummer im Block, Wortart, Wortform, Häufigkeit]
    readonly property var blockTwo: [
{block_qml(1)}
    ]
    readonly property var blockOne: [
{block_qml(0)}
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
    readonly property string dataPath: "C:\\\\Users\\\\Domin\\\\Documents\\\\libreverbum\\\\data"
    readonly property string sourceNotice: {q(data["labels"]["source_notice"])}
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
{chapter_qml("sherlock")}
    ]
    readonly property var dorianChapters: [
{chapter_qml("dorian_gray", constructed_levels=True)}
    ]
    readonly property bool longBook: variant === "lang"
    readonly property var chapters: longBook ? dorianChapters : sherlockChapters
    readonly property string listBookTitle: longBook
        ? {q(chapters["dorian_gray"]["book"]["title"])} : {q(chapters["sherlock"]["book"]["title"])}
    readonly property string listBookAuthor: longBook ? {autor_a} : {autor_b}
    readonly property int selectedChapter: longBook ? 0 : 2
    readonly property string structureNotice: longBook
        ? "Die Datei nennt keine Navigation. Die Kapitel stammen aus der Lesereihenfolge " +
          "des Archivs; Titel und Grenzen können von der Buchgliederung abweichen."
        : ""
}}
"""
    OUT.write_text(text, encoding="utf-8")
    print(
        f"{OUT} geschrieben — Block 1 und 2 zu je {BLOCK_SIZE}, "
        f"längster Belegsatz {bohemian['sentence_len']} Zeichen"
    )


if __name__ == "__main__":
    main()
