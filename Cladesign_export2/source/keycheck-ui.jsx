/* global React */
const { useState } = React;

// ============================================================
// Helpers
// ============================================================
const SAMPLE_EVENTS = [
  { dir: "up",   key: "s", flags: null,                 page: 7, pageHex: "0x0007", usage: 22,  usageHex: "0x0016", chars: "s", code: 1 },
  { dir: "down", key: "d", flags: null,                 page: 7, pageHex: "0x0007", usage: 7,   usageHex: "0x0007", chars: "d", code: 2 },
  { dir: "up",   key: "d", flags: null,                 page: 7, pageHex: "0x0007", usage: 7,   usageHex: "0x0007", chars: "d", code: 2 },
  { dir: "down", key: "s", flags: null,                 page: 7, pageHex: "0x0007", usage: 22,  usageHex: "0x0016", chars: "s", code: 1 },
  { dir: "up",   key: "s", flags: null,                 page: 7, pageHex: "0x0007", usage: 22,  usageHex: "0x0016", chars: "s", code: 1 },
  { dir: "down", key: "d", flags: null,                 page: 7, pageHex: "0x0007", usage: 7,   usageHex: "0x0007", chars: "d", code: 2 },
  { dir: "up",   key: "d", flags: null,                 page: 7, pageHex: "0x0007", usage: 7,   usageHex: "0x0007", chars: "d", code: 2 },
  { dir: "down", pointing: "button1",                   page: 9, pageHex: "0x0009", usage: 1,   usageHex: "0x0001" },
  { dir: "up",   pointing: "button1",                   page: 9, pageHex: "0x0009", usage: 1,   usageHex: "0x0001" },
  { dir: "down", key: "left_shift",   flags: ["shift"],                  page: 7, pageHex: "0x0007", usage: 225, usageHex: "0x00e1" },
  { dir: "down", key: "left_command", flags: ["shift", "command"],       page: 7, pageHex: "0x0007", usage: 227, usageHex: "0x00e3" },
  { dir: "down", key: "a", flags: ["shift", "command"], page: 7, pageHex: "0x0007", usage: 4,   usageHex: "0x0004", chars: "A", code: 0 },
];

const FLAG_GLYPHS = { shift: "⇧", command: "⌘", control: "⌃", option: "⌥" };

function formatCodeHTML(ev) {
  if (ev.pointing) {
    return (
      <span className="row__code">
        <span className="punct">{"{"}</span>
        <span className="key">"pointing_button"</span>
        <span className="punct">:</span>
        <span className="str">"{ev.pointing}"</span>
        <span className="punct">{"}"}</span>
      </span>
    );
  }
  return (
    <span className="row__code">
      <span className="punct">{"{"}</span>
      <span className="key">"key_code"</span>
      <span className="punct">:</span>
      <span className="str">"{ev.key}"</span>
      <span className="punct">{"}"}</span>
    </span>
  );
}

