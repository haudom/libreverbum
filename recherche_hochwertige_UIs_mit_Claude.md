# Hochwertige UIs mit Claude & Claude Code bauen: Ein praxisorientierter Leitfaden (Stand: September 2026)

## TL;DR
- **Der wirksamste Hebel für gutes Design ist die richtige Kontext-Steuerung, nicht das Modell an sich:** Installiere Anthropics offizielle **frontend-design**-Skill (Repo `anthropics/skills`, im Juni/August 2026 neu geschrieben; laut Skillselion mit **861.501 Installs** die drittmeist­installierte Skill überhaupt), lege einen kompakten Design-/Token-Block in deine `CLAUDE.md`, und baue einen **Screenshot-Verifikations-Loop** über Playwright- oder Chrome-DevTools-MCP. Das sind die drei Dinge, die "AI-Slop"-Optik zuverlässig verhindern.
- **Für einen Studenten/Werkstudenten reicht ein schlankes Setup:** frontend-design-Skill + `CLAUDE.md`-Designblock + shadcn/ui-MCP + ein Browser-MCP (Chrome DevTools MCP). Figma-Dev-Mode-MCP und 21st MCP (ex-Magic) lohnen sich nur, wenn du wirklich aus Figma-Designs baust bzw. schnell Komponentenvarianten brauchst.
- **Aktualitätswarnung:** Das Feld bewegt sich schnell. "Magic MCP" heißt jetzt **21st MCP**, alte API-Keys wurden zurückgesetzt; der offizielle Figma-MCP verlangt einen bezahlten Full/Dev-Seat; viele MCP-Server sind noch pre-1.0 mit häufigen Breaking Changes. Prüfe Versionsstände vor dem Produktiveinsatz.

## Key Findings

1. **Warum Claude generische UIs baut ("Distributional Convergence").** Laut Anthropics Engineering-Blogpost *"Improving frontend design through Skills"* (12. November 2025, verfasst von Prithvi Rajasekaran und Alexander Bricken, angekündigt von Boris Cherny am 14.11.2025) samplen Modelle ohne Steuerung aus dem "hochwahrscheinlichen Zentrum" der Trainingsdaten – daher Inter-Font, lila Gradienten auf Weiß, drei-Karten-Grids. Die Lösung ist explizite Steuerung: konkrete ästhetische Vorgaben plus Verbote generischer Muster.

2. **Die offizielle frontend-design-Skill ist der zentrale Baustein.** Sie ist Teil von `anthropics/skills` (Repo mit **176k Stars**; skills.sh listet "GitHub Stars 176.0K", live abgerufen Sept. 2026) und wurde 2026 grundlegend neu geschrieben – weg von starren Font-Blacklists, hin zu einer "Design-Lead in einem kleinen Studio"-Rolle mit Prozess (brainstorm → explore → plan → critique → build → critique again) und einem Token-System (4–6 benannte Hex-Farben, 2+ Schriftrollen, Layout-Konzept, ein "Signature"-Element). Verbatim aus der SKILL.md: *"Approach this as the design lead at a small studio known for giving every client a visual identity that could not be mistaken for anyone else's."*

3. **Screenshot-Feedback-Loops sind der Qualitätssprung.** Claude kann Frontend-Code gut schreiben, aber schlecht visuell urteilen. Der Loop "Code generieren → im Browser rendern → Screenshot → Claude bewertet & korrigiert" über einen Browser-MCP ist der wichtigste Praxis-Trick. Die Skill selbst rät: "taking screenshots if your environment supports it – a picture is worth 1000 tokens."

4. **MCP-Landschaft für UI:** Figma-MCP (offiziell Dev Mode + Community-Framelink), Browser-MCPs (Playwright, Chrome DevTools, Claude in Chrome), Komponenten-MCPs (shadcn/ui, 21st/ex-Magic), Storybook-MCP, sowie Accessibility/Lighthouse-MCPs. Für Einzelentwickler sind 2–3 davon sinnvoll, der Rest ist Overkill.

