# Nachträge einfalten, technik.md §8 bis Ende (Tor vor Phase 2) — Durchsicht

Datum: 15.09.2026 · Commit: 8f87838 (nachgebessert in 0af6b59) · Rolle: Durchsicht

- **Ein eigenes Prüfskript, das nichts findet, sieht aus wie ein bestandener Prüfpunkt.**
  Im Bestand steht öffnend `„` (U+201E), schließend aber ASCII `"` — nicht U+201C. Das
  erste Verweisskript suchte das typografische Paar und meldete „Zitate gesamt: 2" statt
  518. Kosten: rund 10 Minuten. Hätte durchgehen können: **ja**, und zwar als genau das
  falsche Grün, das die Durchsicht sucht: null tote Verweise, weil überhaupt keine
  Verweise gefunden wurden. Gerettet hat nur, dass der Auftrag „rund 160 Stellen" nannte
  und 2 dagegen absurd war.
  > Ableitung für dokumentation.md §10, neben „`PYTHONUTF8=1`" und „Textvergleiche über
  > `repr()`": **Ein eigenes Prüfskript meldet seine Trefferzahl und wird gegen eine
  > unabhängig bekannte Größe gehalten, bevor sein Ergebnis zählt.**
- **Eine Zahl im Auftrag ist kein prüfbarer Gegenstand, solange der Befehl fehlt, der sie
  erzeugt.** „74 Verweisstellen in 12 Dateien" enthält die Schreibregel-Stellen mit, die
  gar nicht nachzuziehen waren. Kosten: gering. Hätte durchgehen können: nein.
- **Der Verzicht auf `pytest` war hier richtig, ist aber begründungspflichtig.** Der Diff
  über alle zwölf Dateien enthält ausschließlich Markdown, Kommentare und Docstrings —
  keine ausführbare Zeile. Die Prüfung des Diffs ersetzt den Lauf in genau diesem Fall
  vollständig; die Testzahl stammt unbestätigt aus dem Bericht des Bauenden.
- **Ob Vorbefunde in den Bericht gehören, ließ der Auftrag offen.** Zwei Stellen waren
  schon vor dem Commit falsch oder unauflösbar (§8: „vier »Kapitel« zu je 30.000 Wörtern"
  gegen 0 Navigationseinträge und 6 Dokumente in der Tabelle darüber; §8c und
  `tools/print_fit_check.py`: „97,5 % Füllung (Abschnitt oben)" — die Zahl steht dort
  nicht). Getrennt ausgewiesen. Hätte durchgehen können: ja — bei strenger Auslegung von
  „Gegenstand ist der Commit" fielen sie unter den Tisch, und ein Durchsehender ist der
  Einzige, der sie überhaupt sieht.
- **Die Aufteilung eines Einfaltens auf mehrere Commits erzeugt tote Verweise auf Zeit.**
  `konzept.md` trug die neue §8c-Überschrift bereits seit `0b09b7d` — zwischen `0b09b7d`
  und `8f87838` zeigte dieser Verweis ins Leere, und keiner der beiden Bauenden konnte das
  sehen. Die verbindliche Umbenennungstabelle hat funktioniert; der Zustand dazwischen ist
  der Preis der Aufteilung.
