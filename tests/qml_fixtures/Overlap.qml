import QtQuick

// Angriffsvorlage (Befund N3, Nachprüfung 00ce53b): ein Rechteck mit höherem `z` deckt
// die rechte Hälfte eines Satzes ab. Die linke Hälfte zeigt weiterhin normal Tinte —
// „irgendeine Änderung beim Ausblenden" allein sagt deshalb nichts über den fehlenden
// Teil des Satzes. `z` steht bewusst über dem Standardwert des Textes, unabhängig von
// der Reihenfolge im Quelltext (`deckel` ist zusätzlich zuerst deklariert).
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Text {
        objectName: "kontrolle"
        x: 20
        y: 560
        text: "Kontrolle gut lesbar"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Rectangle {
        objectName: "deckel"
        x: 150
        y: 10
        width: 400
        height: 50
        color: "#4a545f"
        z: 5
    }

    Text {
        objectName: "halbverdeckt"
        x: 20
        y: 20
        text: "Hier steht ein wichtiger Satz"
        color: "#1a1f26"
        font.family: "Inter"
        font.pixelSize: 20
    }
}
