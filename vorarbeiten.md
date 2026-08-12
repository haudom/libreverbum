# LibreVerbum — Vorarbeiten vor Phase 1

> Stand: 12.08.2026 · Eine Arbeitsliste, kein viertes Grundlagendokument. Was hier
> entschieden wird, wandert anschließend an seinen Platz: technische Festlegungen nach
> [technik.md](technik.md), Schreib- und Bauregeln nach [dokumentation.md](dokumentation.md),
> die zwei bis drei jederzeit geltenden Sätze nach [CLAUDE.md](CLAUDE.md). Diese Datei ist
> danach leer und wird gelöscht.

**Anlass:** Alle fünf technischen Entscheidungen stehen, Phase 1 kann beginnen. Es fehlt
aber das Gerüst, in dem gebaut wird — und es fehlen zwei Regeln gegen Fehler, die
speziell dann entstehen, wenn ein Modell den Großteil des Codes schreibt.

---

## Maßstab: was überhaupt aufgeschrieben wird

> Aufgeschrieben wird nur, was **(a)** kein Werkzeug prüfen kann und **(b)** unsichtbaren
> Schaden anrichtet, wenn es verletzt wird.

Alles andere gehört in ein Werkzeug, nicht in einen Text. Zeilenlänge,
Anführungszeichen und Importreihenfolge in ein Dokument zu schreiben kostet nur
Prüfaufmerksamkeit und wird still verletzt — dieselbe Begründung wie in
dokumentation.md §5: *Dokumentation, die lügen kann, lügt irgendwann.*

Das ist zugleich die Antwort auf die Ausgangsfrage. Ein klassischer Stilleitfaden wäre
für dieses Projekt Ballast; die Begriffstabelle in dokumentation.md §2 dagegen ist
unersetzlich, weil sie verhindert, dass in der siebten Sitzung `base_form` neben `lemma`
entsteht. Nicht das Schreiben von Code ist bei dieser Arbeitsweise der Engpass, sondern
das **Prüfen**. Konventionen, die Code prüfbar machen, zahlen sich vielfach stärker aus
als solche, die ihn hübsch machen.

---

## 1. Projektgerüst und Werkzeuge — **erledigt am 12.08.2026**

Entschieden und umgesetzt: Python 3.12, uv, ruff, pytest, mypy. Die Begründung samt
Lizenzprüfung, Messgrundlage und Befund am Bestand steht in technik.md §6; die
Prüfbefehle stehen in CLAUDE.md, „Prüfen vor »fertig«". Angelegt wurden `pyproject.toml`,
`uv.lock`, `.python-version`, das leere Kernpaket `libreverbum/` und `tests/`.

`tools/` ist am selben Tag nachgezogen worden; das ganze Repository besteht das Tor.

**Offen geblieben und in technik.md §6 vermerkt:** `PLW1514` für die
`encoding="utf-8"`-Pflicht ist noch nicht geprüft, `mypy --strict` noch nicht an echtem
Code erprobt.

<details>
<summary>Ursprüngliche Fassung des Punktes</summary>

**Lücke:** Weder Python-Version noch Abhängigkeitsverwaltung, Formatierer, Typprüfung
oder Testläufer sind irgendwo festgelegt. technik.md kennt bisher nur Sprache,
Oberfläche, Wörterbuch, Modell, Ablage und NLP-Bibliothek.

**Warum zuerst:** Ein automatisches Tor, das jede Änderung passieren muss, ist bei
maschinell geschriebenem Code die wirksamste Einzelmaßnahme — wirksamer als jede
Regel, die nur gelesen wird.

Vorschlag, im Einzelnen zu entscheiden:

| Zweck | Vorschlag | Lizenz (**vor Aufnahme prüfen**, technik.md §1) |
|---|---|---|
| Formatieren und Linten | **ruff** — ersetzt black, isort und flake8 in einem Werkzeug | MIT |
| Tests | **pytest** — wird für dokumentation.md §5 ohnehin gebraucht | MIT |
| Typprüfung auf dem Kern | **mypy** oder **pyright**, samt Typannotationen | MIT |
| Umgebung und Abhängigkeiten | **uv**, `pyproject.toml` als einzige Quelle | Apache-2.0 / MIT |
| Python-Version | festnageln; 3.12 ist der sichere Stand für spaCy und PySide6 | — |