5. **Stack-Fit:** React + Tailwind + shadcn/ui ist der von Anthropic selbst genutzte und am besten unterstützte Stack (auch die web-artifacts-builder-Skill baut darauf). Next.js/Vue/Svelte funktionieren gut. .NET/Desktop (Blazor, WPF, Avalonia, MAUI) funktioniert schlechter, aber Avalonia hat inzwischen einen eigenen "Build MCP".

## Details

### 1. Prompting & Workflow für UI-Qualität

**Konkrete Prompting-Techniken (aus dem offiziellen Anthropic-Blog, Nov 2025):**
- **Interessante Typografie erzwingen.** Anthropics Beispielprompt verbietet explizit: "Never use: Inter, Roboto, Open Sans, Lato, default system fonts" und schlägt distinctive Alternativen vor (JetBrains Mono, Playfair Display, IBM Plex, Bricolage Grotesque). Prinzip: hoher Kontrast bei Schriftpaarungen, extreme Gewichte (100/200 vs. 800/900), Größensprünge von 3x+.
- **Auf eine Ästhetik committen.** Statt "modern" konkrete Richtung: brutalist, luxury, editorial, retro-futuristic, RPG-Theme etc. Der ~400-Token-Block `<frontend_aesthetics>` aus dem Blogpost fasst Typografie, Farbe/Theme (CSS-Variablen, dominante Farben + scharfe Akzente), Motion (CSS-only bzw. Motion-Library für React, ein orchestrierter Page-Load statt verstreuter Micro-Interactions) und Backgrounds (Gradienten/Geometrie statt Volltonfarben) zusammen.
- **"Prompting at the right altitude":** Weder Hardcoding (exakte Hex-Codes) noch vage High-Level-Anweisungen, sondern zielgerichtete Sprache, die das Modell zum Nachdenken über Design-Achsen bringt.
- **Design-Referenzen mitgeben.** Screenshots direkt in Claude Code einfügen (Strg+V, auch auf macOS). Ein bewährter Community-Trick: einen v0-"Design System"-Screenshot als Ästhetik-Anker einfügen und Claude anweisen, sich daran zu orientieren.
- **Selbstkritik einbauen.** Die neue Skill rät zu einem Zwei-Pass-Ansatz und "Chanel's advice: before leaving the house, take a look in the mirror and remove one accessory."

**Screenshot-Feedback-Loop – konkretes Setup:**
- Browser-MCP installieren (siehe MCP-Abschnitt), Dev-Server starten, dann eine feste Regel in `CLAUDE.md`: "Nach jeder Änderung an Komponente/Seite/Stylesheet: 1. Route mit dem Browser-MCP ansteuern. 2. Screenshot bei 1280x800 und 375x812. 3. Konsole auf Fehler prüfen." (Muster aus einem QASkills-Praxisleitfaden, 2026.)
- Wichtig laut Praxisberichten: Der Screenshot ist **nicht** das Deliverable – man muss Claude explizit sagen, was "verifiziert" bedeutet (z.B. konkrete Akzeptanzkriterien), sonst meldet der Agent auch bei kaputter Seite Erfolg.

**Konsistenz mit bestehendem Design-System:**
- shadcn/ui-Kombination aus Skill (`npx skills add shadcn/ui`, liest `components.json`), MCP-Server (Live-Docs & Komponenten-Install) und Preset (Design-Tokens). Damit rät Claude nicht mehr Komponenten-APIs, sondern liest den echten Projekt-Stand.
- Storybook-MCP: verbindet die laufende Storybook-Instanz, damit der Agent Prop-Definitionen prüft, statt sie zu halluzinieren. Empfohlene CLAUDE.md-Regel (offizielle Storybook-Doku): "Never hallucinate component properties! Before using ANY property … you MUST use the MCP tools to check if the property is actually documented."

**CLAUDE.md für Frontend – was reinkommt:**
- Offizielle Anthropic-Guidance: **kurz und signalstark halten**, Zielwert unter 200 Zeilen. Wichtig: CLAUDE.md wird als User-Message/Kontext behandelt, **nicht** als erzwungene Konfiguration – für harte Regeln braucht man Hooks.
- Für Frontend sinnvoll: der Design-Ästhetik-Block (Fonts-Verbote, Farbphilosophie), Verweis auf das Design-System/Token-Datei, Komponenten-Verzeichnis und Konventionen ("nie Hex hardcoden, nutze Tokens"), Tailwind-Konventionen, sowie die Screenshot-Verifikations-Regel. Anti-Overengineering: "use the simplest possible approach" hilft gegen unnötige Abstraktionen.

