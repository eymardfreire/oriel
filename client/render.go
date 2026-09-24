package main

import (
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
)

func renderBay(bay Bay, panels []Panel, theme Theme, width int) string {
	if width < 40 {
		width = 80
	}
	if len(panels) == 0 {
		panels = []Panel{{
			Domain: domainForBay(bay.ID),
			Title:  bay.Title,
		}}
	}
	dense := bay.Layout == "dense"
	inner := contentWidth(bay.Layout, len(panels), width)
	blocks := make([]string, len(panels))
	for i, panel := range panels {
		blocks[i] = panelBox(panelBody(panel, theme), theme, inner, dense)
	}
	switch bay.Layout {
	case "strip", "dense":
		return lipgloss.JoinHorizontal(lipgloss.Top, blocks...)
	case "split":
		if len(blocks) < 2 {
			return blocks[0]
		}
		mid := (len(blocks) + 1) / 2
		left := lipgloss.JoinVertical(lipgloss.Left, blocks[:mid]...)
		right := lipgloss.JoinVertical(lipgloss.Left, blocks[mid:]...)
		return lipgloss.JoinHorizontal(lipgloss.Top, left, right)
	default:
		return lipgloss.JoinVertical(lipgloss.Left, blocks...)
	}
}

func domainForBay(id string) string {
	switch id {
	case "storm":
		return "weather"
	case "field", "far", "fantasy":
		return "sports"
	default:
		return id
	}
}

func contentWidth(layout string, count, total int) int {
	if count < 1 {
		count = 1
	}
	cols := 1
	switch layout {
	case "strip", "dense":
		cols = count
	case "split":
		if count > 1 {
			cols = 2
		}
	}
	width := total/cols - 2
	if width < 16 {
		width = 16
	}
	return width
}

func panelBox(body string, theme Theme, width int, dense bool) string {
	pad := 1
	if dense {
		pad = 0
	}
	return lipgloss.NewStyle().
		Width(width).
		Border(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color(theme.Roles["border"])).
		Foreground(lipgloss.Color(theme.Roles["text"])).
		Background(lipgloss.Color(theme.Roles["surface"])).
		Padding(0, pad).
		Render(body)
}

func panelBody(panel Panel, theme Theme) string {
	lines := []string{headerLine(panel, theme)}
	if len(panel.Items) == 0 {
		lines = append(lines, fg(theme, "muted").Render(panel.Domain+" has no items"))
	}
	for _, item := range panel.Items {
		lines = append(lines, renderItem(item, theme))
	}
	return strings.Join(lines, "\n")
}

func headerLine(panel Panel, theme Theme) string {
	parts := []string{fg(theme, "text").Render(panel.Title)}
	if panel.Fixture {
		parts = append(parts, fg(theme, "muted").Render("fixture"))
	}
	if panel.Stale {
		marker := "stale"
		if panel.StaleReason != "" {
			marker += " " + panel.StaleReason
		}
		parts = append(parts, fg(theme, "stale").Render(marker))
	}
	return strings.Join(parts, "  ")
}

func renderItem(item Item, theme Theme) string {
	switch item.Row {
	case "quote":
		return renderQuote(item, theme)
	case "headline":
		return renderHeadline(item, theme)
	case "score":
		return renderScore(item, theme)
	case "alert":
		return renderAlert(item, theme)
	case "clock":
		return renderClock(item, theme)
	case "fantasy":
		return renderFantasy(item, theme)
	case "observation":
		return renderObservation(item, theme)
	case "forecast":
		return renderForecast(item, theme)
	default:
		return renderHeadline(item, theme)
	}
}

func renderHeadline(item Item, theme Theme) string {
	desk, _ := item.Fields["desk"].(string)
	title := fg(theme, "text").Render(item.Title)
	meta := metaLine([]string{desk, item.Source, formatObserved(item.ObservedAt)}, theme)
	return title + "\n" + meta
}

func renderQuote(item Item, theme Theme) string {
	symbol, _ := item.Fields["symbol"].(string)
	if symbol == "" {
		symbol = item.Title
	}
	line := fg(theme, "text").Render(symbol)
	if raw, ok := item.Fields["price"]; ok && raw != nil {
		if price, ok := asFloat(raw); ok {
			line += "  " + fg(theme, "text").Render(trimFloat(price))
		}
	}
	if change, role := formatChange(item.Fields); change != "" {
		line += "  " + fg(theme, role).Render(change)
	}
	if delayed, _ := item.Fields["delayed"].(bool); delayed {
		line += "  " + fg(theme, "muted").Render("delayed")
	}
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt)}, theme)
}

func renderScore(item Item, theme Theme) string {
	home, _ := item.Fields["home"].(string)
	away, _ := item.Fields["away"].(string)
	score, _ := item.Fields["score"].(string)
	state, _ := item.Fields["state"].(string)
	tier, _ := item.Fields["tier"].(string)
	excerpt, _ := item.Fields["excerpt"].(string)
	factualLine, _ := item.Fields["factual_line"].(string)
	text := fg(theme, "text")
	if excerpt != "" {
		quoted := text.Render("\"" + excerpt + "\"")
		return quoted + "\n" + metaLine([]string{item.Source}, theme)
	}
	line := text.Render(home)
	if score != "" {
		line += "  " + text.Render(score)
	}
	if away != "" {
		line += "  " + text.Render(away)
	}
	tail := []string{state, item.Source}
	if tier == "delayed" {
		tail = append([]string{"delayed"}, tail...)
	}
	if factual, _ := item.Fields["factual"].(bool); factual {
		tail = append(tail, "factual line")
	}
	if factualLine != "" {
		line += "\n" + text.Render(factualLine)
	}
	return line + "\n" + metaLine(tail, theme)
}

