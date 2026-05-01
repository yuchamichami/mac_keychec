# KeyCheck UI Redesign — Handoff Bundle

Synth/DJ-deck aesthetic for the existing macOS KeyCheck app.
**Functional behavior, layout structure, and operation flow are preserved** — this is a visual-only redesign that maps cleanly to SwiftUI.

## Contents

### PNG renders (paste-ready)
| File | Dimensions | Purpose |
|---|---|---|
| `main_window_1600x1000.png` | 1600×1000 | Main window full mockup (1x) |
| `main_window_1600x1000_2x.png` | 3200×2000 | Retina version |
| `component_states_1200x1080.png` | 1200×1080 | Knob / Power / Keycap / Event Row states |
| `component_states_1200x1080_2x.png` | 2400×2160 | Retina version |
| `tokens_1200x520.png` | 1200×520 | Color token chips |
| `tokens_1200x520_2x.png` | 2400×1040 | Retina version |

### Editable SVG sources
| File | Notes |
|---|---|
| `main_window.svg` | Vectorized mockup — open in Figma/Illustrator/Affinity to edit |
| `component_states.svg` | Component states tile |
| `tokens.svg` | Tokens tile |

> SVGs embed CSS styling via `<foreignObject>`. They're true vector but each gradient/shadow is preserved. You can re-export PNGs at any size from these.

### Design tokens (for SwiftUI)
| File | Notes |
|---|---|
| `tokens.json` | All colors, radii, spacing, sizes, shadows, animations as structured JSON. SwiftUI snippets are inline in the `swiftui:` keys for select colors. |

### Source (re-render and tweak)
| File | Notes |
|---|---|
| `source/keycheck-ui.css` | The full stylesheet used for the renders |
| `source/keycheck-ui.jsx` | React components: `MainWindow`, `ComponentStates`, `TokensTile`, plus `Knob`, `PowerButton`, `Keycap`, `EventRow` |

---

## What changed visually (vs. screenshot in the request)

| Before | After |
|---|---|
| iOS-style toggle for Sound | **Push-style power button** with green LED dot |
| Horizontal volume slider | **Rotary knob** (84px) with cyan LED arc, peak region (>100%) shifts to orange/red |
| Plain segmented control | **Mechanical keycap row** — selected = white squircle top with cyan glow |
| Plain Test/Copy/Clear | **Keycap-style buttons** (matching aesthetic) |
| Flat list rows | **4px glowing accent bar** on left (green=down, orange=up), JSON syntax-highlighted code, `⇧`/`⌘` glyph chips, `PAGE`/`USAGE` capped labels |
| Flat black background | Subtle radial+linear gradient `#171347 → #0B1030`, noise texture, slow CRT scanline |
| Standard title bar | Transparent title bar — content extends to top |

Layout, control order, and event semantics are **unchanged**.

---

## SwiftUI implementation guide

### 1. Drop tokens into a Color extension

```swift
extension Color {
    static let bgWindow      = Color(red: 0.043, green: 0.063, blue: 0.188) // #0B1030
    static let bgWindowGrad  = Color(red: 0.090, green: 0.075, blue: 0.278) // #171347
    static let bgCard        = Color(red: 0.055, green: 0.059, blue: 0.141) // #0E0F24
    static let accentCyan    = Color(red: 0.357, green: 0.820, blue: 1.000) // #5BD1FF
    static let accentCyan2   = Color(red: 0.180, green: 0.545, blue: 1.000) // #2E8BFF
    static let downGreen     = Color(red: 0.357, green: 1.000, blue: 0.545) // #5BFF8B
    static let upOrange      = Color(red: 1.000, green: 0.659, blue: 0.357) // #FFA85B
    static let peakRed       = Color(red: 1.000, green: 0.373, blue: 0.373) // #FF5F5F
    static let textPrimary   = Color(red: 0.925, green: 0.933, blue: 1.000) // #ECEEFF
    static let textSecondary = Color(red: 0.490, green: 0.502, blue: 0.565) // #7D8090
}
```

### 2. Window chrome

```swift
WindowGroup {
    ContentView()
}
.windowStyle(.hiddenTitleBar)
.windowToolbarStyle(.unifiedCompact)
```

In ContentView root: `.background(LinearGradient(...))` + `.frame(minWidth: 1000)`.

### 3. Volume knob

Custom `Canvas` view. Draw two arcs:
- background arc: `Path` from -135° to +135°, stroke 3pt with `Color.white.opacity(0.06)`
- lit arc: linear-gradient stroke from `accentCyan2` → `accentCyan`, split at 100% angle
- when `value > 100`, draw a second arc from the 100% angle to current with `upOrange` → `peakRed` gradient
- center: `Circle` filled with `RadialGradient(colors:[#545766, #2C2E3A, #15161E])` + inset shadow
- indicator: `Capsule` 2×14, rotated by `value/150 × 270° - 135°`, anchor at center

`DragGesture()` with onChanged updating value via angle change.

### 4. Power button

ZStack:
- 56pt circle, radial gradient `#4B4F5E → #2A2C38 → #15161E`
- inner shadow (use `.shadow(color: .white.opacity(0.15), radius:0, y:1)` ring trick)
- power glyph centered (open circle + vertical bar)
- 6pt LED circle near top: `downGreen` w/ `.shadow(color:.downGreen, radius:5)` when on

### 5. Keycap

Conditional foreground based on `selected`:
- default: `LinearGradient(top:#20222E → bottom:#15161E)` + inset top highlight
- selected: `LinearGradient(top:#FCFCFE → bottom:#D2D2DE)` + cyan border `Color.accentCyan.opacity(0.5)` + outer glow

`RoundedRectangle(cornerRadius: 6)` with explicit 88×48 (tone) or 76×48 (action).

### 6. Event row

`HStack(spacing:0)`:
- 4pt `Rectangle` filled `downGreen`/`upOrange`, with `.shadow(radius:8, color: same)` for glow
- 22pt `Text("down"/"up")` weight `.light`
- `VStack` for code + meta
- right `Grid` for PAGE/USAGE

`.background(Color.accentCyan.opacity(hover ? 0.04 : 0))`

### 7. Animations

| Transition | Duration | Curve |
|---|---|---|
| Knob rotation | 100ms | easeOut |
| Button press scale | 80ms | easeOut, scale 0.96 |
| New row flash | 200ms | easeOut on accent bar opacity |
| Scanline | 6000ms | linear, looping (Timer-driven `offsetY`) |

---

## Constraints honored

- ✅ No pixel-rasterized assets needed (all vector + CSS gradients translate to SwiftUI)
- ✅ No Lottie / 3D / WebGL
- ✅ No web-only fonts — JetBrains Mono is OFL and bundles into the .app
- ✅ Existing event store / sound player / NSEvent monitor untouched

---

## Re-rendering at different sizes

If you need different output sizes or to tweak colors, edit `source/keycheck-ui.css` (CSS variables at the top), then either:
- Open the project's `KeyCheck UI Redesign.html` and screenshot, or
- Re-run the rasterizer (the project has the script that produced these PNGs)
