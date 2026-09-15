# Beobachtungen einfalten (Tor vor Phase 2) — Nachbesserung

Datum: 15.09.2026 · Commit: 3e13493 · Rolle: Bau

- Der Abgleich der offenen Punkte gegen die Übersichtstabelle ließ sich nicht zuverlässig
  von Hand führen — der erste Durchgang übersah genau die eine Zeile, um die es ging; erst
  ein Zählskript über die `### Offene Punkte`-Blöcke gab Sicherheit.
  Kosten: rund zehn Minuten. Hätte durchgehen können: ja — derselbe Fehler wäre ein zweites
  Mal entstanden.
- Der Befund zum Verhalten von `timeout` unter PowerShell klang plausibel genug, um ihn
  ungeprüft zu übernehmen; erst der tatsächliche Aufruf bestätigte ihn bis in den Wortlaut
  der Fehlermeldung.
  Kosten: zwei Befehle. Hätte durchgehen können: ja — eine falsche Korrektur wäre in zwei
  Dokumente gewandert.
