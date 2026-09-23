import QtQuick

// Angriffsvorlage (B7): Text breiter als sein unmittelbares Elternelement — der klassische
// Layoutüberlauf, den layout_check() gegen das Elternrechteck misst.
Item {
    Rectangle {
        anchors.fill: parent
        color: "#ffffff"
    }

    Item {
        id: box
        x: 20
        y: 20
        width: 200
        height: 40

        Text {
            objectName: "lang"
            text: "Ein sehr langer Text, garantiert breiter als die zweihundert Pixel der Box"
            color: "#000000"
            font.family: "Inter"
            font.pixelSize: 20
        }
    }
}
