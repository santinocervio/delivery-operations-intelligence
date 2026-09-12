# Design truth — Delivery Operations Intelligence

The single brand source for every composition in this project. Compositions read
these tokens; they do not invent colour, type or spacing.

## Concept angle

**Evidence under pressure.** The film is a control room that keeps its nerve: a huge
operation, an obvious explanation, and an analyst who tests that explanation and throws
it away before proposing anything. Motion is measured and mechanical — nothing bounces,
nothing celebrates. The one moment of visual violence is reserved for the rejection beat.

## Palette

Near-black tinted warm (never `#000`), one accent hue in the PedidosYa red-magenta family,
one steel neutral reserved for "the reference / the thing we compared against".

| Token            | Value     | Role                                                        |
| ---------------- | --------- | ----------------------------------------------------------- |
| `--bg`           | `#0C0A0B` | canvas, every scene, never changes                          |
| `--bg-raise`     | `#141011` | raised panels, KPI cards, chart plots                        |
| `--rule`         | `#241C1E` | hairlines, grid, card borders                               |
| `--fg`           | `#F5F1F2` | primary type                                                |
| `--muted`        | `#8A8084` | labels, units, source citations (AA: 5.1:1)                 |
| `--accent`       | `#FF2D55` | the finding, the bottleneck, the focus mark (AA: 5.4:1)     |
| `--accent-deep`  | `#B3123A` | accent shadow / bar bases, decorative only                  |
| `--steel`        | `#7A8794` | the comparison series, the rejected path (AA: 5.3:1)        |

Accent is **scarce**: at most one accent-coloured element carries meaning per frame.
Everything else is fg / muted / steel. Charts use accent for the subject and steel for the
reference — no third series colour anywhere in the film.

## Typography

Two voices in deliberate disagreement — the claim and the evidence.

- **Archivo Black, 400 only** — statements, scene headlines, the title lockup. Loud,
  editorial, human. Tracking `-0.035em` at display sizes. Never request 700/900.
- **IBM Plex Mono, 400 / 700** — every number, axis label, unit, cohort size, source
  citation and body line. Precise, machine, tabular. Tabular figures keep count-ups from
  jittering, which is why the hero numerals are mono rather than display.

The tension is the content's own: a bold operational claim set against measurements that
refuse to overstate themselves. One expressive face (Archivo Black) performs; the mono
recedes and carries proof.

Sizes (1920×1080, full-screen web embed):

| Role              | Size  | Face / weight          |
| ----------------- | ----- | ---------------------- |
| Title lockup      | 132px | Archivo Black          |
| Scene headline    | 76px  | Archivo Black          |
| Hero numeral      | 116px | IBM Plex Mono 700      |
| KPI numeral       | 62px  | IBM Plex Mono 700      |
| Body / statement  | 30px  | IBM Plex Mono 400      |
| Data label        | 22px  | IBM Plex Mono 400      |
| Source citation   | 17px  | IBM Plex Mono 400, `--muted`, uppercase, `0.12em` tracking |

Minimum on-screen text is 17px and it is used only for source citations, which are
persistent rather than read-once.

## Layout

A 12-column grid on a 1920×1080 canvas: 120px side margins, 64px gutters, 88px top and
bottom safe margins. Every scene anchors to one of three shapes:

1. **Full-bleed statement** — headline centred on the optical third, one supporting line.
2. **Left rail / right plot** — claim on columns 1–4, chart on columns 5–12.
3. **Command grid** — 2×3 or 1×4 KPI cards on the raised surface.

A persistent 80px hairline grid at 4% opacity sits under every scene, plus a slow
accent-tinted radial at the frame's lower left. These two carry the ambient breath; they
never reset between scenes, so cuts read as camera moves inside one continuous space.

## Motion

- Entrances 0.36–0.6s. Eases: `power3.out` for arrivals, `power2.inOut` for camera moves,
  `expo.out` for the rejection slam only.
- Count-ups run 0.9–1.4s on `power2.out` and land on the exact published value.
- Bars and lines draw from their measured length; nothing scales from zero opacity alone.
- Ambient: the grid drifts 8px over the full film, the radial breathes on a 9s cycle.
- **No bounce, no elastic, no confetti.** The single permitted "hit" is the rejection
  stamp in Scene 4.

## Persistent chrome

A 17px mono strip sits bottom-left on every data scene naming the source table, and a
bottom-right frame counter reading `SCENE n / 8`. The chrome never animates out; it
updates in place. This is the film's credibility signature — every claim on screen names
the file it came from.

## Bans

No gradient text, no glow text, no 3D, no stock photography, no icon soup, no drop shadows
on type, no cyan, no purple. No logo reconstruction: the PedidosYa wordmark and official
typeface are not in the repository and are not recreated here.
