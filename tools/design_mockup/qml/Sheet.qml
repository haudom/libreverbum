import QtQuick
import Mock

// Ein Blatt — die Arbeitsfläche L1 auf dem Tisch L0.
//
// Deckende Füllung, 8 px Radius, eine Haarlinie als Kante. Kein Verlauf, kein
// Glanzstreifen, keine Durchsichtigkeit, kein Schlagschatten: Ein Blatt sieht überall
// gleich aus, egal worüber es liegt (review_round1.md B4/B16 — dort änderte die Scheibe
// ihren Kontrast je nachdem, welches Licht des Grundes zufällig darunter lag).
//
// `clip` ist an und bleibt an. Es ist die zweite Hälfte der Layoutregel: Das dehnbare
// Element bekommt die Resthöhe, alles Feste eine feste Höhe — und wenn doch einmal etwas
// überläuft, schneidet es hier **sichtbar** ab, statt lautlos über den Fensterrand zu
// laufen (B1/B2: dort meldete `shot.py` null Warnungen, während der Belegsatz unter der
// Tastenleiste hinaus aus dem Bild lief).
Rectangle {
    id: sheet

    property bool outlined: true

    color: Theme.surface
    radius: Theme.radius
    border.width: outlined ? Theme.borderWidth : 0
    border.color: Theme.hairline
    clip: true
}
