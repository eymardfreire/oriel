package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

func statusLine(now time.Time, title, mark string, suggestion Suggestion, theme Theme, slot int, notice string, board bool, refine string) string {
	clock := "--:--:--"
	if !now.IsZero() {
		clock = now.Format("15:04:05")
	}
	parts := []string{
		fg(theme, "accent").Render(clock),
		fg(theme, "text").Render(title),
	}
	if mark != "" {
		parts = append(parts, fg(theme, "accent").Render(mark))
	}
	if line := suggestionLine(suggestion); line != "" {
		parts = append(parts, fg(theme, "text").Render(line))
	}
	if slot > 0 {
		parts = append(parts, fg(theme, "accent").Render(fmt.Sprintf("slot %d", slot)))
	}
	if notice != "" {
		parts = append(parts, fg(theme, "text").Render(notice))
	}
	parts = append(parts, fg(theme, "muted").Render(statusHints(board, refine)))
	return strings.Join(parts, "  ")
}

func statusHints(board bool, refine string) string {
	parts := []string{"j/k focus", "p pause", "t theme"}
	if board {
		parts = []string{"h home", "j/k focus", "p pause", "s# save", "# load", "[ ] slots", "t theme"}
	}
	if refine != "" {
		parts = append(parts, refine)
	}
	parts = append(parts, "? settings", "a apply", "q quit")
	return strings.Join(parts, "   ")
}

func refineHint(bayID string) string {
	switch bayID {
	case "field":
		return "f follows"
	case "sideline":
		return "f sports"
	case "brief":
		return "f brief"
	default:
		return ""
	}
}

func settingsView(theme Theme, themeIDs []string, bays []string, enabled map[string]bool, board bool, width int) string {
	lines := []string{
		fg(theme, "accent").Render("Settings"),
		fg(theme, "text").Render("Theme  " + theme.ID + "    t cycles the shipped themes for this window"),
	}
	if board {
		lines = append(lines, fg(theme, "text").Render("Bays    a number toggles that bay on this board"))
		for i, id := range bays {
			state := "hidden"
			if enabled[id] {
				state = "shown"
			}
			lines = append(lines, fg(theme, "text").Render(fmt.Sprintf("%d  %-10s %s", i+1, id, state)))
		}
	}
	lines = append(lines, fg(theme, "muted").Render("? closes    q quits"))
	body := strings.Join(lines, "\n")
	if width < 40 {
		width = 80
	}
	return lipgloss.NewStyle().
		Width(width-2).
		Border(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color(theme.Roles["accent"])).
		Background(lipgloss.Color(theme.Roles["surface"])).
		Padding(1, 2).
		Render(body)
}

type followChoice struct {
	ID       string
	Name     string
	Followed bool
	Slot     string
}

type pickerStyle struct {
	Empty   string
	On      string
	Off     string
	Footer  string
	Pending string
}

func fieldPickerStyle() pickerStyle {
	return pickerStyle{
		Empty:   "No shipped competition is available",
		On:      "following",
		Off:     "not followed",
		Footer:  "j/k move    enter toggles    f closes    q quits",
		Pending: "enter toggles",
	}
}

func briefPickerStyle() pickerStyle {
	return pickerStyle{
		Empty:   "No brief choice is available",
		On:      "selected",
		Off:     "open",
		Footer:  "j/k move    enter selects    f closes    q quits",
		Pending: "enter selects",
	}
}

func followPick(buffer string, count int, confirm bool) (index int, ready bool, valid bool) {
	if buffer == "" || count < 1 {
		return 0, false, false
	}
	number, err := strconv.Atoi(buffer)
	if err != nil || number < 1 || number > count {
		return 0, false, false
	}
	if confirm || len(buffer) >= 2 || number*10 > count {
		return number - 1, true, true
	}
	return number - 1, false, true
}

func followsView(theme Theme, title, hint string, choices []followChoice, pending string, cursor, width int, style pickerStyle) string {
	lines := []string{
		fg(theme, "accent").Render(title),
		fg(theme, "text").Render(hint),
	}
	if pending != "" {
		lines = append(lines, fg(theme, "warn").Render("number "+pending+"  "+style.Pending))
	}
	if len(choices) == 0 {
		lines = append(lines, fg(theme, "muted").Render(style.Empty))
	}
	if cursor < 0 || cursor >= len(choices) {
		cursor = 0
	}
	for i, choice := range choices {
		state := style.Off
		if choice.Followed {
			state = style.On
		}
		mark := " "
		if i == cursor {
			mark = ">"
		}
		lines = append(lines, fg(theme, "text").Render(fmt.Sprintf("%s %2d  %-28s %s", mark, i+1, choice.Name, state)))
	}
	lines = append(lines, fg(theme, "muted").Render(style.Footer))
	body := strings.Join(lines, "\n")
	if width < 40 {
		width = 80
	}
	return lipgloss.NewStyle().
		Width(width-2).
		Border(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color(theme.Roles["accent"])).
		Background(lipgloss.Color(theme.Roles["surface"])).
		Padding(1, 2).
		Render(body)
}

func nextTheme(ids []string, current string) string {
	if len(ids) == 0 {
		return defaultTheme
	}
	sorted := append([]string(nil), ids...)
	sort.Strings(sorted)
	for i, id := range sorted {
		if id == current {
			return sorted[(i+1)%len(sorted)]
		}
	}
	return sorted[0]
}
