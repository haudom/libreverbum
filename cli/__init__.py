"""Kommandozeilenzugang — Triage über die Tastatur (bauplan.md T16).

Aufgabe
-------
Ein vollständiger Kapiteldurchlauf von außerhalb des Kerns: EPUB wählen, Kapitel wählen,
`libreverbum.pipeline.run_chapter` aufrufen, die Kandidaten gegen das Profil abgleichen,
den Nutzer über die Tastatur durch die Triage führen und das Ergebnis nach Anki und als
Druckseite exportieren.

Dieses Paket liegt bewusst **neben** `libreverbum/`, nicht darunter (bauplan.md, „Die
Kommandozeile ist eine Oberfläche und gehört damit nicht in den Kern, sondern daneben").
Begründung der Platzwahl im Bericht zu T16. Der Kern bleibt unberührt: Jedes Modul hier
ruft ihn nur auf (technik.md §1, „Architekturregel"), es importiert dafür beliebig viele
Kernmodule zugleich — die Importregel aus technik.md §7 gilt nur innerhalb von
`libreverbum/`, nicht für die Oberfläche, die ihn aufruft.

Voraussetzungen
---------------
Eine interaktive Konsole (`input`/`print`), ein bereits bezogenes Wörterbuch
(`libreverbum.dictionary`, T6) und, sobald ein Wort zum Lernen markiert wird, ein
erreichbarer Modellserver (`config.toml`, technik.md §9 — keine Autosuche).
"""