**Plan Mode, Subagents, /commands:**
- **Plan Mode:** Claude erst planen lassen (oft mit stärkerem Modell für die Planung, günstigerem für die Ausführung), bevor Code geschrieben wird. Planung vor Implementierung wird von praktisch allen Best-Practice-Quellen als nicht verhandelbar bezeichnet.
- **Subagents:** Writer/Reviewer-Muster – ein Agent baut die UI, ein zweiter mit frischem Kontext reviewt (weniger Bias). Für Design gibt es Community-Agents wie einen "accessibility-expert" (WCAG-Review) oder Design-Critique-Skills.
- **/commands & Plugins:** Slash-Commands in `.claude/commands/`, Skills in `.claude/skills/`, gebündelt als Plugins.

**Häufige Fehlerquellen:**
- Context Rot: zu langer/verrauschter Kontext degradiert die Qualität – `/clear` beim Task-Wechsel, `/compact` zum Verdichten.
- Overengineering und "erfundene" Zweit-Komponentensysteme parallel zum bestehenden Design-System.
- Blindes Vertrauen in "sieht fertig aus"-Meldungen ohne visuelle Verifikation.
- Vage Anweisungen ("mach es modern") produzieren genau die generische Optik, die man vermeiden will.

### 2. Offizielle Anthropic-Ressourcen

- **Engineering-/Produkt-Blog:** *"Improving frontend design through Skills"* (claude.com/blog, 12.11.2025) – die Kernquelle für Prompting-Technik.
- **Frontend Design Cookbook:** Jupyter-Notebook `prompting_for_frontend_aesthetics.ipynb` im Repo `anthropics/claude-cookbooks`.
- **frontend-design Plugin/Skill:** in `anthropics/claude-code` unter `plugins/frontend-design/` und in `anthropics/skills` unter `skills/frontend-design/`. Beschreibung: "Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one."
- **web-artifacts-builder-Skill:** baut hochwertigere Artefakte in claude.ai mit React + Tailwind + shadcn/ui (bündelt am Ende via Parcel in eine HTML-Datei). Aktivieren mit "use the web-artifacts-builder skill".
- **Claude Code Best-Practices-Doku** (code.claude.com/docs): Plan Mode, Subagents, Plugins, Marketplaces.
- **Claude Design** (claude.ai/design): laut Anthropic-Ankündigung (anthropic.com/news/claude-design-anthropic-labs, 17.4.2026) *"powered by our most capable vision model, Claude Opus 4.7, and available in research preview for Claude Pro, Max, Team, and Enterprise subscribers."* Wandelt Prompts/Docs/Codebases in Prototypen, Slides, Landing Pages. Killer-Feature: liest deine Codebase, um dein echtes Design-System (Farben, Typografie, Komponenten) anzuwenden; Output ist Live-HTML mit engem Handoff zu Claude Code.
- **Artifacts / Generative UI:** interaktive Apps direkt im Chat; gut zum schnellen Prototyping.
- **Claude in Chrome:** Chrome-Extension, mit der Claude deinen echten Browser (mit Logins/Cookies) steuert – gut für authentifizierte Apps und schnelle visuelle Checks.

**Wann was?** Claude Design = schnelle Exploration/Prototyp ohne Code. Artifacts = interaktive Einzel-Demos im Chat. Claude Code + frontend-design-Skill = produktiver Code im echten Repo. Claude in Chrome = visuelle Checks in authentifizierten/echten Sessions.

### 3. Skills (Agent Skills)

**Offizielle Skills (Repo `anthropics/skills`, 176k Stars):** `frontend-design` (Kern), `web-artifacts-builder`, `canvas-design` (PNG/PDF-Grafik), `theme-factory`, `brand-guidelines`, `webapp-testing` (Playwright-basierte UI-Verifikation), `skill-creator` (zum Bauen eigener Skills).

