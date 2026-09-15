# Nachträge einfalten, technik.md §2/§3/§5/§6 (Tor vor Phase 2) — Bau

Datum: 15.09.2026 · Commit: 7f913c6 · Rolle: Bau

- **Die Umbenennungstabelle nannte einzelne Überschriften, nicht die verschachtelte
  Gruppe, in der sie stehen.** In §3 hängen vier Abschnitte aneinander („Warum die
  Festlegung …", „Trefferquote …", „Warum die Empfehlung …", „Zeit: Nachtrag zu …") und
  verweisen wechselseitig aufeinander — teils ohne das Wort „Nachtrag" zu benutzen („stand
  oben unter …", „siehe unten"). Kosten: rund 15 Minuten zusätzliches Lesen. Hätte
  durchgehen können: ja — ein `grep` nach „Nachtrag" findet diese Binnenverweise nicht,
  weil das Wort darin gar nicht vorkommt.
- **Zwei Verweistexte in `tools/` brachen an kollidierenden Anführungszeichen.** Der
  eingesetzte Text enthält `„…"`, die umgebende f-String-Zeile ebenfalls Anführungszeichen;
  beim ersten Versuch entstand ein Syntaxfehler. Gefangen von einem `ast.parse` über alle
  bearbeiteten `.py`-Dateien **vor** dem Prüftor. Kosten: eine Korrekturrunde, rund 5
  Minuten. Hätte durchgehen können: nein — `ruff check` hätte es gemeldet, aber erst nach
  dem vollständigen Testlauf, also teurer.
- **Ein zweiter Bearbeiter änderte während der Sitzung `CLAUDE.md`.** Die Datei blieb im
  Arbeitsbaum sichtbar verändert und wurde weder repariert noch mitcommittet. Kosten:
  keine, nur eine `git diff`-Kontrolle. Hätte durchgehen können: nein — aber mit `git add
  -A` wäre die fremde Arbeit mitgewandert, genau die Falle aus CLAUDE.md, „Arbeitsweise".
