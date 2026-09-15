# Beobachtungen einfalten (Tor vor Phase 2) — Durchsicht

Datum: 15.09.2026 · Commit: 6dcbeaf, 01aed9b · Rolle: Durchsicht

- Das eigene Extraktionsskript für die offenen Punkte starb im ersten Lauf an einem
  `UnicodeEncodeError` (`→` gegen cp1252) — derselbe Fall, den der durchgesehene Commit in
  dokumentation.md §10 gerade regelt.
  Kosten: ein Wiederholungslauf mit `PYTHONUTF8=1`. Hätte durchgehen können: nein, der Lauf
  brach laut ab.
- Der Abgleich der offenen Punkte gegen die neue Übersichtstabelle ging nur maschinell; von
  Hand über 3.500 Zeilen wäre die eine fehlende Zeile vermutlich durchgerutscht.
  Kosten: rund zehn Minuten für ein Skript. Hätte durchgehen können: ja.
- Ob die neue Regel „Verfälschungslauf in `timeout` wickeln" befolgbar ist, ließ sich nur
  durch Ausprobieren in beiden Shells beantworten — aus dem Dokument geht nicht hervor,
  welche gemeint ist.
  Kosten: zwei Befehle. Hätte durchgehen können: ja.
- Der Auftrag an den Bauenden nannte „zwölf `### Offene Punkte`-Abschnitte" ausdrücklich als
  Vermutung; es sind dreizehn, weil §10 die Überschrift im Singular trägt.
  Kosten: keine. Hätte durchgehen können: nein — die Kennzeichnung als Vermutung hat genau
  das geleistet, wofür sie im selben Commit eingeführt wurde.