**Community-/Partner-Skills für UI (Auswahl, mit Qualitätshinweis):**
- **Vercel web-design-guidelines** (Repo `vercel-labs/agent-skills`, **31,2k Stars**, main-Branch, Sept. 2026): reviewt bestehenden UI-Code gegen die "Web Interface Guidelines" (100+ Regeln zu Accessibility, Performance, UX). Ergänzt frontend-design (Kreativität) um Korrektheit. Lädt die Regeln live aus dem Guidelines-Repo (`vercel-labs/web-interface-guidelines`), bleibt damit aktuell. Install: `npx skills add https://github.com/vercel-labs/agent-skills --skill web-design-guidelines`.
- **claudekit/superpowers-Ökosystem:** enthält frontend-design-Varianten; große Community-Sammlungen wie `antigravity-awesome-skills` (~22k Stars, 1.234+ Skills, Stand März 2026) bündeln Rollen-Kits ("Web Wizard": frontend-design, api-design-principles, lint-and-validate).
- **shadcn-registries-Skill:** verwaltet components.json, erkennt Package-Manager, findet Komponenten über mehrere Registries.
- **Warnhinweis:** Viele Marketplace-Einträge (mcpmarket.com, claudemarketplaces.com) sind Aggregatoren, nicht Originalquellen. Prüfe immer das GitHub-Original, Stars und letztes Update. Manche "v1"-Skills sind explizit als veraltet markiert (Backward-Compat), z.B. `design-taste`-v1 vs. `design-taste-frontend`-v2.

**Installation/Verwaltung (Stand 2026):**
- **Skill lokal:** Ordner `.claude/skills/<name>/SKILL.md` (projektweit) oder `~/.claude/skills/<name>/` (global). Claude lädt sie automatisch, wenn der Task passt, oder per `/<name>` aufrufen.
- **Plugin/Marketplace:** `/plugin marketplace add <owner/repo>` dann `/plugin install <name>@<marketplace>`. Offizielle Marketplaces: `claude-plugins-official` und `anthropic-agent-skills`. Nach Installation ggf. `/reload-plugins`.
- **claude.ai/Cowork/Desktop lesen keine Plugins** – dort Skills einzeln als ZIP unter Customize → Skills → Add hochladen.
- **MCP hinzufügen:** `claude mcp add <name> -- npx ...` oder JSON in `.mcp.json`.

**Eigene Design-Skill – Struktur einer SKILL.md:**
```
---
name: my-design-system
description: Wende unser Design-System an (Tokens, Komponenten, Tailwind-Konventionen). Nutze bei jedem UI-Task.
---
# Design System
## Tokens
- Farben: --brand-primary #..., --bg #..., --accent #... (nie Hex hardcoden, immer Tokens)
- Typografie: Display = "...", Body = "...", Mono = "..."
- Spacing-Skala: 4/8/12/16/24/32
## Komponenten
- Buttons: nutze <Button variant="ghost|outline"> aus components/ui
- Import-Pfade: @/components/ui/...
## Regeln
- Tailwind-Utility-Merge nutzen; dvh statt vh; text-balance für Headlines
- Responsive bis Mobile; sichtbarer Keyboard-Focus; prefers-reduced-motion respektieren
## Verifikation
- Nach Änderung: Screenshot 1280x800 + 375x812, Konsole prüfen
```
Tipp: Mit `skill-creator` iterativ verbessern.

### 4. MCP-Server für UI-Arbeit

