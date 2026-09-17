import QtQuick
import Mock

// Das Meldungsfeld — der Ort, an dem ein Fehlschlag **im Wortlaut** im Fenster steht
// (Regel 13, gemeinsame Prüfzeile aller sieben Bildschirme).
//
// Im alten Entwurf gab es dieses Bauteil nicht, und es gab auch keine Farbe dafür: Das
// einzige Rot der Token war an die Adjektive vergeben (review_round1.md B8). Hier hat
// `warn` genau diese eine Aufgabe.
//
// Zwei Tonlagen, dieselbe Bauform: `warn` für den Fehlschlag, `hinweis` für eine
// Einschränkung, die kein Fehlschlag ist (fehlende Navigation im EPUB, Prüfzeile 2.6) —
// eine Warnfarbe dafür wäre gelogen. Der Text bricht um und wird **nie** gekürzt: Regel 1,
// nichts fällt weg.
Rectangle {
    id: box

    property string text: ""
    property string tone: "warn"   // "warn" | "hinweis"

    readonly property color toneColor: tone === "warn" ? Theme.warn : Theme.inkSoft

    implicitHeight: label.implicitHeight + Theme.space.l
    color: tone === "warn" ? Theme.warnFill : "transparent"
    radius: Theme.radius
    border.width: Theme.borderWidth
    border.color: toneColor

    // Der Randstrich macht die Meldung auch dort erkennbar, wo die Füllung im dunklen
    // Thema fast auf dem Blatt liegt.
    Rectangle {
        width: Theme.markerWidth
        height: parent.height - Theme.borderWidth * 2
        x: Theme.borderWidth
        y: Theme.borderWidth
        color: box.toneColor
    }

    Text {
        id: label
        anchors.fill: parent
        anchors.leftMargin: Theme.space.m + Theme.markerWidth
        anchors.rightMargin: Theme.space.m
        anchors.topMargin: Theme.space.m - Theme.space.xs
        anchors.bottomMargin: Theme.space.m - Theme.space.xs
        text: box.text
        color: box.toneColor
        wrapMode: Text.Wrap
        font.family: Theme.fonts.ui
        font.pixelSize: Theme.size.small
        lineHeight: 1.35
    }
}