// ============================================================
// Knob (volume rotary)
// value 0..150
// ============================================================
function Knob({ value = 75, size = 84, label = true }) {
  // sweep arc range: -135deg to +135deg
  const min = -135, max = 135;
  const range = max - min; // 270
  const ratio = Math.max(0, Math.min(1, value / 150));
  const angle = min + ratio * range;

  // peak threshold at 100%
  const ratioCold = Math.min(value, 100) / 150;
  const ratioHot  = Math.max(0, value - 100) / 150;

  const r = size / 2 - 4;
  const cx = size / 2, cy = size / 2;

  // build arc paths
  function polar(cx, cy, r, deg) {
    const rad = (deg - 90) * Math.PI / 180;
    return [cx + r * Math.cos(rad), cy + r * Math.sin(rad)];
  }
  function arcPath(startDeg, endDeg, r) {
    const [sx, sy] = polar(cx, cy, r, startDeg);
    const [ex, ey] = polar(cx, cy, r, endDeg);
    const large = Math.abs(endDeg - startDeg) > 180 ? 1 : 0;
    return `M ${sx} ${sy} A ${r} ${r} 0 ${large} 1 ${ex} ${ey}`;
  }

  // arc from min to angle, split at 100% point
  const arcMaxColdDeg = min + (100 / 150) * range; // angle at 100%
  const litEndCold = Math.min(angle, arcMaxColdDeg);
  const litEndHot  = angle > arcMaxColdDeg ? angle : null;

  return (
    <div className="knob" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ position: "absolute", inset: 0 }}>
        {/* background arc */}
        <path d={arcPath(min, max, r)} stroke="rgba(255,255,255,0.06)" strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* lit arc (cyan) */}
        {litEndCold > min && (
          <path d={arcPath(min, litEndCold, r)} stroke="url(#knobGradCold)" strokeWidth="3" fill="none" strokeLinecap="round" filter="url(#knobGlow)" />
        )}
        {/* lit arc (peak orange/red) */}
        {litEndHot !== null && (
          <path d={arcPath(arcMaxColdDeg, litEndHot, r)} stroke="url(#knobGradHot)" strokeWidth="3" fill="none" strokeLinecap="round" filter="url(#knobGlow)" />
        )}
        <defs>
          <linearGradient id="knobGradCold" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#2e8bff" />
            <stop offset="100%" stopColor="#5bd1ff" />
          </linearGradient>
          <linearGradient id="knobGradHot" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#ffa85b" />
            <stop offset="100%" stopColor="#ff5f5f" />
          </linearGradient>
          <filter id="knobGlow"><feGaussianBlur stdDeviation="1.5" /></filter>
        </defs>
      </svg>
      <div className="knob__dial" />
      <div className="knob__brush" />
      <div className="knob__indicator" style={{ transform: `translateX(-50%) rotate(${angle}deg)` }} />
    </div>
  );
}

// ============================================================
// Sound power button
// ============================================================
function PowerButton({ on = true, pressed = false }) {
  return (
    <div className={"power__btn" + (on ? "" : " off") + (pressed ? " pressed" : "")}>
      <div className="power__icon" />
    </div>
  );
}

// ============================================================
// Keycap button
// ============================================================
function Keycap({ label, on = false, hover = false, width, children, style }) {
  let cls = "kcap";
  if (on) cls += " on";
  if (hover) cls += " hover";
  return (
    <div className={cls} style={{ width, ...(style || {}) }}>
      {children || label}
    </div>
  );
}

// ============================================================
// Event row
// ============================================================
function EventRow({ ev }) {
  return (
    <div className={"row " + ev.dir}>
      <div className="row__bar" />
      <div className="row__dir">{ev.dir}</div>
      <div className="row__main">
        {formatCodeHTML(ev)}
        {ev.flags && (
          <span className="row__meta">
            <span style={{ color: "#7d8090", letterSpacing: 1 }}>flags</span>
            {ev.flags.map(f => (
              <span key={f} style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
                <span className="glyph">{FLAG_GLYPHS[f] || "·"}</span>
                <span>{f}</span>
              </span>
            ))}
          </span>
        )}
        {ev.chars !== undefined && !ev.flags && (
          <span className="row__meta">
            <span>chars: <span style={{ color: "#ffd58a" }}>"{ev.chars}"</span></span>
            <span>code: <span style={{ color: "#eceeff" }}>{ev.code}</span></span>
          </span>
        )}
      </div>
      <div className="row__usage">
        <span className="lbl">PAGE</span>
        <span>{ev.page} ({ev.pageHex})</span>
        <span className="lbl">USAGE</span>
        <span>{ev.usage} ({ev.usageHex})</span>
      </div>
    </div>
  );
}

