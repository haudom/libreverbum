import QtQuick

// Angriffsvorlage für tests/test_gui_screenshot.py (B7, Durchsicht d993e3e): ein Text mit
// Kontrast deutlich unter der Schwelle. Farben absichtlich als Literal statt aus
// Theme.qml — diese Datei liegt unter tests/ und rendert isoliert gegen einen eigenen
// --qml-dir, nie gegen den echten Bestand (tests/test_design_tokens.py klammert
// tests/qml_fixtures/ deshalb ausdrücklich aus).
Item {
    Rectangle {
        anchors.fill: parent
        color: "#e3dfd6"
    }

    Text {
        objectName: "paleText"
        x: 20
        y: 20
        text: "Blasser Text"
        color: "#cfcabf"
        font.family: "Inter"
        font.pixelSize: 16
    }
}