func renderObservation(item Item, theme Theme) string {
	place, _ := item.Fields["place"].(string)
	condition, _ := item.Fields["condition"].(string)
	text := fg(theme, "text")
	var detail []string
	if raw, ok := item.Fields["temperature_c"]; ok && raw != nil {
		if temp, ok := asFloat(raw); ok {
			detail = append(detail, trimFloat(temp)+"°C")
		}
	}
	if condition != "" {
		detail = append(detail, condition)
	}
	body := text.Render(place)
	if len(detail) > 0 {
		body += "\n" + text.Render(strings.Join(detail, "  "))
	}
	return body + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt)}, theme)
}

func renderForecast(item Item, theme Theme) string {
	place, _ := item.Fields["place"].(string)
	period, _ := item.Fields["period"].(string)
	condition, _ := item.Fields["condition"].(string)
	text := fg(theme, "text")
	line := text.Render(place)
	if period != "" {
		line += "  " + text.Render(period)
	}
	var temps []string
	if raw, ok := item.Fields["temperature_high_c"]; ok && raw != nil {
		if high, ok := asFloat(raw); ok {
			temps = append(temps, trimFloat(high)+"°C")
		}
	}
	if raw, ok := item.Fields["temperature_low_c"]; ok && raw != nil {
		if low, ok := asFloat(raw); ok {
			temps = append(temps, trimFloat(low)+"°C")
		}
	}
	if len(temps) > 0 || condition != "" {
		detail := strings.Join(temps, " ")
		if condition != "" {
			if detail != "" {
				detail += "  "
			}
			detail += condition
		}
		line += "\n" + text.Render(detail)
	}
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt)}, theme)
}

func renderFantasy(item Item, theme Theme) string {
	player, _ := item.Fields["player"].(string)
	if player == "" {
		player = item.Title
	}
	position, _ := item.Fields["position"].(string)
	team, _ := item.Fields["team"].(string)
	slot, _ := item.Fields["slot"].(string)
	var bits []string
	if slot != "" {
		bits = append(bits, slot)
	}
	if player != "" {
		bits = append(bits, player)
	}
	if position != "" && position != slot {
		bits = append(bits, position)
	}
	if team != "" {
		bits = append(bits, team)
	}
	line := fg(theme, "text").Render(strings.Join(bits, "  "))
	if pinned, _ := item.Fields["pinned"].(bool); pinned {
		line += "  " + fg(theme, "accent").Render("pin")
	}
	if raw, ok := item.Fields["points"]; ok && raw != nil {
		if points, ok := asFloat(raw); ok {
			line += "  " + fg(theme, "text").Render(trimFloat(points))
		}
	}
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt)}, theme)
}

func renderAlert(item Item, theme Theme) string {
	severity, _ := item.Fields["severity"].(string)
	headline, _ := item.Fields["headline"].(string)
	if headline == "" {
		headline = item.Title
	}
	role := "warn"
	switch strings.ToLower(severity) {
	case "severe", "extreme":
		role = "down"
	}
	line := ""
	if severity != "" {
		line = fg(theme, role).Render(severity) + "  "
	}
	line += fg(theme, "text").Render(headline)
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt)}, theme)
}

func renderClock(item Item, theme Theme) string {
	when, _ := item.Fields["time"].(string)
	if when == "" {
		when = item.Title
	}
	return fg(theme, "text").Render(when)
}

func formatChange(fields map[string]any) (string, string) {
	raw, ok := fields["change"]
	if !ok || raw == nil {
		return "", "muted"
	}
	change, ok := asFloat(raw)
	if !ok {
		return "", "muted"
	}
	if change > 0 {
		return "+" + trimFloat(change), "up"
	}
	if change < 0 {
		return trimFloat(change), "down"
	}
	return "0", "muted"
}

func metaLine(parts []string, theme Theme) string {
	shown := make([]string, 0, len(parts))
	for _, part := range parts {
		if part != "" {
			shown = append(shown, part)
		}
	}
	return fg(theme, "muted").Render(strings.Join(shown, " · "))
}

func fg(theme Theme, role string) lipgloss.Style {
	return lipgloss.NewStyle().Foreground(lipgloss.Color(theme.Roles[role]))
}

func asFloat(value any) (float64, bool) {
	switch n := value.(type) {
	case float64:
		return n, true
	case int:
		return float64(n), true
	default:
		return 0, false
	}
}

func trimFloat(value float64) string {
	return strconv.FormatFloat(value, 'f', -1, 64)
}

func formatObserved(raw string) string {
	parsed, err := time.Parse(time.RFC3339, raw)
	if err != nil {
		return raw
	}
	return parsed.UTC().Format("2006-01-02 15:04 UTC")
}