**Figma – zwei Wege:**
- **Offizieller Figma Dev Mode MCP Server.** Voraussetzung: ein **bezahlter Full- oder Dev-Seat** (View/Collab-Seats haben Limits). Remote-Variante empfohlen: `claude mcp add --transport http figma-remote-mcp https://mcp.figma.com/mcp`, dann OAuth-Login. Vier Tools: get_code, get_image, get_variable_defs, get_code_connect_map. Link-/Auswahl-basiert; ~20 KB pro Call, daher ein fokussierter Frame statt ganzer Seite. Praxis: gibt Claude echte Variablennamen/Tokens statt Hex-Codes. Bekannte Hürde: 403-Fehler ohne passenden Seat.
- **Framelink / Figma-Context-MCP** (Community, Repo `GLips/Figma-Context-MCP`, **15,7k Stars, MIT-Lizenz**): braucht einen Figma-API-Key. Konfiguration laut README: `npx -y figma-developer-mcp --figma-api-key=YOUR-KEY --stdio`. Vorteil: descriptive JSON, ~25% kleinere Payloads, respektiert Projektkonventionen besser als der offizielle Server. Nachteil: Figma-API-Rate-Limits (Free-Tier aggressiv; 429-Lockouts möglich). Aktuelle Version: v0.13.x (Juni 2026).

**Browser-MCPs (für Screenshots, Verifikation, Debugging):**
- **Chrome DevTools MCP** (empfohlen für die meisten): `claude mcp add chrome-devtools -- npx chrome-devtools-mcp@latest`. Benötigt Node 20.19+. Bestes Diagnose-Tool: Performance, Konsole, Netzwerk, Device-Emulation. Startet eine separate Chrome-Instanz.
- **Playwright MCP** (Microsoft): `claude mcp add playwright -- npx @playwright/mcp@latest`, dazu `npx playwright install`. Cross-Browser (Chromium/Firefox/WebKit), 33+ Tools, Accessibility-Snapshots. Höherer Token-Verbrauch; noch pre-1.0 mit häufigen Breaking Changes. Nur nötig, wenn Cross-Browser gebraucht wird.
- **Claude in Chrome:** für authentifizierte Sessions/schnelle Checks im echten Browser.
- **Empfehlung aus Praxistests (2026):** Chrome DevTools MCP als Basis; Claude in Chrome für Logins; Playwright nur bei Cross-Browser-Bedarf.

**Komponenten-/Registry-MCPs:**
- **shadcn/ui MCP** (offiziell): `.mcp.json`-Eintrag bzw. `claude mcp add shadcn -- npx shadcn@latest mcp`. Browst/sucht/installiert Komponenten aus Registries per natürlicher Sprache; verhindert halluzinierte Props.
- **21st MCP (früher "Magic MCP", 21st.dev):** `npx @21st-dev/cli@latest install claude --api-key ...`. "v0 im Editor": laut 21st.dev/mcp *"search 12,000+ React components and install them without leaving your editor. Formerly known as Magic MCP."* Generiert React+Tailwind+shadcn-Komponenten aus `/ui`-Prompts. **Wichtig:** Laut `21st-dev/magic-mcp`-README: *"The Magic backend (magic.21st.dev) was superseded by the unified 21st MCP, and all old API keys were reset for security."* Nur React (nicht Vue/Svelte). Free-Tier mit Limits, danach kostenpflichtig.

**Storybook-/Design-System-MCPs:** offizielles `@storybook/addon-mcp` (läuft im Dev-Server, für React) bzw. Community-`mcp-design-system-extractor` (verbindet jede deployte Storybook-Instanz). Zweck: Agent nutzt echte, dokumentierte Komponenten statt Neuerfindungen.

**Accessibility/Performance-MCPs:** Lighthouse-MCPs (Core Web Vitals, a11y, SEO) und axe-core-basierte Server (WCAG-Audits mit Selektoren). Deque hat einen offiziellen axe-DevTools-MCP (analyze + remediate; braucht Docker + bezahlte Axe-Lizenz). Für die meisten reicht ein Lighthouse-MCP plus die Vercel-Guidelines-Skill.

**Sicherheit (wichtig bei allen Browser-/Figma-MCPs):** Indirekte **Prompt Injection** ist das Hauptrisiko (OWASP LLM01) – bösartige Seiteninhalte können den Agenten kapern. Konkreter Vorfall/CVE: **CVE-2025-9611, CVSS 7.2 (HIGH), veröffentlicht 7. Jan. 2026** (GitHub Advisory GHSA-8rgw-6xp9-2fg3, Credit: Jonathan Leitschuh): *"Microsoft Playwright MCP Server versions prior to 0.0.40 fails to validate the Origin header on incoming connections … resulting in unintended invocation of MCP tool endpoints."* Dazu RCE-Risiko über `browser_run_code_unsafe`. Gegenmaßnahmen: nur Nicht-Produktions-/Test-Daten, keine Produktions-Credentials, MCP aus CI heraushalten, Output menschlich prüfen, lokale/eng gescopte Konfiguration. Microsoft ist explizit: das Tool ist keine Sicherheitsgrenze – deine Governance ist es.