Die Typprüfung fängt genau den Fehler, der beim Schreiben durch ein Modell entsteht:
erfundene Attribute und Signaturen, die plausibel aussehen und erst zur Laufzeit
auffallen.

**Zu tun**

- [x] Werkzeuge entscheiden, Lizenz jedes Pakets vor der Aufnahme prüfen
- [x] Python-Version prüfen und festlegen (spaCy `en_core_web_md`, PySide6)
- [x] `pyproject.toml` anlegen, `.venv/` bleibt ungetrackt
- [x] Als *Abschnitt 6* in technik.md aufnehmen, mit Begründung wie bei 1 bis 5
- [x] In CLAUDE.md den Befehl nennen, der vor jedem „fertig" zu laufen hat

</details>

---

## 2. Modulaufteilung und Importregel

**Lücke:** technik.md §1, „Architekturregel" fordert den Kern „ohne jeden Bezug zur
Oberfläche" — aber welche Module es gibt und wer wen importieren darf, steht nirgends.

**Warum das zählt:** Ohne festgelegte Aufteilung erfindet jede Sitzung die Struktur neu.
Das ist die teuerste Form der Drift, weil sie sich erst zeigt, wenn schon Code darauf
aufbaut. Eine einmalige Modulkarte genügt: ein Satz je Modul, dazu die Importrichtung.

**Und die Regel ist prüfbar.** Regel 9 (*NLP- und Modellaufrufe nie im
Oberflächen-Thread*) steht in der Prüftabelle von dokumentation.md §5 bisher unter
„Bauentscheidung ohne sinnvollen Testpunkt". Für ihre strukturelle Hälfte stimmt das
nicht: Ein Test kann feststellen, dass unter dem Kernpaket kein `PySide6` importiert
wird. Damit wird aus einer Absichtserklärung eine geprüfte Zusage.

**Zu tun**

