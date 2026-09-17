import QtQuick
import Mock

// Marke mit Wortlaut — nie eine Farbe allein, nie ein Punkt.
//
// Ersetzt die Wortartpunkte aus Runde 1 (review_round1.md B9: „ein Rätsel, dessen Lösung daneben
// steht" — vier 7-px-Punkte ohne Legende, bei denen Braun und Dunkeltürkis nicht zu
// unterscheiden waren). Eine Marke trägt immer den Text, den sie meint.
//
// **Sie ist kein Kasten mehr** (review_round3.md C6). Bis Runde 2 war sie ein abgerundetes
// Rechteck mit 1-px-Kontur in `accent` und halbfettem Text in `accent` — dieselbe Bauform
// wie die sekundäre Schaltfläche und wie die Tastenkappe. Damit stand auf einem
// Bildschirm, der **keine Maus braucht**, das einzige klickbar aussehende Ding genau
// dort, wo etwas zu lesen und nichts zu tun ist: Die eine Angabe, die eine Entscheidung
// wirklich ändern kann, wurde als Bedienelement gelesen und übersprungen.
//
// Jetzt ein Akzentbalken links und der Text in `inkSoft`. Der Balken ist dieselbe Breite
// wie der Balken der laufenden Zeile (`Theme.markerWidth`) — was `accent` heißt, heißt
// überall dasselbe —, und die Marke sieht aus wie eine Randbemerkung, weil sie eine ist.
// Der Akzent bleibt damit auf dem Bildschirm für „hier bist du gerade / das ist die
// Antwort" reserviert: laufende Zeile, Fokusring, Übersetzung, Wortform im Satz.
Item {
    id: tag

    property string text: ""

    implicitHeight: Math.max(Theme.space.l, label.implicitHeight)
    implicitWidth: Theme.markerWidth + Theme.space.m + label.implicitWidth

    Rectangle {
        id: bar
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: Theme.markerWidth
        height: Math.min(parent.height, label.implicitHeight + Theme.space.xs)
        radius: width / 2
        color: Theme.accent
    }

    Text {
        id: label
        anchors.left: bar.right
        anchors.leftMargin: Theme.space.m
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        text: tag.text
        color: Theme.inkSoft
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.tag
        font.weight: Theme.strong
        wrapMode: Text.WordWrap
    }
}
