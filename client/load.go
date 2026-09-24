package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const (
	defaultTheme = "night"
	defaultBay   = "brief"
)

var themeRoles = []string{
	"bg", "surface", "border", "text", "muted", "accent",
	"up", "down", "warn", "info", "stale",
}

type Theme struct {
	ID    string            `json:"id"`
	Mode  string            `json:"mode"`
	Roles map[string]string `json:"roles"`
}

type Bay struct {
	ID             string   `json:"id"`
	Title          string   `json:"title"`
	Theme          string   `json:"theme"`
	Layout         string   `json:"layout"`
	Panels         []string `json:"panels"`
	RefreshSeconds int      `json:"refresh_seconds"`
}

type Desk struct {
	ID    string    `json:"id"`
	Title string    `json:"title"`
	Bays  []DeskBay `json:"bays"`
}

type DeskBay struct {
	ID   string `json:"id"`
	Role string `json:"role"`
}

type Panel struct {
	ID          string `json:"id"`
	Domain      string `json:"domain"`
	Title       string `json:"title"`
	UpdatedAt   string `json:"updated_at"`
	Stale       bool   `json:"stale"`
	StaleReason string `json:"stale_reason"`
	Fixture     bool   `json:"fixture"`
	Items       []Item `json:"items"`
}

type Item struct {
	ID         string         `json:"id"`
	Title      string         `json:"title"`
	Source     string         `json:"source"`
	SourceURL  string         `json:"source_url"`
	ObservedAt string         `json:"observed_at"`
	Row        string         `json:"row"`
	Fields     map[string]any `json:"fields"`
}

func findRoot(start string) (string, error) {
	dir, err := filepath.Abs(start)
	if err != nil {
		return "", err
	}
	for {
		if isDir(filepath.Join(dir, "catalog", "themes")) && isDir(filepath.Join(dir, "fixtures")) {
			return dir, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("oriel root not found from %s", start)
		}
		dir = parent
	}
}

func isDir(path string) bool {
	info, err := os.Stat(path)
	return err == nil && info.IsDir()
}

func loadTheme(root, id string) (Theme, error) {
	var theme Theme
	path := filepath.Join(root, "catalog", "themes", id+".json")
	if err := readJSON(path, &theme); err != nil {
		return Theme{}, fmt.Errorf("unknown theme %q", id)
	}
	if theme.ID != id {
		return Theme{}, fmt.Errorf("theme file %s has id %q", path, theme.ID)
	}
	if theme.Mode != "dark" && theme.Mode != "light" {
		return Theme{}, fmt.Errorf("theme %q has unknown mode %q", id, theme.Mode)
	}
	for _, role := range themeRoles {
		if !isHex(theme.Roles[role]) {
			return Theme{}, fmt.Errorf("theme %q is missing role %s", id, role)
		}
	}
	return theme, nil
}

func loadBay(root, id string) (Bay, error) {
	var bay Bay
	path := filepath.Join(root, "catalog", "bays", id+".json")
	if err := readJSON(path, &bay); err != nil {
		return Bay{}, err
	}
	if bay.ID != id {
		return Bay{}, fmt.Errorf("bay file %s has id %q", path, bay.ID)
	}
	return bay, nil
}

func loadDesk(root, id string) (Desk, error) {
	var desk Desk
	path := filepath.Join(root, "catalog", "desks", id+".json")
	if err := readJSON(path, &desk); err != nil {
		return Desk{}, err
	}
	if desk.ID != id {
		return Desk{}, fmt.Errorf("desk file %s has id %q", path, desk.ID)
	}
	return desk, nil
}

func loadPanel(root, id string) (Panel, error) {
	var panel Panel
	path := filepath.Join(root, "fixtures", id+".json")
	if err := readJSON(path, &panel); err != nil {
		return Panel{}, err
	}
	return panel, nil
}

func openBay(root, bayID, themeFlag string) (Bay, Theme, []Panel, error) {
	bay, err := loadBay(root, bayID)
	if err != nil {
		if _, deskErr := loadDesk(root, bayID); deskErr == nil {
			return Bay{}, Theme{}, nil, fmt.Errorf("%q is a desk, not a bay; this client opens one bay", bayID)
		}
		ids, listErr := listIDs(filepath.Join(root, "catalog", "bays"))
		if listErr != nil {
			return Bay{}, Theme{}, nil, fmt.Errorf("unknown bay %q", bayID)
		}
		return Bay{}, Theme{}, nil, fmt.Errorf("unknown bay %q (bays: %s)", bayID, strings.Join(ids, ", "))
	}
	theme, err := loadTheme(root, resolveTheme(themeFlag, bay.Theme))
	if err != nil {
		return Bay{}, Theme{}, nil, err
	}
	panels := make([]Panel, 0, len(bay.Panels))
	for _, id := range bay.Panels {
		panel, err := loadPanel(root, id)
		if err != nil {
			return Bay{}, Theme{}, nil, fmt.Errorf("panel %s: %w", id, err)
		}
		panels = append(panels, panel)
	}
	return bay, theme, panels, nil
}

func resolveTheme(flagTheme, bayTheme string) string {
	if flagTheme != "" {
		return flagTheme
	}
	if bayTheme != "" {
		return bayTheme
	}
	return defaultTheme
}

func readJSON(path string, dest any) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(data, dest); err != nil {
		return fmt.Errorf("%s: %w", path, err)
	}
	return nil
}

func listIDs(dir string) ([]string, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, err
	}
	ids := make([]string, 0, len(entries))
	for _, entry := range entries {
		name := entry.Name()
		if entry.IsDir() || !strings.HasSuffix(name, ".json") {
			continue
		}
		ids = append(ids, strings.TrimSuffix(name, ".json"))
	}
	return ids, nil
}

func isHex(value string) bool {
	if len(value) != 7 || value[0] != '#' {
		return false
	}
	for _, r := range value[1:] {
		switch {
		case r >= '0' && r <= '9', r >= 'a' && r <= 'f', r >= 'A' && r <= 'F':
		default:
			return false
		}
	}
	return true
}
