import QtQuick

// Angriffsvorlage (F8/F11, Nachprüfung d00e7c9):
// - RichText mit `<font face="Inter">` ohne eigenes `font.family` — die Item-eigene
//   Angabe bleibt der QML-Vorgabewert ("Sans Serif", ein generischer Alias, keine echte
//   Familie); das darf keine „SCHRIFT NICHT GELADEN"-Meldung auslösen.
// - Eine Textstelle mit `font.pointSize` statt `font.pixelSize` — `font.pixelSize()`
//   liefert dafür -1, `QFontInfo(font).pixelSize()` die tatsächliche Pixelgröße.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    Text {
        objectName: "richtext"
        x: 20
        y: 20
        textFormat: Text.RichText
        text: "<font face=\"Inter\">Formatierter Text</font>"
        color: "#000000"
    }

    Text {
        objectName: "punktgroesse"
        x: 20
        y: 60
        text: "Grosse Schrift in Punkt"
        color: "#7a7f85"
        font.family: "Inter"
        font.pointSize: 30
    }
}
