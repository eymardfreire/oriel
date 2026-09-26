## 1. Pass 1: `f` follows the focused bay (handoff gate)

- [x] 1.1 Open the field list only when field is focused, and the sideline list only when sideline is focused
- [x] 1.2 Name the action in the status hint (`f follows`, `f sports`, `f brief`), and omit `f` when the focused bay has no list
- [x] 1.3 Pressing `f` on a bay with no list leaves every list closed and says that bay has nothing to choose
- [x] 1.4 Client tests for field, sideline, brief, and far focus

## 2. Pass 2: Brief selection (handoff gate)

- [x] 2.1 Add `catalog/brief/selection.json` with empty place, outlet, and family
- [x] 2.2 Add `POST /bays/brief/selection`, reject an unknown id, and leave the file unchanged on rejection
- [x] 2.3 Brief overlay lists places, enabled outlets, and market families; enter selects one per section, and the empty id restores that section's default
- [x] 2.4 Apply the selection when composing brief: home, first headline, and first quote when unset; keep the previous row when the chosen source has nothing; leave a missing price blank
- [x] 2.5 Tests for a chosen place, a rejected outlet, and a family with no price

## 3. Pass 3: Far sources (handoff gate)

- [x] 3.1 Check a few public far-tier result, schedule, or report sources live
- [x] 3.2 Add a competition only when the existing sports fetcher can read a fact from it, with the check date in the catalog and the README
- [x] 3.3 Leave the catalog unchanged when none answer, so the bay still says no far-coverage competition is configured

## 4. Pass 4: Sweep (handoff gate)

- [x] 4.1 Record in the handoff which bays still have no in-client choice: fantasy roster and pins, market instruments, trade families, wire outlets, and storm places
- [x] 4.2 Do not add pickers for those bays
