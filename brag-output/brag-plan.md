# Creative Plan & Storyboard: RepoPeek Launch Video

## Primary Objective
Sell the outcome, not the implementation.
Your AI can write code. RepoPeek helps it understand your codebase.

## Audience & Positioning
- **Target Audience:** Developers, AI-assisted builders, indie hackers, engineering teams, and power users of Claude Code, Cursor, Windsurf, GitHub Copilot, and Antigravity.
- **Narrative Arc:**
  1. *Recognition (0–5s):* "My AI coding assistant really does waste context and miss dependencies."
  2. *Discovery (5–13s):* "RepoPeek gives it an interactive map of my codebase."
  3. *Desire (13–18s):* "I want this in my development workflow."
  4. *Brand (18–20s):* "Give your AI a map."
- **Tone:** `polished` / `cinematic` — modern developer-tool launch aesthetic, restrained coral-red accents, crisp dark mode, authoritative yet founder-warm.
- **Duration:** 20.0 seconds (600 frames at 30 fps)
- **Format:** 16:9 Landscape (1920x1080), Progressive YUV420p H.264 + AAC Stereo
- **Voice:** Neural warm male (`en-US-AndrewNeural`), founder-like, conversational, confident.
- **Music & Sound:** 120 BPM Fm electronic synth groove with responsive audio ducking, mechanical keystroke ticks, transition risers, crystal AST chimes, radar pings, and sub-bass impact.

---

## Complete Voiceover Script (45 Words)

| Scene | Timestamp | Voiceover Line | Words |
|---|---|---|---|
| **Scene 1** | 0.5s – 4.3s | *"Your AI can write code. But does it really understand your codebase?"* | 12 |
| **Scene 2** | 4.9s – 11.8s | *"RepoPeek gives your assistant a map, finding only relevant code and showing what changes affect before you edit."* | 18 |
| **Scene 3** | 12.3s – 16.8s | *"Less wasted context, safer refactors, and your code stays local."* | 10 |
| **Scene 4** | 17.2s – 19.1s | *"Give your AI a map."* | 5 |
| **Total** | **20.0s** | | **45 words** |

---

## Visual Direction & Color Tokens
- **Canvas / Background:** Deep near-black `#08090e` with subtle drifting cyber-grid `#10121b`.
- **Primary Surface:** Charcoal glassmorphic card `#0f111a` with 2px stroke `#21263a`.
- **Brand Accent:** Restrained coral-red `#ff4d6d` / `#ff3366` for impact radar, warnings, and brand tagline.
- **Semantic AST Tokens:**
  - Modules: Cyan `#38bdf8`
  - Classes: Purple `#a855f7`
  - Functions: Emerald `#10b981`
  - Data / Config: Amber `#f59e0b`
- **Typography:** Segoe UI Bold / Segoe UI (Headings), Consolas / Consolas Bold (Code & Metrics).
- **Poster Frame:** Frame 555 (18.5s settled brand lockup) baked as Frame 0 of `brag.mp4` and saved to `brag.jpg`.

---

## Scene-by-Scene Storyboard (20.0s Total)

### Scene 1: The Pain (0.0s – 4.8s | Frames 0 – 144)
- **Visual:** Terminal window in an 18,400-file monorepo. The user prompts the AI to refactor session timeout. The AI blindly reads multiple 2,000+ line files. A large context meter surges to 22,633 tokens in glowing coral-red. A downstream dependency alert flashes warning that 4 callers are about to break.
- **Kinetic Text:** `"Your AI can write code. But does it understand your codebase?"`
- **Audio:** Keystrokes, low tension drone, subtle alert tone, audio transition riser.
- **Narration:** *"Your AI can write code. But does it really understand your codebase?"*

### Scene 2: The Transformation & Map (4.8s – 12.2s | Frames 144 – 366)
- **Visual:** Smooth radial transition from chaos into RepoPeek's luminous dependency graph.
  - *Phase 1 (Bloom):* Multi-language relational graph blossoms outward.
  - *Phase 2 (Surgical Retrieval):* Unrelated nodes dim; camera isolates the exact 40-line AST slice for `touch_session()`. Floating HUD card highlights `~1,200 tokens (vs 22,633 raw)`.
  - *Phase 3 (Blast Radius Radar):* Glowing coral-red radar wave ripples outward, flagging downstream callers (`on_session_expiry`, `audit_sync`) before editing.
- **Kinetic Text:** `"REPOPEEK CODEBASE MAP — Surgical AST isolation + pre-edit blast radius radar"`
- **Audio:** Synth arpeggio drops in, crystal AST chime, radar ping.
- **Narration:** *"RepoPeek gives your assistant a map, finding only relevant code and showing what changes affect before you edit."*

### Scene 3: The Payoff (12.2s – 17.0s | Frames 366 – 510)
- **Visual:** Three glassmorphic value cards side-by-side:
  1. **Less Wasted Context:** `82.5% Context Reduction` (verified on 3-defect benchmark: 22,633 tokens down to 3,966 tokens).
  2. **Safer Code Changes:** `Pre-Edit Blast Radius Radar` (catches downstream breaks before commit).
  3. **Your Code Stays Local:** `100% Local-First Privacy` (NetworkX & SQLite WAL on your machine, sub-50ms sync, zero cloud SaaS).
- **Audio:** Energetic electronic beat with punchy kick drum and clap.
- **Narration:** *"Less wasted context, safer refactors, and your code stays local."*

### Scene 4: Closing Brand & Outro (17.0s – 20.0s | Frames 510 – 600)
- **Visual:** Symmetrical hero card with glowing RepoPeek radar logo, bold white typography, coral tagline `"Give your AI a map."`, and call-to-action button:
  - CTA: `Explore RepoPeek on GitHub`
  - URL: `github.com/pratiyush-DA/repopeek`
  - Trust Badges: `36+ Languages · 264 Passing Tests · Sub-50ms Sync · 100% Local-First`
- **Audio:** Resonant synth chord swell resolving to clean silence.
- **Narration:** *"Give your AI a map."*

---

## Product Facts & Verification Guardrails
- **Core Identity:** Intelligent code navigation and safety radar for AI coding assistants.
- **3-Defect Benchmark:** 82.5% context reduction (22,633 tokens without RepoPeek down to 3,966 with RepoPeek).
- **Suite Benchmark:** 17.7% net savings across all benchmark tasks.
- **Incremental Sync:** Sub-50ms incremental graph updates via background watch daemon.
- **Test Suite:** 264 passing unit and integration tests.
- **Privacy:** 100% local execution, zero third-party graph database, zero cloud egress.
