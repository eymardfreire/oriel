package main

import (
	"encoding/json"
	"os"
	"path/filepath"
)

var defaultBoardBays = []string{"wires", "markets", "storm", "trade"}

type boardLayout struct {
	Bays  []string `json:"bays,omitempty"`
	Theme string   `json:"theme,omitempty"`
}

type boardPrefs struct {
	Theme   string        `json:"theme"`
	Bays    []string      `json:"bays"`
	Layouts []boardLayout `json:"layouts,omitempty"`
	Slot    int           `json:"slot,omitempty"`
}

func prefsPath(root string) string {
	return filepath.Join(root, "client", "state", "board.json")
}

func loadBoardPrefs(root string) boardPrefs {
	prefs := boardPrefs{Theme: defaultTheme, Bays: append([]string(nil), defaultBoardBays...), Layouts: ensureHomeSlot(nil)}
	data, err := os.ReadFile(prefsPath(root))
	if err != nil {
		return prefs
	}
	var saved boardPrefs
	if json.Unmarshal(data, &saved) != nil {
		return prefs
	}
	if saved.Theme != "" {
		prefs.Theme = saved.Theme
	}
	if len(saved.Bays) > 0 {
		prefs.Bays = saved.Bays
	}
	prefs.Layouts = ensureHomeSlot(normalizeLayouts(saved.Layouts))
	if saved.Slot >= 1 && saved.Slot <= 9 {
		prefs.Slot = saved.Slot
	}
	return prefs
}

func normalizeLayouts(layouts []boardLayout) []boardLayout {
	out := make([]boardLayout, 9)
	for i := 0; i < len(layouts) && i < 9; i++ {
		out[i].Theme = layouts[i].Theme
		if len(layouts[i].Bays) > 0 {
			out[i].Bays = append([]string(nil), layouts[i].Bays...)
		}
	}
	return out
}

func ensureHomeSlot(layouts []boardLayout) []boardLayout {
	layouts = normalizeLayouts(layouts)
	for _, layout := range layouts {
		if len(layout.Bays) > 0 {
			return layouts
		}
	}
	return saveLayout(layouts, 1, defaultBoardBays, defaultTheme)
}

func saveLayout(layouts []boardLayout, slot int, bays []string, theme string) []boardLayout {
	layouts = normalizeLayouts(layouts)
	if slot < 1 || slot > 9 {
		return layouts
	}
	layouts[slot-1] = boardLayout{Bays: append([]string(nil), bays...), Theme: theme}
	return layouts
}

func layoutAt(layouts []boardLayout, slot int) (boardLayout, bool) {
	layouts = normalizeLayouts(layouts)
	if slot < 1 || slot > 9 || len(layouts[slot-1].Bays) == 0 {
		return boardLayout{}, false
	}
	return layouts[slot-1], true
}

func cycleSlot(layouts []boardLayout, slot, dir int) int {
	layouts = normalizeLayouts(layouts)
	if dir >= 0 {
		dir = 1
	} else {
		dir = -1
	}
	start := slot - 1
	if slot == 0 && dir < 0 {
		start = 0
	}
	if slot == 0 && dir > 0 {
		start = -1
	}
	for step := 1; step <= 9; step++ {
		index := start + dir*step
		index = ((index % 9) + 9) % 9
		if len(layouts[index].Bays) > 0 {
			return index + 1
		}
	}
	return 0
}

func saveBoardPrefs(root string, prefs boardPrefs) {
	path := prefsPath(root)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	data, err := json.MarshalIndent(prefs, "", "  ")
	if err != nil {
		return
	}
	_ = os.WriteFile(path, data, 0o644)
}

func selectedSet(ids []string) map[string]bool {
	set := map[string]bool{}
	for _, id := range ids {
		set[id] = true
	}
	return set
}
