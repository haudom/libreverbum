import QtQuick

// Angriffsvorlage (F7, Nachprüfung d00e7c9): `console.warn` unter einem eigenen
// `--qml-dir` (Direktpfad, ohne `Main.qml`) — vor der Nachbesserung hatte dieser Pfad
// keinen `qInstallMessageHandler` und ließ das unbemerkt durch.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    Text {
        text: "hallo"
        color: "#000000"
        font.family: "Inter"
        font.pixelSize: 16
    }

    Component.onCompleted: console.warn("F7-Testwarnung")
}