// ============================================================
// Main window (1600×1000)
// ============================================================
function MainWindow() {
  const [volume] = useState(112);
  const [tone] = useState("Click");
  const [soundOn] = useState(true);

  return (
    <div className="app">
      <div className="titlebar">
        <div className="tl-dots">
          <div className="tl-dot r" />
          <div className="tl-dot y" />
          <div className="tl-dot g" />
        </div>
        <div className="tl-title">KEYCHECK</div>
        <div style={{ width: 54 }} />
      </div>

      <div className="bar">
        {/* Sound power */}
        <div className="power">
          <span className="power__label">Sound</span>
          <PowerButton on={soundOn} />
        </div>

        {/* Tone segmented */}
        <div className="tones">
          {["Click", "Beep", "Pop", "Tick"].map(t => (
            <Keycap key={t} label={t} on={t === tone} />
          ))}
        </div>

        {/* Volume knob */}
        <div className="vol">
          <span className="vol__label">Vol</span>
          <Knob value={volume} />
          <span className="knob__val">{volume}%</span>
        </div>

        {/* Action buttons */}
        <div className="actions">
          <Keycap label="Test" />
          <Keycap label="Copy" />
          <Keycap label="Clear" />
        </div>
      </div>

      <div className="sec">
        <div className="sec__h">Keyboard &amp; pointing events</div>
        <div className="sec__count">
          <span className="num">{SAMPLE_EVENTS.length}</span> events
        </div>
      </div>
      <div className="divider" />

      <div className="log">
        {SAMPLE_EVENTS.map((ev, i) => <EventRow key={i} ev={ev} />)}
      </div>
    </div>
  );
}

// ============================================================
// Component states tile (1200 wide)
// ============================================================
function ComponentStates() {
  return (
    <div className="swatch-grid">
      <div className="tile">
        <h3>Volume Knob</h3>
        <div className="tile-row">
          <div className="state"><Knob value={0}   /><div className="state-label">0%</div></div>
          <div className="state"><Knob value={45}  /><div className="state-label">45%</div></div>
          <div className="state"><Knob value={75}  /><div className="state-label">75%</div></div>
          <div className="state"><Knob value={100} /><div className="state-label">100%</div></div>
          <div className="state"><Knob value={130} /><div className="state-label">130% peak</div></div>
          <div className="state"><Knob value={150} /><div className="state-label">150% max</div></div>
        </div>
      </div>

      <div className="tile">
        <h3>Power Button (Sound)</h3>
        <div className="tile-row" style={{ gap: 56 }}>
          <div className="state"><PowerButton on={true}  /><div className="state-label">On</div></div>
          <div className="state"><PowerButton on={false} /><div className="state-label">Off</div></div>
          <div className="state"><PowerButton on={true} pressed /><div className="state-label">Pressed</div></div>
        </div>
      </div>

      <div className="tile" style={{ gridColumn: "1 / -1" }}>
        <h3>Keycap Button — Tone Selector</h3>
        <div className="tile-row" style={{ gap: 24 }}>
          <div className="state"><Keycap label="Click" /><div className="state-label">Default</div></div>
          <div className="state"><Keycap label="Click" hover /><div className="state-label">Hover</div></div>
          <div className="state"><Keycap label="Click" on /><div className="state-label">Selected</div></div>
          <div style={{ width: 24 }} />
          <div className="state"><Keycap label="Test" width={76} /><div className="state-label">Action default</div></div>
          <div className="state"><Keycap label="Test" width={76} hover /><div className="state-label">Action hover</div></div>
        </div>
      </div>

      <div className="tile" style={{ gridColumn: "1 / -1" }}>
        <h3>Event Row</h3>
        <div className="row-demo">
          <EventRow ev={SAMPLE_EVENTS[1]} />
          <EventRow ev={SAMPLE_EVENTS[10]} />
          <EventRow ev={SAMPLE_EVENTS[7]} />
        </div>
      </div>
    </div>
  );
}

// ============================================================
// Design tokens
// ============================================================
function TokensTile() {
  const colors = [
    ["bg-window",      "#0B1030"],
    ["bg-window-grad", "#171347"],
    ["bg-card",        "#0E0F24"],
    ["bg-card-hover",  "#131428"],
    ["accent-cyan",    "#5BD1FF"],
    ["accent-cyan-2",  "#2E8BFF"],
    ["down-green",     "#5BFF8B"],
    ["up-orange",      "#FFA85B"],
    ["peak-red",       "#FF5F5F"],
    ["text-primary",   "#ECEEFF"],
    ["text-secondary", "#7D8090"],
    ["divider",        "rgba(255,255,255,0.04)"],
  ];
  return (
    <div className="tokens">
      <h2>Design Tokens</h2>
      <div className="tok-grid">
        {colors.map(([name, val]) => (
          <div className="tok" key={name}>
            <div className="tok__chip" style={{ background: val }} />
            <div className="tok__name">{name}</div>
            <div className="tok__val">{val}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { MainWindow, ComponentStates, TokensTile });