- [ ] Modulkarte für Phase 1 festlegen — je Modul ein Satz, entlang der sechs Schritte
      des Kernablaufs (konzept.md, „Der Kernablauf")
- [ ] Importrichtung festhalten: Oberfläche → Kern, nie umgekehrt
- [ ] Test schreiben, der den Kern auf Freiheit von Oberflächen-Importen prüft
- [ ] Prüftabelle in dokumentation.md §5 um Regel 9 ergänzen

---

## 3. Regel 13 — nichts scheitert leise

**Lücke:** Nirgends steht, was geschehen soll, wenn der Modellserver nicht antwortet,
das EPUB kaputt ist oder ein Wörterbucheintrag fehlt.

**Warum das gerade hier gefährlich ist:** An dieser Stelle entsteht reflexhaft ein
`try/except` mit einer Protokollzeile. Das Ergebnis ist **leises Scheitern** — genau die
Falle, die technik.md unter „Die Falle: es scheitert nicht laut, sondern leise" schon
einmal beschreibt. Der `saw`-Fall ist derselbe Mechanismus: Es kommt ein Ergebnis, es
sieht brauchbar aus, es ist falsch. Ein halb gefülltes Kapitel, dessen fehlende Hälfte
nur im Protokoll steht, ist schlimmer als ein Abbruch mit Meldung.

Formulierungsvorschlag für dokumentation.md §4:

> **Regel 13:** Kein `except`, das den Fehler nur protokolliert und weiterläuft. Wer
> einen Fehlschlag abfängt, macht ihn im Ergebnis sichtbar — als Abbruch mit
> Fehlermeldung oder als markierter Eintrag (`uncertain`, vgl. Regel 10).

**Zu tun**

- [ ] Regel 13 in dokumentation.md §4 aufnehmen, Quelle: technik.md, „Die Falle…"
- [ ] Prüfpunkt in §5 ergänzen: unerreichbarer Modellserver führt zu sichtbarem
      Fehlschlag, nicht zu einem stillen Loch in der Wortliste

---

## 4. Regel 14 — Umfangsgrenze

**Lücke:** Es gibt keine Aussage darüber, was **nicht** gebaut wird.

**Warum:** Beim Schreiben durch ein Modell entstehen ungefragt Konfigurationsschalter,
Abstraktionsschichten, Zwischenspeicher und Vorkehrungen „für später". Für ein Werkzeug
mit einem einzigen Nutzer ist eine Umfangsgrenze mehr wert als jede Stilregel — jede
Zeile, die niemand angefordert hat, muss trotzdem gelesen, geprüft und gepflegt werden.
konzept.md, „Abgrenzung" zieht diese Linie bereits fürs Produkt; sie fehlt fürs Bauen.

Formulierungsvorschlag:

> **Regel 14:** Gebaut wird, was die aktuelle Phase verlangt. Keine
> Konfigurationsschalter ohne zweiten Anwendungsfall, keine Abstraktion über einer
> einzigen Umsetzung, kein Zwischenspeicher ohne gemessenen Anlass. Was für eine
> spätere Phase gedacht ist, steht im Phasenplan, nicht im Code.

Dazu gehört die schon geltende, aber nirgends als Vorbedingung notierte Pflicht: **keine
neue Abhängigkeit ohne vorherige Lizenzprüfung** (technik.md §1, „Bekannte Kosten").

**Zu tun**

- [ ] Regel 14 in dokumentation.md §4 aufnehmen
- [ ] Lizenzprüfung als Vorbedingung jeder neuen Abhängigkeit ausdrücklich festhalten

---

## 5. Der Ort entscheidet über die Wirkung

Eine Regel wirkt nur dort, wo beim Bauen tatsächlich hingesehen wird. CLAUDE.md wird
jede Sitzung geladen, dokumentation.md nicht zwangsläufig — deshalb gehören die wenigen
jederzeit geltenden Sätze nach CLAUDE.md und der Rest bleibt, wo er steht, mit Verweis
von dort. Dasselbe Gefälle wie in dokumentation.md §1: **Was im Bestand steht, gilt
faktisch.**

Der `REGEL`-Marker aus §4 ist genau dafür das richtige Mittel und bleibt unverändert:
Er bringt die Begründung an die eine Stelle im Code, an der die Verletzung verlockend
ist, ohne sie abzuschreiben.

**Zu tun**

- [ ] Nach den Entscheidungen 1 bis 4 prüfen, welcher Satz nach CLAUDE.md gehört und
      welcher nur verwiesen wird
- [ ] CLAUDE.md, „Aktueller Stand" nachziehen, sobald Phase 1 beginnt

---

## Bewusst nicht gemacht

- **Kein allgemeines Stilkapitel.** Was ruff erzwingt, wird nicht zusätzlich
  aufgeschrieben. Ein Kapitel „Coding Conventions" verdünnte nur die zwölf Regeln, die
  wirklich Schaden verhindern
- **Keine Sammlung von Mustervorlagen** über die Docstring-Vorlage in §3 hinaus. Vorlagen
  werden gefüllt, auch wo nichts zu sagen ist — dieselbe Begründung, aus der die
  Pflichtabschnitte im Docstring auf zwei gekürzt wurden
- **Kein eigenes Regelwerk „für KI".** Die vorhandenen Regeln gelten für Mensch und
  Modell gleichermaßen; ein zweites Regelwerk daneben erzeugt nur die Frage, welches gilt

---

## Reihenfolge

1 zuerst — solange kein Formatierer, Testläufer und keine Typprüfung stehen, sammelt
sich Code an, der später nachgezogen werden muss. Dann 2, weil die Modulkarte die erste
Zeile Anwendungscode überhaupt verortet. 3 und 4 sind kurze Texteingriffe und können
jederzeit dazwischen. 5 kommt zum Schluss, wenn feststeht, was tatsächlich gilt.
