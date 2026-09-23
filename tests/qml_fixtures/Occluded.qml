import QtQuick

// Angriffsvorlage (F3, Nachprüfung d00e7c9): Ein gut kontrastierter Text, danach von
// einem undurchsichtigen Element vollständig überdeckt. Ändert sich beim Ausblenden
// nichts, unterscheidet `check_contrast` das per `_find_occluder` von einer reinen
// Farbgleichheit — hier soll „ÜBERDECKT" stehen, nicht „UNSICHTBAR", weil ein zweites,
// sichtbares Element den Kasten überschneidet.
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
        objectName: "verdeckt"
        x: 20
        y: 20
        text: "Wichtiger Hinweis, verdeckt"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Rectangle {
        x: 10
        y: 15
        width: 300
        height: 30
        color: "#e3dfd6"
    }
}
