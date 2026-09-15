# Nachträge einfalten, technik.md §2/§3/§5/§6 (Tor vor Phase 2) — Durchsicht

Datum: 15.09.2026 · Commit: 7f913c6 (nachgebessert in 64ce625) · Rolle: Durchsicht

- **Die Vorgabe und die Umbenennungstabelle widersprachen sich stillschweigend.** Die
  Tabelle schrieb datumsfreie Überschriften vor, die Vorgabe verlangt „Messwerte behalten
  ihr Datum". Wo das Datum **nur** in der Nachtragsüberschrift stand, war es nach dem
  Einfalten ersatzlos weg — getroffen hat es vier Messungen, darunter die drei
  meistzitierten des Projekts (je rund 23 Verweise aus dem Code). Hätte durchgehen können:
  ja — ein Diff zeigt das nicht als Verlust, sichtbar wird es erst beim Abzählen der
  Datumsvorkommen vorher/nachher. Die Ergänzung „Stand das Datum nur in der Überschrift,
  wandert es in den ersten Messsatz" ging noch während des Laufs an den dritten
  Teilauftrag und hat dort mindestens vier weitere Daten gerettet.
- **Beim Verschmelzen zweier Nachträge genügt es nicht, dass alle Zahlen erhalten
  bleiben.** In §5 stand danach die Messreihe der verworfenen Je-Kapitel-Regel im Präsens
  unter der Überschrift der geltenden buchweiten und zählte Wörter auf, die heute gerade
  nicht wegfallen. Alles Geforderte war da, und der Abschnitt las sich trotzdem falsch.
  Die Prüffrage lautet also nicht „ist alles noch da?", sondern **„steht jede erhaltene
  Messreihe unter der Regel, unter der sie gemessen wurde?"**.
- **Eine neu geschriebene Zusammenfassung ist die gefährlichste Zeile eines Einfaltens.**
  Der Satz „zeigt ein genaueres und durchweg schnelleres Bild; das Budget hält damit erst
  recht" klang wie eine Zusammenfassung der Tabelle 200 Zeilen weiter unten und
  widersprach ihr in beiden Hälften. Im Diff sieht er richtig aus. Hätte durchgehen
  können: ja.
- **Ein Skript, das jedes Zitat der Form `datei.md §N, „…"` gegen die Überschriften und
  den Fließtext hält, findet tote Marken zuverlässiger als Lesen** und ist je Teilauftrag
  wiederverwendbar. Rund ein Drittel der Prüfzeit ging in die Einzelprüfung der ~50
  Verweise nach ihrer *Bedeutung* statt nach dem Datum.
- **Selbstmeldungen des Bauenden sind für die Durchsicht mehr wert als ihr Umfang
  vermuten lässt.** Der Hinweis auf den §12-Verweis („Abschnitt 3, Nachtrag 25.08.2026")
  nahm die Suche nicht ab, aber die Zuordnung: Ohne ihn wäre er als „gehört zum
  §12-Teilauftrag" abgelegt worden, statt nachzusehen, dass das Ziel in §3 nie existierte.
