# Nachträge einfalten, konzept.md (Tor vor Phase 2) — Durchsicht

Datum: 15.09.2026 · Commit: 0b09b7d (nachgebessert in 0878216) · Rolle: Durchsicht

- **Der Prüfauftrag zählte die zu durchsuchenden Orte auf — und verengte damit, was der
  vorgeschriebene `grep` weit gefasst hatte.** `CLAUDE.md` stand in keiner der beiden
  Listen, weder beim Bauenden noch beim Prüfenden, und genau dort lag der zweitschwerste
  Befund: eine Kurzfassung der Regel aus dokumentation.md §7, die sich weiter mit dem
  eingefalteten Nachtrag belegte. Gefunden nur, weil der `grep` über den **ganzen**
  Wegwerfordner lief statt über die im Commit berührten Verzeichnisse. Kosten: ein Befehl.
  Hätte durchgehen können: ja — die Datei kommt im Diff gar nicht vor, die Stelle liest
  sich wie Prosa. Ableitung: Die Suchmenge bei einem Einfalten ist „alles außer
  `beobachtungen/`", nie „die geänderten Verzeichnisse".
- **Ein fremder Commit im Verlauf macht `git diff <vorvorgänger> <commit>` zur Falle.**
  Der Auftrag nannte dieses Paar; darin lag die README-Arbeit eines anderen Bearbeiters mit
  23 geänderten Zeilen, aus denen beinahe Befunde gegen den falschen Bauenden entstanden
  wären. Kosten: rund zehn Minuten und ein verworfener Befundentwurf. Hätte durchgehen
  können: ja. Ableitung: Das Vergleichspaar einer Durchsicht ist `git show <commit>`.
- **Wie ein Übergangszustand zu werten ist, ließ der Auftrag offen.** Vier Verweise aus
  konzept.md zeigten auf technik.md-Überschriften, die es im durchgesehenen Commit noch
  nicht gab — nach dem Buchstaben tote Verweise, nach der Absicht richtig vorbereitete.
  Entschieden gegen die verbindliche Umbenennungstabelle. Hätte durchgehen können: nein,
  aber nur wegen dieser Tabelle. Wo ein Einfalten auf mehrere Teilaufträge verteilt wird,
  ist sie nicht Komfort, sondern die einzige Prüfgrundlage des Durchsehenden.
- **Bei einem Dokumentationscommit ist das Tor nicht bloß unvollständig, es ist stumm.**
  Fünf der sechs Befunde dieser Runde sind vom Typ, den kein Testlauf je anfassen würde;
  `grep` war der ganze Prüfapparat. Das stützt dokumentation.md §10 an einer Stelle, an der
  es bisher nur für Code belegt war.
