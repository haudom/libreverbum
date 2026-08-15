"""LibreVerbum — der Kern.

Zehn Module entlang der sechs Schritte des Kernablaufs (technik.md §7): `entities` trägt die
Gegenstände, je einen Schritt tragen `epub`, `extraction`, `profile`, `triage`, `dictionary`,
`translation`, `anki` und `printout`, und `pipeline` verkettet sie zu einem Durchlauf. Die
Karte sagt, wo etwas hingehört; die Module entstehen, wenn sie gebraucht werden.

Zwei Regeln sind verbindlich: Der Kern kennt die Oberfläche nicht (technik.md §1,
„Architekturregel"), und innerhalb des Kerns importiert jeder Schritt nur `entities` — wer
mehrere Schritte kennt, ist `pipeline` und sonst niemand (technik.md §7, „Die Importregel").
"""
