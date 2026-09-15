# Nachträge einfalten, technik.md §8 bis Ende (Tor vor Phase 2) — Bau

Datum: 15.09.2026 · Commit: 8f87838 · Rolle: Bau

- **Die Ergänzung zur Datumsbewahrung kam mitten im Lauf** — aus der Durchsicht des
  vorigen Teilauftrags, als §8 bereits fertig war (dort war das Datum zufällig im Text
  erhalten). Für §8b, §8c, §11, §13 und die Mehrwortausdrücke war je Block eine
  Nachkontrolle nötig. Kosten: rund zehn Minuten je Block. Hätte durchgehen können: ja —
  ohne die Ergänzung wären mindestens die Daten aus §13 und den drei Blockzitaten der
  Mehrwortausdruck-Messung ersatzlos verlorengegangen; das Eindampfen führt sie nicht von
  selbst mit.
- **Ein ausdrücklich als „nicht selbst entscheiden" markierter Punkt braucht eine Antwort,
  bevor der Bearbeiter die Stelle erreicht.** Der §12-Verweis „Abschnitt 3, Nachtrag
  25.08.2026" wurde per Zwischennachricht aufgeklärt (Ziel: §9, `triage.order`) und kam
  rechtzeitig. Kosten: keine. Hätte durchgehen können: nein, weil ausdrücklich markiert.
- **Ein Test zitierte eine Stichwort-Phrase, die das Umschreiben aufgelöst hat.**
  `tests/test_epub.py` verwies auf „Der Fund ist ein stiller Verlust" — ein Satz, der in
  §8 nur solange stand, wie der Abschnitt ein Befundbericht war. Geschützt waren durch den
  Auftrag nur zwei andere Stichworte. Hätte durchgehen können: ja — ein `grep` nach der
  alten Phrase hätte nichts mehr gefunden, und kein Prüfbefehl zeigt einen Verweis an, der
  ins Leere geht.
- **Wie weit eine Tabellenspalte umzuformulieren ist, ohne ihre Zahlen zu verändern,
  stand nicht im Auftrag** („bisher gelesen" war dort nur Beispiel für „Bauanweisung, die
  weg muss"). Kosten: rund fünf Minuten Abwägung. Hätte durchgehen können: nein.
