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
	parts := []string{"j/k rows", "← →", "enter select", "p pause", "t theme"}
	if board {
		parts = []string{"h home", "j/k rows", "← →", "enter select", "p pause"}
	}
	if refine != "" {
		parts = append(parts, refine)
	}
	parts = append(parts, "? guide", "q quit")
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

func guidePageCount(board bool) int {
	if board {
		return 3
	}
	return 2
}

func guideRoom(height int) int {
	room := height - 6
	if room < 8 {
		room = 8
	}
	return room
}

func guideLines(page int, board bool, bays []string, enabled map[string]bool, cursor int) []string {
	pages := guidePageCount(board)
	if page < 0 || page >= pages {
		page = 0
	}
	title := fmt.Sprintf("Guide  %d/%d", page+1, pages)
	switch page {
	case 1:
		return append([]string{title, "What each bay is, and where you set it up.", ""}, bayGuideLines()...)
	case 2:
		return boardGuideLines(title, bays, enabled, cursor)
	default:
		return keyGuideLines(title, board)
	}
}

func keyGuideLines(title string, board bool) []string {
	lines := []string{
		title,
		"How to move, and every key.",
		"",
		"j moves to the bay below. k moves to the bay above.",
		"Left and right move across the row.",
		"enter opens that bay's list, when it has one. f does the same.",
		"In a list, j and k move, a number jumps to a row, and enter selects it.",
		"",
		"p pauses paging. t cycles the theme.",
	}
	if board {
		lines = append(lines,
			"h restores wires, markets, storm, and trade.",
			"s, then a digit, saves this board. A digit loads that slot.",
			"[ and ] cycle the slots that already have a board saved.",
			"",
			"A suggestion on the status line names another desk.",
			"a swaps this board for that desk. It replaces the bays you are looking at,",
			"so it stays off this bar. enter does not swap the board.",
		)
	}
	return lines
}

func bayGuideLines() []string {
	return []string{
		"Trade. Freight, customs, and the supply chain.",
		"The families live in catalog/trade. There is no list in the client.",
		"",
		"Wires. Headlines from the shipped outlets.",
		"Each outlet is a file in catalog/outlets. enabled keeps or drops it.",
		"",
		"Storm. Watched cities, alerts, and weather news.",
		"Places are catalog/weather/places.json.",
		"Home is Tampa, in server/config.toml.",
		"",
		"Markets. Quotes, family by family.",
		"The symbols are catalog/markets/selection.json.",
		"",
		"Field. Scores for the competitions you follow.",
		"enter or f opens the list. j and k move. enter follows or drops the row.",
		"",
		"Sideline. Sports news.",
		"With nothing chosen, the newest headline from each sport.",
		"enter or f picks which sports stay.",
		"",
		"Brief. One place, one headline, and one quote.",
		"With nothing chosen: Tampa, the first live headline, the first live quote.",
		"enter or f picks those three. A place you pick is not marked home.",
		"",
		"Far Desk. This is not another follow list.",
		"Field is the slate you follow. A live or delayed score shows when a source has one.",
		"Far Desk is a league that only has a public result or a schedule.",
		"A line is a fact from that source, and the source is named. Nothing is added.",
		"You do not pick it from here. The two on it are 3. Liga and the Nippon Baseball League.",
		"",
		"Fantasy. An NFL roster: pins, then the lineup, then the bench.",
		"The roster is catalog/sports/roster.json. There is no key for it yet.",
	}
}

func boardGuideLines(title string, bays []string, enabled map[string]bool, cursor int) []string {
	lines := []string{
		title,
		"This board. j and k move. A number jumps. enter shows or hides.",
		"",
	}
	if len(bays) == 0 {
		lines = append(lines, "No shipped bay is available.")
		return lines
	}
	if cursor < 0 || cursor >= len(bays) {
		cursor = 0
	}
	for i, id := range bays {
		state := "hidden"
		if enabled[id] {
			state = "shown"
		}
		mark := " "
		if i == cursor {
			mark = ">"
		}
		lines = append(lines, fmt.Sprintf("%s %d  %-12s %s", mark, i+1, bayGuideTitle(id), state))
	}
	return lines
}

func bayGuideTitle(id string) string {
	switch id {
	case "brief":
		return "Brief"
	case "fantasy":
		return "Fantasy"
	case "far":
		return "Far Desk"
	case "field":
		return "Field"
	case "markets":
		return "Markets"
	case "sideline":
		return "Sideline"
	case "storm":
		return "Storm"
	case "trade":
		return "Trade"
	case "wires":
		return "Wires"
	default:
		if id == "" {
			return id
		}
		return strings.ToUpper(id[:1]) + id[1:]
	}
}

func guideView(theme Theme, page int, board bool, bays []string, enabled map[string]bool, cursor, scroll, width, height int) string {
	raw := guideLines(page, board, bays, enabled, cursor)
	if height > 1 {
		room := guideRoom(height) - 1
		if room < 1 {
			room = 1
		}
		if scroll < 0 {
			scroll = 0
		}
		if scroll > len(raw)-room && len(raw) > room {
			scroll = len(raw) - room
		}
		if scroll < 0 {
			scroll = 0
		}
		end := scroll + room
		if end > len(raw) {
			end = len(raw)
		}
		if scroll < len(raw) {
			raw = raw[scroll:end]
		}
	}
	lines := make([]string, 0, len(raw)+1)
	for i, line := range raw {
		role := "text"
		if i == 0 {
			role = "accent"
		}
		lines = append(lines, fg(theme, role).Render(line))
	}
	lines = append(lines, fg(theme, "muted").Render("← → pages    ? closes    q quits"))
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
	return number - 1, confirm, true
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
