import QtQuick
import Mock

// Der Roboter — das Wartezeichen des Fortschrittsbildschirms.
//
// Das Verfahren aus Runde 1 bleibt, weil es klug und billig ist (review_round1.md 2.6): Gedreht
// wird nicht das Bild, sondern das Gesicht **auf** dem Kopf. Die Silhouette eines Zylinders
// ändert sich beim Drehen nicht, nur seine Merkmale wandern darauf entlang (x = R·sin φ)
// und werden zum Rand hin schmaler (Breite ∝ cos φ). Keine 3D-Transformation, kein Effekt.
//
// Vier Dinge sind anders als in Runde 1:
//
// 1. **Er hat einen Körper.** Vorher war er ein Kopf über einem Strich und sah aus wie ein
//    Gerät; jetzt ist er eine Figur mit Schultern, Armen und einer Brust, in der Zeilen
//    stehen. Das ist der Unterschied zwischen „ein Objekt wartet" und „jemand arbeitet".
// 2. **Er sieht sich um, er rotiert nicht.** ±0,95 rad mit Halten an beiden Enden statt
//    einer vollen Umdrehung alle 3,7 Sekunden (B18: „zwischen 135° und 225° ist das
//    Gesicht vollständig weg — rund ein Drittel jedes Zyklus zeigt keinen Roboter, sondern
//    ein Objekt"). Auf einem Bildschirm, der Minuten stehen kann, ist Geduld die Aussage.
// 3. **Er atmet und blinzelt.** Drei Bewegungen mit verschiedenen Perioden (Umsehen 8 s,
//    Atmen 3,4 s, Blinzeln alle 5,2 s) überlagern sich so, dass sich das Bild nie exakt
//    wiederholt — der Grund, warum eine Dauerrotation nach der dritten Minute nervt und
//    das hier nicht.
// 4. **Er ist flach.** Kein Verlauf, kein Glanz, kein Spitzlicht, kein Schlagschatten —
//    dieselbe Hausordnung wie jede andere Fläche. Was ihn trägt, ist die Form.
//
// Die Maße im Inneren sind Anteile von `hw` (der Kopfbreite) statt Vielfache der
// Rastereinheit. Das ist die eine ausgewiesene Ausnahme von der Rasterregel: Eine
// Zeichnung, die mitwachsen soll, hat Proportionen, kein Raster.
Item {
    id: robot

    // Bogenmaß; 0 = Blick nach vorn. Für das Standbild ein leichter Winkel: Ein Gesicht,
    // das den Betrachter frontal anstarrt, wirkt auf einem Wartebildschirm angespannt.
    property real angle: -0.30
    property bool working: true
    property real blink: 1.0        // 1 = Auge offen, 0 = geschlossen
    property real breath: 0.0       // −1 … 1, hebt und senkt die ganze Figur

    readonly property bool animating: robot.working
                                      && (typeof appAnimate !== "undefined" ? appAnimate : false)

    implicitWidth: 168
    implicitHeight: 208

    // ── Aufriss ──────────────────────────────────────────────────────────────────────
    // Alles hängt an der Kopfbreite `hw`. Die Figur ist rund 1,95 `hw` hoch; sie wird so
    // groß gewählt, dass sie in beide Richtungen hineinpasst, und dann mittig gestellt.
    readonly property real hw: Math.min(width * 0.70, height * 0.50)
    readonly property real headH: hw * 0.84
    readonly property real torsoH: hw * 0.62
    readonly property real figureH: hw * 0.30 + headH + hw * 0.07 + torsoH + hw * 0.12

    // NICHT `top` nennen: Eine Eigenschaft dieses Namens auf einem `Item` bringt die
    // QML-Erzeugung zum **Haengen** — kein Fehler, keine Warnung, das Fenster erscheint
    // nie. Gekostet hat das eine halbe Stunde Bisektion; `shot.py` kann es nicht melden,
    // weil es nie bis zum Rendern kommt.
    readonly property real originY: (height - figureH) / 2 + breath * hw * 0.020
    readonly property real cx: width / 2
    readonly property real headY: originY + hw * 0.30
    readonly property real headX: cx - hw / 2
    readonly property real cy: headY + headH * 0.48      // Höhe der Augenachse
    readonly property real rx: hw * 0.40                 // Radius des gedachten Zylinders
    readonly property real torsoY: headY + headH + hw * 0.07

    // Sichtbarkeit (Tiefe) und Querlage eines Merkmals, das bei phi auf dem Zylinder sitzt.
    function depth(phi) { return Math.cos(robot.angle + phi) }
    function across(phi) { return Math.sin(robot.angle + phi) }

    // ── Antenne und Lampe ────────────────────────────────────────────────────────────
    // Die Lampe sitzt auf dem Zylinder wie alles andere: Dreht der Kopf, wandert sie mit.
    Rectangle {
        x: robot.cx + robot.across(0) * robot.rx * 0.30 - width / 2
        y: robot.headY - robot.hw * 0.17
        width: Math.max(1, robot.hw * 0.022)
        height: robot.hw * 0.19
        color: Theme.inkFaint
    }

    Rectangle {
        id: lamp
        x: robot.cx + robot.across(0) * robot.rx * 0.30 - width / 2
        y: robot.headY - robot.hw * 0.27
        width: robot.hw * 0.115
        height: width
        radius: width / 2
        color: Theme.accentFill

        // Das Atmen des Lichts. „Es läuft noch" ist alles, was dieser Bildschirm
        // behaupten darf — und das Einzige, was er ohne Zahlen sagen kann.
        SequentialAnimation on opacity {
            running: robot.animating
            loops: Animation.Infinite
            NumberAnimation { to: 0.40; duration: 1700; easing.type: Easing.InOutSine }
            NumberAnimation { to: 1.00; duration: 1700; easing.type: Easing.InOutSine }
        }
    }

    // ── Ohren ────────────────────────────────────────────────────────────────────────
    // Die beiden Knöpfe an der Seite sind es, die die Drehung überhaupt lesbar machen:
    // Sie wandern an der Silhouette entlang und verschwinden hinter ihr. Ohne sie sähe
    // der Kopf aus, als bewegten sich nur die Augen.
    Repeater {
        model: [-Math.PI / 2, Math.PI / 2]
        delegate: Rectangle {
            required property var modelData
            readonly property real d: robot.depth(modelData)
            visible: Math.abs(robot.across(modelData)) > 0.45
            width: robot.hw * 0.10 * Math.max(0.35, Math.abs(d) * 0.5 + 0.5)
            height: robot.headH * 0.30
            radius: width / 2
            x: robot.cx + robot.across(modelData) * (robot.hw * 0.55) - width / 2
            y: robot.cy - height / 2
            z: -1
            color: Theme.robotShell
            border.width: Theme.borderWidth
            border.color: Theme.hairline
        }
    }

    // ── Kopf ─────────────────────────────────────────────────────────────────────────
    Rectangle {
        x: robot.headX
        y: robot.headY
        width: robot.hw
        height: robot.headH
        radius: width * 0.30
        color: Theme.robotShell
        border.width: Theme.borderWidth
        border.color: Theme.hairline
    }

    // ── Visier ───────────────────────────────────────────────────────────────────────
    // Das Visier ist am Kopf festgemacht und dreht sich nicht mit — es ist das Fenster,
    // die Augen dahinter sind es, die wandern. `clip` sorgt dafür, dass ein Auge am Rand
    // sauber verschwindet statt über die Wange zu laufen.
    Rectangle {
        id: visor
        x: robot.cx - width / 2
        y: robot.cy - robot.headH * 0.175
        width: robot.hw * 0.82 * (0.84 + 0.16 * Math.abs(robot.depth(0)))
        height: robot.headH * 0.35
        radius: height * 0.44
        clip: true
        color: Theme.robotVisor

        Repeater {
            model: [-0.55, 0.55]
            delegate: Rectangle {
                required property var modelData
                readonly property real d: robot.depth(modelData)
                readonly property real full: robot.hw * 0.155
                visible: d > 0.06
                width: full * d
                height: full * robot.blink
                radius: Math.min(width, height) / 2
                x: robot.cx - visor.x + robot.across(modelData) * robot.rx * 0.92 - width / 2
                y: visor.height / 2 - height / 2
                color: Theme.accentFill
            }
        }

        // Rückseite: Lüftungsschlitze. Ohne sie wirkte der Kopf bei abgewandtem Gesicht
        // ausgeschaltet statt abgewandt — er hätte dann gar kein Merkmal mehr.
        Row {
            id: vents
            readonly property real d: -robot.depth(0)
            spacing: robot.hw * 0.032
            visible: d > 0.06
            y: visor.height / 2 - robot.hw * 0.075
            x: robot.cx - visor.x + robot.across(Math.PI) * robot.rx * 0.92 - width / 2
            Repeater {
                model: 3
                delegate: Rectangle {
                    width: robot.hw * 0.024 * Math.max(0.25, vents.d)
                    height: robot.hw * 0.15
                    radius: width / 2
                    color: Theme.hairline
                }
            }
        }
    }

    // ── Lautsprechergitter unter dem Visier ──────────────────────────────────────────
    // Sitzt ebenfalls auf dem Zylinder und verschwindet beim Wegdrehen. Es ist der
    // einzige Grund, warum der Kopf ein Gesicht hat und kein Display ist.
    Row {
        spacing: robot.hw * 0.026
        y: robot.headY + robot.headH * 0.71
        x: robot.cx + robot.across(0) * robot.rx * 0.55 - width / 2
        visible: robot.depth(0) > 0.30
        opacity: Math.min(1, (robot.depth(0) - 0.30) * 4)
        Repeater {
            model: 4
            delegate: Rectangle {
                width: Math.max(1, robot.hw * 0.026)
                height: robot.hw * 0.055
                radius: width / 2
                color: Theme.hairline
            }
        }
    }

    // ── Hals ─────────────────────────────────────────────────────────────────────────
    Rectangle {
        x: robot.cx - robot.hw * 0.13
        y: robot.headY + robot.headH - robot.hw * 0.02
        width: robot.hw * 0.26
        height: robot.hw * 0.11
        color: Theme.robotShell
        border.width: Theme.borderWidth
        border.color: Theme.hairline
    }

    // ── Arme ─────────────────────────────────────────────────────────────────────────
    // Zwei Stummel, die den Rumpf breiter machen, als er ist. Sie bewegen sich nicht: Der
    // Roboter wartet mit den Händen im Schoß, und drei bewegte Dinge sind genug.
    Repeater {
        model: [-1, 1]
        delegate: Rectangle {
            required property var modelData
            width: robot.hw * 0.115
            height: robot.torsoH * 0.62
            radius: width / 2
            x: robot.cx + modelData * (robot.hw * 0.46 + width / 2) - width / 2
            y: robot.torsoY + robot.torsoH * 0.20
            color: Theme.robotShell
            border.width: Theme.borderWidth
            border.color: Theme.hairline
        }
    }

    // ── Rumpf ────────────────────────────────────────────────────────────────────────
    Rectangle {
        x: robot.cx - robot.hw * 0.46
        y: robot.torsoY
        width: robot.hw * 0.92
        height: robot.torsoH
        radius: robot.hw * 0.16
        color: Theme.robotShell
        border.width: Theme.borderWidth
        border.color: Theme.hairline

        // Das Brustfenster: drei Zeilen, die durchlaufen. Es ist die einzige Stelle, an
        // der die Figur sagt, was sie eigentlich tut — sie liest. Die Zeilen sind
        // verschieden lang wie Zeilen einer Seite, nicht gleich lang wie ein Ladebalken.
        Rectangle {
            id: chest
            anchors.centerIn: parent
            width: robot.hw * 0.52
            height: robot.torsoH * 0.52
            radius: robot.hw * 0.045
            color: Theme.robotVisor
            clip: true

            Column {
                id: lines
                width: parent.width - robot.hw * 0.10
                x: robot.hw * 0.05
                spacing: Math.max(1, robot.hw * 0.035)
                y: robot.hw * 0.04 + shift

                // Die Zeilen wandern nach oben und setzen unten wieder an — dieselbe
                // Aussage wie die Lampe, nur in der Sprache der Seite: Es geht weiter.
                property real shift: 0
                SequentialAnimation on shift {
                    running: robot.animating
                    loops: Animation.Infinite
                    NumberAnimation { to: -robot.hw * 0.115; duration: 2100; easing.type: Easing.InOutQuad }
                    PauseAnimation { duration: 700 }
                    NumberAnimation { to: 0; duration: 0 }
                    PauseAnimation { duration: 400 }
                }

                Repeater {
                    model: [1.0, 0.72, 0.88, 0.55]
                    delegate: Rectangle {
                        required property var modelData
                        width: lines.width * modelData
                        height: Math.max(1, robot.hw * 0.030)
                        radius: height / 2
                        color: Theme.robotShell
                    }
                }
            }
        }
    }

    // ── Sockel: eine Linie, kein Schatten ────────────────────────────────────────────
    // Die Figur steht auf etwas. Ein Schlagschatten wäre die einzige Stelle im ganzen
    // Entwurf, an der etwas schwebt — deshalb eine Haarlinie.
    Rectangle {
        x: robot.cx - robot.hw * 0.34
        y: robot.torsoY + robot.torsoH + robot.hw * 0.09
        width: robot.hw * 0.68
        height: Theme.borderWidth
        color: Theme.hairline
    }

    // ── Die drei Bewegungen ──────────────────────────────────────────────────────────
    // Das Umsehen: nach links, halten, nach rechts, halten. Kein Vollkreis.
    SequentialAnimation on angle {
        running: robot.animating
        loops: Animation.Infinite
        NumberAnimation { to: -0.95; duration: 2600; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 1400 }
        NumberAnimation { to: 0.95; duration: 2600; easing.type: Easing.InOutSine }
        PauseAnimation { duration: 1400 }
    }

    // Das Atmen: hebt und senkt die ganze Figur um rund zwei Pixel.
    SequentialAnimation on breath {
        running: robot.animating
        loops: Animation.Infinite
        NumberAnimation { to: 1; duration: 1700; easing.type: Easing.InOutSine }
        NumberAnimation { to: -1; duration: 1700; easing.type: Easing.InOutSine }
    }

    // Das Blinzeln: kurz, selten, und mit einer anderen Periode als die beiden anderen
    // Bewegungen — deshalb trifft es nie zweimal denselben Blickwinkel.
    SequentialAnimation on blink {
        running: robot.animating
        loops: Animation.Infinite
        PauseAnimation { duration: 4600 }
        NumberAnimation { to: 0.08; duration: 90 }
        PauseAnimation { duration: 70 }
        NumberAnimation { to: 1.0; duration: 130 }
    }
}
