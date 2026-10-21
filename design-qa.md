# Ticket workspace design review — 2026-10-21

final result: passed

This result covers the requested local redesign and the states below. It is not
a release approval: the deliberately restored exercise bugs still fail the
correctness suite. This report supersedes the earlier mock implementation review.

## Visual targets and evidence

- Original art direction: `output/design/support-workspace-v3.png` (1485×1059).
  The user authorized a complete redesign. Keep its graphite queue, warm paper,
  citrine accent, and absent logo/wordmark; change density and mobile behavior.
- Starting implementation: `output/design/iterations/00-before-desktop.png`
  (1440×960 CSS view) and `00-before-default.jpg` (619×615).
- Final implementation: `http://localhost:5173/`, compiled Vite preview with the
  existing FastAPI service at port 8000. T-101 selected, original B1 seed content,
  no unsaved changes. No backend or API changes in this iteration.
- Final unscaled screenshots at approved 100% preview zoom:
  `output/design/iterations/04-final-desktop.jpg` (1440×960),
  `04-final-mobile-detail.jpg` and `04-final-mobile-queue.jpg` (390×844),
  `04-final-320-keyboard.jpg` (320×844). Pixel dimensions equal CSS viewport
  dimensions; the viewport override reports devicePixelRatio 1.
- Full-view comparison: `output/design/iterations/desktop-before-after.png`
  (2880×960, baseline left, final right). Target/current composition:
  `mock-and-final.png`; the original mock is scaled proportionally to fit the
  left panel, so this is an art-direction comparison, not a pixel-difference test.
- Focused comparison: `output/design/iterations/editor-before-after.png`
  (2000×550). Crops preserve internal scale and show field affordances, metadata,
  typography and action proximity. Mobile baseline/current comparison:
  `mobile-native-before-after.png` (1238×615).

### Capture normalization and rejected evidence

Initial IAB viewport overrides combined with 140% zoom downscaled app pixels into
the upper-left portion of the screenshot. Original `*-raw.jpg` files are retained.
For the starting desktop image and provisional iteration images, uniformly scale
the raw image by 1.4 and crop to the CSS viewport. For example, the 1440×960 raw
image is resized to 2016×1344 and cropped from (0,0) to (1440,960). The normalized
queue width and header height match recorded DOM bounds; no UI elements, colors,
or content were edited. These images support geometry, not fine antialiasing.

The original 390px baseline capture was truncated to 390×260 and is excluded from
visual acceptance. Its DOM measurements remain supporting evidence only. The
619px native baseline/current images are a matched mobile comparison. The user
later approved resetting zoom; all `04-final-*` screenshots are direct browser
captures requiring no normalization. Final typography was checked in these clear
captures. The active preview's viewport override was reset afterward. The second
preview tab retains its 2016×1344 test viewport: the browser reset operates on the
selected tab, and the available APIs did not expose selecting that tab for reset.
Both tabs were refreshed to the final build at 100% zoom.

## Findings and iteration history

| Finding | Evidence and impact | Resolution |
| --- | --- | --- |
| P1: Mobile queue competes with editing | At 390×844 the old queue occupied y87–450 and Save began at y1111. The editing task required scrolling past a separate scrolling queue. | One visible pane at a time, Back/Return navigation, a single queue scroll area. Final Save is y681–725 for T-101 at 390×844. |
| P1: Switching tickets discards edits | Editor-local state was lost on keyed remount. The new draft regression failed before implementation. | Per-ticket draft map retains all three fields. Cancel/save clear only that ticket; show Unsaved changes while values differ from saved data. |
| P2: Excess scale and distant actions | Large title/rows and bottom-pushed Save weakened scanning and separated the task from its action. | 56px global header, 320px desktop queue, content-driven rows, 27px desktop title, bounded 760px form, actions 20px below Description. |
| P2: Editing affordances unclear | Title and status resembled display text; read-only metadata shared the editing presentation. | Explicit bordered title/status controls; read-only Priority/Requester/Created use a definition list. |
| P2: Mobile skip/focus regressions | First mobile redesign linked to a hidden main pane; navigation focused Title; resize could hide focused queue controls. | Skip target follows visible pane. Explicit mobile navigation focuses Back. Focus moves when its control becomes hidden. Three new tests were red before repair. |
| P2: Stale focus request steals focus | After desktop navigation, focusing Description then narrowing moved focus back to Title. The added regression reproduced this. | Focus requests have action-specific identity; resizing alone does not replay an old request. Regression passes. |
| P2: Tiny secondary labels | Iteration 1 retained 9–10px labels/indicators. | Iteration 2 raises those to 11px; task text remains 15–16px and readonly values 13px. |