**Einordnung für Einzelentwickler/Student:**
- **Lohnt sich:** (1) frontend-design-Skill (kostenlos, größter Effekt), (2) ein Browser-MCP (Chrome DevTools MCP), (3) shadcn/ui-MCP wenn shadcn-Stack.
- **Optional/situativ:** Figma-MCP nur bei echtem Figma-Workflow (und passendem Seat); 21st MCP für schnelle Komponentenvarianten.
- **Overkill für Einzelne:** dedizierte visuelle Regressionstests in CI, Enterprise-Accessibility-Agent-Flotten, mehrere parallele Browser-MCPs gleichzeitig (Token-Kosten).

### 5. Tech-Stack & Tooling

- **Bester Fit: React + Tailwind + shadcn/ui.** Anthropic nutzt genau diesen Stack in der web-artifacts-builder-Skill und Claude Design generiert React+Vite+Tailwind+shadcn. Das Tooling-Ökosystem (MCPs, Skills) ist hier am dichtesten. **Next.js** ist ebenfalls stark unterstützt. **Vue/Svelte** funktionieren (shadcn-vue existiert), haben aber weniger fertige UI-Tools.
- **Belastbare Benchmarks fehlen weitgehend** – die Stack-Empfehlung stützt sich auf Anthropics eigene Tooling-Entscheidungen und breite Community-Konvergenz, nicht auf harte Vergleichszahlen. Das sollte man ehrlich so einordnen.
- **.NET/Desktop (Nebenschauplatz):** Claude Code funktioniert dort spürbar schlechter als im Web-Frontend. **Avalonia** hat reagiert: kostenloser "Build MCP" (`claude mcp add --transport http avalonia-docs https://docs-mcp.avaloniaui.net/mcp`) mit Docs, Live-DevTools-Introspektion (Visual Tree lesen, Screenshots), sogar "recreate this app from screenshot"-Workflows. Für **Blazor** gibt es Community-Skills (Blazor Expert, Fluent-UI-Referenz). **WPF/MAUI:** keine etablierten Design-Tools; XAML-Erfahrung ist gemischt – Entwickler berichten, dass LLMs bei Avalonia/XAML öfter hängenbleiben als bei React/Blazor. Fazit: Für polierte UIs bleibt Web-Frontend die stärkste Wahl; im .NET-Desktop-Bereich ist Avalonia+Build-MCP der ausgereifteste KI-Pfad.
- **v0 / Lovable / Claude Design im Vergleich:** v0 (Vercel) = beste UI-Politur für Next.js, gut zum Prototyping vor Integration. Lovable = schnellste Full-Stack-MVP ohne Terminal (React+Vite+Tailwind+shadcn+Supabase), aber Lock-in. Claude Code = arbeitet im echten Repo, jeder Stack, volle Kontrolle. Kombination in der Praxis: in v0/Claude Design/Figma explorieren, dann mit Claude Code sauber ins Repo bauen.

### 6. Praktische Synthese

