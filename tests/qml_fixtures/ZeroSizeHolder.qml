import QtQuick

// Angriffsvorlage (B7, Befund B2, Durchsicht d993e3e): Ein 0×0-Halter — ein übliches
// Layoutmuster, um eine Gruppe ohne eigene Fläche zu bündeln — mit einem Text darin, der
// weit außerhalb des Fensters steht. Der alte Code übersprang jedes Kind mit 0×0 komplett
// (`continue`, noch vor dem `walk()`-Aufruf) und ließ damit den ganzen Teilbaum
// unbesucht — dieser Text wäre nie gesehen worden.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    // Sichtbarer Text zusätzlich zum versteckten unten — sonst zeichnet die Seite nur
    // die weiße Fläche, das Bild wäre einfarbig, und schon Schritt 1/2 (die Untergrenze
    // aus Befund B4) bräche den Lauf ab, bevor check_layout überhaupt an der Reihe ist.
    Text {
        objectName: "sichtbar"
        x: 20
        y: 20
        text: "Normaler Text, sichtbar"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Item {
        id: holder
        objectName: "holder"
        x: 20
        y: 60
        // width/height bewusst nicht gesetzt (0×0) — der alte Code sprang genau
        // hier über den ganzen Teilbaum hinweg.

        Text {
            objectName: "versteckt"
            x: 1500
            text: "Ich stehe außerhalb des Fensters"
            color: "#000000"
            font.family: "Inter"
            font.pixelSize: 16
        }
    }
}