1. **Implementation/review 1:** Critic and implementer discussed density, edit
   affordances, action placement, mobile scrolling and draft loss. Compact layout,
   whole mobile panes and per-ticket drafts were implemented. Ten workspace cases
   passed; build passed. Initial screenshots were provisional due to capture scaling.
2. **Implementation/review 2:** Both agents discussed visible-pane skip targets,
   mobile reading focus, resize repair, minimum label size and unsaved feedback.
   Three focus/navigation regressions plus the unsaved indicator failed before
   their changes; fourteen cases then passed. Build passed.
3. **Focused follow-up:** Critic identified the stale focus-request case in source
   review; parent reproduced it with fourteen passes/one failure. Repair
   produced fifteen passes. Both agents inspected full and focused desktop/mobile
   images and found no remaining P1/P2 issue in those states.
4. **Final verification:** Added reverse-breakpoint coverage suggested by the test
   scout. It already passed via the existing queue-focus effect, so no production
   fix was needed. Final suite has sixteen passing workspace cases. Clear final
   captures replaced provisional handoff images after the approved zoom reset.

## Required visual surfaces

- **Typography:** Self-hosted Geist and Geist Mono retained. Final direct captures
  show readable form hierarchy and natural queue/title wrapping. Secondary labels
  use 11px; task text uses 15–16px; title is 27px desktop/24px mobile. The large
  display-title treatment in the mock is intentionally reduced for daily editing.
- **Spacing/layout:** Compact queue, consistent section gaps, bounded form, nearby
  actions and subtle 4px control radii. Desktop retains useful breathing room;
  mobile uses the full working width. No horizontal overflow at 320px or 390px.
- **Color/tokens:** Graphite #242a27, paper #f7f8f3, citrine #e0ee9d. Selected queue
  item has background and border cues. Control border #89938a against input fill
  #fdfef9 is approximately 3.14:1; readonly label #697460 against paper is 4.61:1.
  This is a bounded review, not a claim of complete WCAG conformance.
- **Assets:** Existing self-hosted fonts and Phosphor vector icon package retained;
  no decorative raster substitutions, invented logo or prompt text. No added
  imagery is needed for a ticket-editing workspace.
- **Copy/content:** Real API ticket content retained; labels are concise. Priority,
  requester and date remain read-only. “Unknown” for in_progress and inaccurate
  summaries are deliberate exercise exceptions, not newly introduced UI failures.

## Behavior and checks observed

- Browser: desktop 1440×960, mobile 390×844, 320×844, and native pane 619×615.
  T-101 draft survives Next/Previous and Back/queue selection; Cancel restores
  original values without PUT. Keyboard Tab reaches T-102 in the queue and Enter
  opens it with focus on Back. At 320px, a long draft title expands vertically
  inside a 280px field without horizontal page overflow. Temporary draft cancelled.
- New tests cover independent drafts, visible mobile panes, pending-save locking,
  save/cancel focus, skip targets, both resize directions, retained visible-field
  focus and unsaved feedback. Existing exact PUT payload/retry assertions remain.
- `npm test`: **27 passed / 19 failed**; all **16 workspace tests pass**. The failed
  test-name set exactly matches the starting 18-pass/19-failure exercise baseline.
  No assertion was weakened to accommodate planted bugs.
- `npm run build`: passed. `git diff --check`: passed. Final browser error/warning
  log query returned no entries. Detailed red/green counts are recorded in
  `output/design/iterations/verification.json`.
- Backend checks and remote GitLab CI were not run for this frontend-only change.
  Existing deliberately failing backend tests remain outside this change.
- Local evidence gate passed with `BASE_REF=HEAD CHECK_WORKTREE=1` and
  `EVIDENCE_FILE=/private/tmp/support-redesign-quality-evidence.txt`. It checks
  tracked-file presence across the dirty tree, omits new untracked source files,
  and does not establish behavioral correctness or authorize release.

## Remaining limits and implementation checklist

- [x] Both design agents discussed and reviewed multiple implementation rounds.
- [x] Fix the captured P1/P2 redesign findings and verify the regression cases.
- [x] Capture final desktop/mobile/keyboard states at 100%; reset active viewport.
- [x] Preserve deliberate demo bugs, API contracts and removed branding.
- [x] Record bug-log evidence and local checks for human review.

Physical-device software-keyboard behavior, assistive technology, other browser
engines and remote CI remain unverified. Drafts are in-memory and do not survive
page reloads; persistent drafts were not requested. Human review decides whether
to merge or release; the exercise baseline is intentionally not release-green.
