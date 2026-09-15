# Nachträge einfalten, konzept.md (Tor vor Phase 2) — Bau

Datum: 15.09.2026 · Commit: 0b09b7d · Rolle: Bau

- Die Aufteilung des Einfaltens auf drei Teilaufträge stand im Widerspruch zur Forderung
  „kein Wort »Nachtrag« mehr in konzept.md": Innerhalb der eingefalteten Blöcke standen
  Zitate von technik.md-Überschriften, die erst ein späterer Teilauftrag umbenennen würde.
  Aufgelöst über die verbindliche Umbenennungstabelle im Auftrag — die künftigen
  Überschriften wurden vorweggenommen, außerhalb der eigenen Blöcke die alten belassen.
  Kosten: rund 20 Minuten Abwägen. Hätte durchgehen können: ja — ohne die Tabelle wäre
  entweder die harte Regel verletzt oder in fremdes Terrain eingegriffen worden.
- Der Auftrag verlangte namentlich sechs Verweisänderungen in `technik.md`, obwohl diese
  Datei zugleich Gegenstand eines anderen Teilauftrags war — ein Widerspruch zu CLAUDE.md,
  „Zwei Bearbeiter gleichzeitig lohnen sich nur bei disjunkten Dateien". Ausgeführt mit
  kleinen, genau gesetzten Änderungen und einer Gegenprobe des Dateizustands unmittelbar
  davor. Hätte durchgehen können: nein bei echtem Konflikt (Git hätte ihn gemeldet), aber
  ein stilles gegenseitiges Überschreiben derselben Zeile war nicht ausgeschlossen.
- Zwei Sätze in den Nachtragsblöcken trugen reine Bauplan-Bearbeitungsgeschichte (T9, T10,
  T15, „Befund 5, Review T9") ohne dauerhaften Wert — nach der Prüffrage aus
  dokumentation.md §7 ersatzlos gestrichen.
- `nohup pytest > datei 2>&1 &` kehrt in einem Hintergrundauftrag sofort zurück, nur der
  **Start** wird gemeldet, nicht der Lauf. Es brauchte einen zweiten Hintergrundlauf, der
  auf das Prozessende wartet. Kosten: rund 5 Minuten Umweg. Hätte durchgehen können: ja —
  wer den sofortigen Rückgabewert für das Testergebnis hält, meldet „fertig" ohne Lauf.
  (Der Bericht selbst blieb dabei aus; die Hauptsitzung hat den Lauf am Ende selbst
  gestartet und geerntet — das ist der Fall aus dokumentation.md §9, den die Regel
  „Bauen und Messen trennen" meint.)
