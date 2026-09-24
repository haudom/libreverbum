import QtQuick

// Angriffsvorlage (Befund N2, Nachprüfung 00ce53b): RichText mit zwei Farbspannen in
// derselben Textstelle — ein langer, gut lesbarer Teil und eine kurze, blasse
// Randbemerkung („Warnung"). Die Randbemerkung liefert für sich genommen weit weniger
// geänderte Pixel als der lange Teil; eine Auswahl, die nur die häufigste Farbe oder
// eine relativ zur größten Gruppe bemessene Schwelle nimmt, übersieht sie. Gemessen
// werden muss die **schlechteste** Farbspanne, nicht die beste.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Text {
        objectName: "kontrolle"
        x: 20
        y: 100
        text: "Kontrolle gut lesbar"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Text {
        objectName: "reich"
        x: 20
        y: 20
        textFormat: Text.RichText
        font.family: "Inter"
        font.pixelSize: 16
        text: "<span style='color:#1a1f26'>Gut lesbarer langer Teil des Satzes hier</span> <span style='color:#cfcabf'>Warnung</span>"
    }
}