**Beispiel-Workflow "leere Idee → polierte UI":**
1. **Setup (einmalig):** frontend-design-Skill installieren (`/plugin marketplace add anthropics/skills` → install), Chrome DevTools MCP hinzufügen, `CLAUDE.md` mit Design-Block + shadcn-Konventionen + Screenshot-Regel anlegen.
2. **Exploration/Plan:** Plan Mode. Prompt: *"Wir bauen ein Dashboard für [konkretes Produkt/Zielgruppe]. Committe auf eine BOLD aesthetic direction, erstelle ein Token-System (4–6 Hex-Farben, Display+Body-Font, Spacing-Skala, ein Signature-Element). Zeige mir zuerst den Plan als ASCII-Wireframe, bevor du Code schreibst."*
3. **Build:** *"Implementiere den Plan mit React + Tailwind + shadcn/ui. Nutze CSS-Variablen für alle Tokens, keine Inter/Roboto, ein orchestrierter Page-Load statt verstreuter Animationen."*
4. **Verifikations-Loop:** *"Starte den Dev-Server, öffne die Route mit dem Chrome-DevTools-MCP, mach Screenshots bei 1280x800 und 375x812, prüfe die Konsole. Kritisiere das Ergebnis gegen unseren Plan und behebe Abweichungen. 'Remove one accessory.'"*
5. **Polish/A11y:** *"Führe einen Lighthouse-/axe-Audit aus und behebe WCAG-AA-Verstöße (Kontrast, Fokus, Touch-Targets)."* Optional Vercel-web-design-guidelines-Skill für Code-Review.

**Minimal-Empfehlung (zuerst einrichten):**
- frontend-design-Skill + kompakter `CLAUDE.md`-Designblock + Chrome DevTools MCP für den Screenshot-Loop. Kostenlos, ~15 Minuten, größter Qualitätssprung.

**Maximal-Variante:**
- Zusätzlich: shadcn/ui-MCP+Skill+Preset, Storybook-MCP für ein echtes Design-System, Figma-Dev-Mode-MCP (mit Dev-Seat) oder Framelink, 21st MCP für Komponentenvarianten, Lighthouse+axe-MCP, Vercel-Guidelines-Skill, Writer/Reviewer-Subagent-Muster, Claude Design für Vorab-Exploration.

**Übersichtstabelle (Stand September 2026):**

| Tool | Typ | Zweck | Bezug/Install | Stand/Aktualität |
|---|---|---|---|---|
| frontend-design | Skill (offiziell) | Distinctive UI, Anti-AI-Slop | `anthropics/skills` | 2026 neu geschrieben, 176k Stars, ~862k Installs |
| web-artifacts-builder | Skill (offiziell) | Bessere claude.ai-Artefakte (React/Tailwind/shadcn) | `anthropics/skills` | Aktiv |
| skill-creator | Skill (offiziell) | Eigene Skills bauen | `anthropics/skills` | Aktiv |
| Vercel web-design-guidelines | Skill (Partner) | UI-Code-Review, a11y/UX | `vercel-labs/agent-skills` | 31,2k Stars, aktiv |
| Chrome DevTools MCP | MCP | Screenshots, Perf, Konsole, Netzwerk | `npx chrome-devtools-mcp@latest` | Aktiv, Node 20.19+ |
| Playwright MCP | MCP | Cross-Browser-Tests, Screenshots | `npx @playwright/mcp@latest` | Pre-1.0, häufige Breaking Changes; CVE-2025-9611 vor v0.0.40 |
| shadcn/ui MCP | MCP | Komponenten aus Registry, Live-Docs | `npx shadcn@latest mcp` | Aktiv |
| 21st MCP (ex-Magic) | MCP | UI-Komponentengenerierung (12.000+ React) | `npx @21st-dev/cli@latest install claude` | Umbenannt 2026, alte Keys resettet |
| Figma Dev Mode MCP | MCP (offiziell) | Design-Tokens/Code aus Figma | `claude mcp add --transport http figma-remote-mcp https://mcp.figma.com/mcp` | Braucht Full/Dev-Seat |
| Framelink Figma-Context-MCP | MCP (Community) | Figma→Code, kompakte Payloads | `npx figma-developer-mcp` | 15,7k Stars, v0.13.x (Juni 2026) |
| Storybook MCP | MCP | Design-System-Konsistenz | `@storybook/addon-mcp` | Aktiv |
| Lighthouse/axe MCP | MCP | Performance/Accessibility-Audits | diverse (glama.ai) | Diverse Maintainer |
| Claude Design | Produkt (offiziell) | Prompt→Prototyp, liest Codebase | claude.ai/design | Research Preview seit 17.4.2026, Opus 4.7 |

## Recommendations

