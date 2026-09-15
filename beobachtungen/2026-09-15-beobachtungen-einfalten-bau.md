# Beobachtungen einfalten (Tor vor Phase 2) — Bau

Datum: 15.09.2026 · Commit: 6dcbeaf, 01aed9b · Rolle: Bau

- Ein zweiter Bearbeiter hat während der Sitzung zwei Commits (`7cb5d7b`, `bea4d1f`) in
  genau die Abschnitte gesetzt, die diese Teilaufgabe ebenfalls änderte — dokumentation.md
  §9 und CLAUDE.md, „Arbeitsweise".
  Kosten: ein vollständiger `git diff`/`git log`-Abgleich, um zu belegen, dass die eigenen
  Änderungen auf dem neuen Stand aufsetzen. Hätte durchgehen können: ja — die `Edit`-Aufrufe
  hätten stillschweigend gegen den inzwischen fremden Stand gematcht.
- Zwei Stellen im Bestand trugen dieselbe veraltete Zahl wie die im Auftrag genannten
  (technik.md §6 „32 Tests"; eine Marken-Aufzählung in CLAUDE.md ohne `needs_wordfreq`),
  der Auftrag nannte aber nur die zwei Stellen in dokumentation.md und CLAUDE.md.
  Kosten: gering, gefunden nur durch `grep` über den ganzen Bestand statt punktgenaues
  Ansteuern der genannten Zeilen. Hätte durchgehen können: ja — die Berichtigung hätte als
  erledigt gegolten, während zwei Fundstellen weiter dieselbe falsche Zahl stand.
- `git add --renormalize .` nimmt eine neue, noch nicht verfolgte Datei nicht mit; die
  `.gitattributes` blieb `??`, bis sie ausdrücklich hinzugefügt wurde.
  Kosten: zwei Fehlversuche. Hätte durchgehen können: ja — ohne die Kontrolle per
  `git status` hätte der Commit die neue Datei glatt vergessen.
- `git checkout -- <datei>` schrieb die Arbeitsbaumdatei trotz neuer `eol=lf`-Regel zunächst
  nicht um, weil Git den alten Stat-Cache nutzte; erst Löschen und erneutes Auschecken
  erzwang die Normalisierung.
  Kosten: ein Zwischenschritt. Hätte durchgehen können: ja — „belegen, dass die Prüfsumme
  hält" hätte sonst nur den unveränderten Altzustand geprüft.