**Stufe 1 – sofort (kostenlos, ~15 Min):**
1. frontend-design-Skill installieren (`/plugin marketplace add anthropics/skills`, dann das frontend-design-Plugin installieren).
2. `CLAUDE.md` mit kompaktem Design-Block anlegen (Font-Verbote, Token-Verweis, "keine Default-Tailwind/Inter-Optik", Anti-Overengineering).
3. Chrome DevTools MCP hinzufügen und eine Screenshot-Verifikations-Regel in `CLAUDE.md` schreiben.
Benchmark für Weitergehen: Wenn deine UIs immer noch "templated" wirken oder Claude Props halluziniert → Stufe 2.

**Stufe 2 – wenn du regelmäßig mit einem Komponenten-System arbeitest:**
4. shadcn/ui-Stack + MCP + Skill + Preset einrichten (Tokens zentralisieren).
5. Bei echtem Design-System: Storybook-MCP mit der "never hallucinate props"-Regel.
6. Writer/Reviewer-Subagent-Muster für Review mit frischem Kontext.
Benchmark: Wenn du aus Figma-Designs baust → Stufe 3.

**Stufe 3 – Design-Handoff & Qualitätssicherung:**
7. Figma: mit Dev-Seat den offiziellen Dev-Mode-MCP, sonst Framelink (API-Key, Rate-Limits beachten).
8. Lighthouse/axe-MCP + Vercel-Guidelines-Skill für Accessibility/Performance-Gates.
9. Claude Design für schnelle Vorab-Exploration von Richtungen.

**Sicherheits-Baseline (immer):** Browser-/Figma-MCPs nur mit Test-Daten, ohne Produktions-Credentials, nicht in CI, Output prüfen. Prompt-Injection ernst nehmen.

**Was ich NICHT empfehle** für einen Einzelentwickler/Studenten: mehrere Browser-MCPs parallel, Enterprise-Accessibility-Agent-Flotten, oder das blinde Installieren großer Skill-Sammlungen (Kontext-Bloat, ungeprüfte Qualität).

## Caveats

- **Hohe Änderungsrate.** Fast alle genannten Tools sind 2025/2026 entstanden und ändern sich monatlich. Konkrete Beispiele veralteter Stände: "Magic MCP" → "21st MCP" mit Key-Reset; Playwright MCP weiterhin pre-1.0; Figma-MCP-Anforderungen (Seat-Pflicht) haben sich verschärft. Prüfe vor Nutzung immer README/Release-Datum.
- **Marketplace-Aggregatoren ≠ Originalquellen.** Seiten wie mcpmarket.com, claudemarketplaces.com, claudedirectory.org listen Skills/MCPs teils mit übertriebenen Superlativen. Verifiziere am GitHub-Original (Stars, letztes Commit, offene Issues).
- **Star-Zahlen schwanken/cachen unterschiedlich.** Die Werte hier (z.B. anthropics/skills 176k, vercel-labs/agent-skills 31,2k, Framelink 15,7k) sind Direktabrufe von September 2026; behandle sie als Größenordnung, nicht als exakte Konstante. GitHub-Seiten zeigten während der Recherche teils unterschiedliche gecachte Werte (z.B. anthropics/skills 168,9k–176k).
- **Keine belastbaren Stack-Benchmarks.** Die Aussage "React+Tailwind+shadcn funktioniert am besten" beruht auf Tooling-Dichte und Anthropics eigenen Entscheidungen, nicht auf kontrollierten Messungen.
- **CLAUDE.md ist keine harte Regel.** Anthropics Doku stellt klar: Inhalt wird als Kontext behandelt, nicht erzwungen. Für garantierte Regeln braucht man Hooks/CI-Checks.
- **Community-Anekdoten vs. Doku.** Screenshot-Loops, "v0-Screenshot als Anker", Karpathy-inspirierte Regeln etc. sind Community-Empfehlungen mit guter Resonanz, aber ohne offizielle Garantie – klar von der offiziell dokumentierten frontend-design-Skill und dem Blogpost zu unterscheiden.
- **Kosten.** Claude Code wird nach Nutzung/Abo abgerechnet; intensive Iterations-/Screenshot-Loops verbrauchen Tokens. Einige MCPs (21st ab Free-Limit, Deque axe, shadcn.io Pro) sind kostenpflichtig.