package main

import (
	"fmt"
	"math"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/x/ansi"
)

func renderBay(bay Bay, panels []Panel, theme Theme, width int) string {
	return renderFrame(bay, panels, theme, width, 0, 0, time.Time{}, "full", nil)
}

func renderFrame(bay Bay, panels []Panel, theme Theme, width, height, focus int, now time.Time, detail string, flashes map[string]time.Time) string {
	if width < 40 {
		width = 80
	}
	if len(panels) == 0 {
		panels = []Panel{{
			Domain: domainForBay(bay.ID),
			Title:  bay.Title,
		}}
	}
	cols := 1
	if bay.Layout != "strip" {
		cols = columnCount(width)
	} else {
		cols = len(panels)
	}
	if cols > len(panels) {
		cols = len(panels)
	}
	if cols < 1 {
		cols = 1
	}
	if bay.Layout == "strip" && width/cols < 36 {
		cols = 1
	}
	inner := width/cols - 2
	if inner < 8 {
		inner = 8
	}
	if cols > 1 && cols*(inner+2) > width {
		inner = width/cols - 2
	}
	dense := bay.Layout == "dense" || cols > 1
	content := boxContentWidth(inner, dense)
	budget := 0
	if height > 0 && !(bay.Layout == "strip" && cols > 1) {
		budget = panelLineBudget(width, height, len(panels), detail)
	}
	blocks := make([]string, len(panels))
	for i, panel := range panels {
		body := panelBody(panel, theme, now, bay.RefreshSeconds, 0, detail, content, budget, flashes)
		blocks[i] = panelBox(body, theme, inner, dense, i == focus)
	}
	if bay.Layout == "strip" && cols > 1 {
		return lipgloss.JoinHorizontal(lipgloss.Top, blocks...)
	}
	return flowColumns(blocks, cols)
}

const rotationSeconds = 16

func bayGrid(count, width int) (cols, rows int) {
	if count < 1 {
		return 1, 1
	}
	band := columnCount(width)
	if band < 1 {
		band = 1
	}
	switch {
	case count == 1:
		cols = 1
	case count <= 4:
		cols = count
		if cols > band {
			cols = band
		}
	default:
		cols = 4
		if cols > band {
			cols = band
		}
	}
	if cols < 1 {
		cols = 1
	}
	rows = (count + cols - 1) / cols
	if rows < 1 {
		rows = 1
	}
	return cols, rows
}

func detailFor(width, height, panels int) string {
	if height <= 0 {
		return "full"
	}
	if panels < 1 {
		panels = 1
	}
	if height < 8 || (panels > 1 && height < 6*panels) {
		return "summary"
	}
	if height < 18 || width < 36 {
		return "compact"
	}
	return "full"
}

func itemPages(count, room int) int {
	if room < 1 || count <= room {
		return 1
	}
	return (count + room - 1) / room
}

func nextPage(page, pages int, paused bool) int {
	if paused || pages <= 1 {
		return page
	}
	if page < 0 {
		page = 0
	}
	return (page + 1) % pages
}

func pageItems(items []Item, page, room int) []Item {
	if room < 1 || page < 0 {
		return items
	}
	start := page * room
	if start >= len(items) {
		return nil
	}
	end := start + room
	if end > len(items) {
		end = len(items)
	}
	return items[start:end]
}

func panelSpan(width, panels int) (cols, rows int) {
	if panels < 1 {
		return 1, 1
	}
	cols = columnCount(width)
	if cols > panels {
		cols = panels
	}
	if cols < 1 {
		cols = 1
	}
	rows = (panels + cols - 1) / cols
	return cols, rows
}

func itemRoom(width, height, panels int, detail string) int {
	return panelLineBudget(width, height, panels, detail)
}

func panelLineBudget(width, height, panels int, detail string) int {
	if height <= 0 {
		return 0
	}
	if panels < 1 {
		panels = 1
	}
	rows := 1
	if detail != "summary" {
		_, rows = panelSpan(width, panels)
	}
	each := (height - 2) / rows
	lines := each - 3
	if lines < 1 {
		return 1
	}
	return lines
}

func bayPageCount(view bayView, width, height int) int {
	if marketsBay(view) && height > 0 {
		_, _, pages, _, _ := marketPage(view.panels, width, height, view.page)
		return pages
	}
	detail := detailFor(width, height, len(view.panels))
	_, _, pages := pageByLines(view.panels, detail, view.page, panelLineBudget(width, height, len(view.panels), detail))
	return pages
}

func marketsBay(view bayView) bool {
	if view.bay.ID == "markets" {
		return true
	}
	if len(view.panels) == 0 {
		return false
	}
	for _, panel := range view.panels {
		if panel.Domain != "markets" {
			return false
		}
	}
	return true
}

func marketInnerHeight(height int) int {
	inner := height - 1
	if inner >= 4 {
		return inner
	}
	if height > 4 {
		return height
	}
	return 4
}

func panelLines(items int) int {
	lines := items + 3
	if lines < 4 {
		lines = 4
	}
	return lines
}

func marketFamilyWindow(panelCount, cols, innerH int) int {
	if panelCount < 1 {
		return 0
	}
	if cols < 1 {
		cols = 1
	}
	fit := panelCount
	for fit > 1 {
		per := (fit + cols - 1) / cols
		if per < 1 {
			per = 1
		}
		content := innerH - per*3
		if per*4 <= innerH && content >= per && content/per >= 4 {
			break
		}
		fit--
	}
	if fit < 1 {
		return 1
	}
	return fit
}

func shareLines(demands []int, available int) []int {
	give := make([]int, len(demands))
	if len(demands) == 0 {
		return give
	}
	if available < len(demands) {
		available = len(demands)
	}
	remaining := available
	for i, demand := range demands {
		later := len(demands) - i - 1
		want := demand
		if want < 1 {
			want = 1
		}
		cap := remaining - later
		if cap < 1 {
			cap = 1
		}
		if cap > want {
			cap = want
		}
		if cap > remaining {
			cap = remaining
		}
		give[i] = cap
		remaining -= cap
	}
	for remaining > 0 {
		best := -1
		unmet := 0
		for i, demand := range demands {
			need := demand - give[i]
			if need > unmet {
				unmet = need
				best = i
			}
		}
		if best < 0 {
			break
		}
		give[best]++
		remaining--
	}
	return give
}

func packMarketColumns(panels []Panel, cols, innerH int) [][]int {
	if len(panels) == 0 {
		return nil
	}
	if cols < 1 {
		cols = 1
	}
	var columns [][]int
	var current []int
	used := 0
	flush := func() {
		if len(current) == 0 {
			return
		}
		columns = append(columns, append([]int(nil), current...))
		current = nil
		used = 0
	}
	for i, panel := range panels {
		need := panelLines(len(panel.Items))
		if len(current) > 0 && used+need > innerH && len(columns) < cols-1 {
			flush()
		}
		current = append(current, i)
		room := innerH - used
		take := need
		if take > room {
			take = room
		}
		if take < 0 {
			take = 0
		}
		used += take
		if used >= innerH && len(columns) < cols-1 && i+1 < len(panels) {
			flush()
		}
	}
	flush()
	return columns
}

func balanceColumns(panels []Panel, cols int) [][]int {
	n := len(panels)
	if n == 0 {
		return nil
	}
	if cols < 1 {
		cols = 1
	}
	if cols > n {
		cols = n
	}
	columns := make([][]int, 0, cols)
	start := 0
	for c := 0; c < cols && start < n; c++ {
		remaining := cols - c
		if remaining <= 1 {
			col := make([]int, 0, n-start)
			for i := start; i < n; i++ {
				col = append(col, i)
			}
			columns = append(columns, col)
			break
		}
		rest := 0
		for i := start; i < n; i++ {
			rest += panelLines(len(panels[i].Items))
		}
		target := rest / remaining
		end := start
		limit := n - (remaining - 1)
		used := 0
		for end < limit {
			need := panelLines(len(panels[end].Items))
			if end > start && used >= target {
				break
			}
			used += need
			end++
		}
		if end == start {
			end = start + 1
		}
		col := make([]int, 0, end-start)
		for i := start; i < end; i++ {
			col = append(col, i)
		}
		columns = append(columns, col)
		start = end
	}
	return columns
}

func columnsHold(panels []Panel, columns [][]int, innerH int) bool {
	if len(columns) == 0 {
		return false
	}
	for _, col := range columns {
		used := 0
		for _, idx := range col {
			if idx < 0 || idx >= len(panels) {
				return false
			}
			used += panelLines(len(panels[idx].Items))
		}
		if used > innerH {
			return false
		}
	}
	return true
}

func layoutMarketWindow(panels []Panel, width, innerH int) (columns [][]int, budgets []int) {
	n := len(panels)
	budgets = make([]int, n)
	if n == 0 {
		return nil, budgets
	}
	maxCols := columnCount(width)
	if maxCols > n {
		maxCols = n
	}
	if maxCols < 1 {
		maxCols = 1
	}
	total := 0
	for _, panel := range panels {
		total += panelLines(len(panel.Items))
	}
	cols := 1
	for cols < maxCols && cols*innerH < total {
		cols++
	}
	columns = packMarketColumns(panels, cols, innerH)
	if maxCols > len(columns) {
		spread := balanceColumns(panels, maxCols)
		if len(spread) > len(columns) && columnsHold(panels, spread, innerH) {
			columns = spread
		}
	}
	for _, col := range columns {
		demands := make([]int, len(col))
		for j, idx := range col {
			demands[j] = len(panels[idx].Items)
		}
		available := innerH - 3*len(col)
		if available < len(col) {
			available = len(col)
		}
		give := shareLines(demands, available)
		for j, idx := range col {
			budgets[idx] = give[j]
		}
	}
	return columns, budgets
}

func marketPage(panels []Panel, width, height, page int) (shown []Panel, label string, pages int, columns [][]int, origin int) {
	if len(panels) == 0 || height <= 0 {
		return panels, "", 1, nil, 0
	}
	innerH := marketInnerHeight(height)
	maxCols := columnCount(width)
	if maxCols > len(panels) {
		maxCols = len(panels)
	}
	if maxCols < 1 {
		maxCols = 1
	}
	window := marketFamilyWindow(len(panels), maxCols, innerH)
	if window < 1 {
		window = 1
	}
	windows := (len(panels) + window - 1) / window
	type step struct{ start, row int }
	var steps []step
	for w := 0; w < windows; w++ {
		start := w * window
		end := start + window
		if end > len(panels) {
			end = len(panels)
		}
		_, budgets := layoutMarketWindow(panels[start:end], width, innerH)
		rowPages := 1
		for i := range budgets {
			room := budgets[i]
			if room < 1 {
				room = 1
			}
			if n := itemPages(len(panels[start+i].Items), room); n > rowPages {
				rowPages = n
			}
		}
		for r := 0; r < rowPages; r++ {
			steps = append(steps, step{start, r})
		}
	}
	pages = len(steps)
	if pages < 1 {
		pages = 1
		steps = []step{{0, 0}}
	}
	if page < 0 {
		page = 0
	}
	page %= pages
	chosen := steps[page]
	end := chosen.start + window
	if end > len(panels) {
		end = len(panels)
	}
	slice := panels[chosen.start:end]
	columns, budgets := layoutMarketWindow(slice, width, innerH)
	shown = make([]Panel, len(slice))
	for i, panel := range slice {
		room := budgets[i]
		if room < 1 {
			room = 1
		}
		row := chosen.row
		if count := itemPages(len(panel.Items), room); count > 0 {
			row = chosen.row % count
		}
		panel.Items = pageItems(panel.Items, row, room)
		shown[i] = panel
	}
	if pages > 1 {
		label = strconv.Itoa(page+1) + "/" + strconv.Itoa(pages)
	}
	return shown, label, pages, columns, chosen.start
}

func visiblePanels(panels []Panel, detail string, page, room int) (shown []Panel, label string, pages int) {
	if len(panels) == 0 {
		return panels, "", 1
	}
	if room < 1 {
		return panels, "", 1
	}
	if detail == "summary" {
		type step struct{ panel, offset int }
		var steps []step
		for i, panel := range panels {
			if len(panel.Items) == 0 {
				steps = append(steps, step{i, 0})
				continue
			}
			for offset := 0; offset < len(panel.Items); offset += room {
				steps = append(steps, step{i, offset})
			}
		}
		pages = len(steps)
		if pages < 1 {
			pages = 1
		}
		if page < 0 {
			page = 0
		}
		page = page % pages
		chosen := panels[steps[page].panel]
		chosen.Items = pageItems(chosen.Items, steps[page].offset/room, room)
		label = ""
		if pages > 1 {
			label = strconv.Itoa(page+1) + "/" + strconv.Itoa(pages)
		}
		return []Panel{chosen}, label, pages
	}
	pages = 1
	for _, panel := range panels {
		if count := itemPages(len(panel.Items), room); count > pages {
			pages = count
		}
	}
	if page < 0 {
		page = 0
	}
	page = page % pages
	shown = make([]Panel, len(panels))
	for i, panel := range panels {
		panelPage := page
		if count := itemPages(len(panel.Items), room); count > 0 {
			panelPage = page % count
		}
		panel.Items = pageItems(panel.Items, panelPage, room)
		shown[i] = panel
	}
	if pages > 1 {
		label = strconv.Itoa(page+1) + "/" + strconv.Itoa(pages)
	}
	return shown, label, pages
}

func pageByLines(panels []Panel, detail string, page, budget int) (shown []Panel, label string, pages int) {
	if len(panels) == 0 || budget < 1 {
		return panels, "", 1
	}
	if detail == "summary" {
		var steps []Panel
		for _, panel := range panels {
			chunks := chunkItems(panel.Items, detail, budget)
			if len(chunks) == 0 {
				steps = append(steps, panel)
				continue
			}
			for _, chunk := range chunks {
				next := panel
				next.Items = chunk
				steps = append(steps, next)
			}
		}
		pages = len(steps)
		if pages < 1 {
			pages = 1
		}
		if page < 0 {
			page = 0
		}
		page = page % pages
		label = ""
		if pages > 1 {
			label = strconv.Itoa(page+1) + "/" + strconv.Itoa(pages)
		}
		return []Panel{steps[page]}, label, pages
	}
	chunks := make([][][]Item, len(panels))
	pages = 1
	for i, panel := range panels {
		chunks[i] = chunkItems(panel.Items, detail, budget)
		if len(chunks[i]) > pages {
			pages = len(chunks[i])
		}
	}
	if page < 0 {
		page = 0
	}
	page = page % pages
	shown = make([]Panel, len(panels))
	for i, panel := range panels {
		panelPage := page
		if count := len(chunks[i]); count > 0 {
			panelPage = page % count
		}
		if len(chunks[i]) == 0 {
			panel.Items = nil
		} else {
			panel.Items = chunks[i][panelPage]
		}
		shown[i] = panel
	}
	if pages > 1 {
		label = strconv.Itoa(page+1) + "/" + strconv.Itoa(pages)
	}
	return shown, label, pages
}

func chunkItems(items []Item, detail string, budget int) [][]Item {
	if len(items) == 0 {
		return nil
	}
	if budget < 1 {
		return [][]Item{items}
	}
	var pages [][]Item
	var current []Item
	used := 0
	var previous Item
	for _, item := range items {
		cost := rowCost(item, detail, len(current) > 0, previous)
		if len(current) > 0 && used+cost > budget {
			pages = append(pages, current)
			current = nil
			used = 0
			cost = rowCost(item, detail, false, Item{})
		}
		if cost > budget {
			cost = budget
		}
		current = append(current, item)
		used += cost
		previous = item
	}
	if len(current) > 0 {
		pages = append(pages, current)
	}
	return pages
}

func rowNeed(panels []Panel, detail string) int {
	need := 1
	for _, panel := range panels {
		for _, item := range panel.Items {
			if cost := rowCost(item, detail, false, Item{}); cost > need {
				need = cost
			}
		}
	}
	return need
}

func rowCost(item Item, detail string, gap bool, previous Item) int {
	switch item.Row {
	case "quote", "clock", "standing":
		return 1
	case "headline":
		cost := 2
		if detail == "full" {
			if summary, _ := item.Fields["summary"].(string); summary != "" {
				cost = 3
			}
		}
		if gap && previous.Row == "headline" {
			cost++
		}
		return cost
	case "observation":
		cost := 2
		if observationHasDetail(item) {
			cost = 3
		}
		if detail == "full" && observationRegionBreak(item, previous, gap) {
			cost++
		}
		return cost
	case "forecast":
		if forecastHasDetail(item) {
			return 3
		}
		return 2
	default:
		return 2
	}
}

func observationHasDetail(item Item) bool {
	if condition, _ := item.Fields["condition"].(string); condition != "" {
		return true
	}
	for _, key := range []string{"temperature_c", "apparent_temperature_c", "humidity_pct", "wind_speed_kmh"} {
		if raw, ok := item.Fields[key]; ok && raw != nil {
			return true
		}
	}
	return false
}

func observationRegionBreak(item, previous Item, hasPrevious bool) bool {
	if _, extreme := item.Fields["extreme"]; extreme {
		return false
	}
	region, _ := item.Fields["region"].(string)
	if region == "" {
		return false
	}
	if !hasPrevious {
		return true
	}
	if _, extreme := previous.Fields["extreme"]; extreme {
		return true
	}
	prev, _ := previous.Fields["region"].(string)
	return region != prev
}

func forecastHasDetail(item Item) bool {
	if condition, _ := item.Fields["condition"].(string); condition != "" {
		return true
	}
	for _, key := range []string{"temperature_high_c", "temperature_low_c"} {
		if raw, ok := item.Fields[key]; ok && raw != nil {
			return true
		}
	}
	return false
}

func renderBoard(views []bayView, theme Theme, width, height, focus, tick int, now time.Time, flashes map[string]time.Time) string {
	if len(views) == 0 {
		return ""
	}
	if width < 40 {
		width = 80
	}
	cols, rows := bayGrid(len(views), width)
	bodyH := height - 2
	cellH := 0
	if bodyH >= rows && rows > 0 {
		cellH = bodyH / rows
	}
	cellW := width / cols
	lines := make([]string, 0, rows)
	for r := 0; r < rows; r++ {
		cells := make([]string, 0, cols)
		for c := 0; c < cols; c++ {
			index := r*cols + c
			if index >= len(views) {
				continue
			}
			focused, panelFocus := focusInBay(views, index, focus)
			cells = append(cells, renderBayCell(views[index], theme, cellW, cellH, focused, panelFocus, tick, now, flashes))
		}
		lines = append(lines, lipgloss.JoinHorizontal(lipgloss.Top, cells...))
	}
	return strings.Join(lines, "\n")
}

func renderBayCell(view bayView, theme Theme, width, height int, focused bool, panelFocus, tick int, now time.Time, flashes map[string]time.Time) string {
	detail := detailFor(width, height, len(view.panels))
	var shown []Panel
	var label string
	var columns [][]int
	origin := 0
	markets := marketsBay(view) && height > 0
	if markets {
		shown, label, _, columns, origin = marketPage(view.panels, width, height, view.page)
		detail = "full"
	} else {
		if detail != "summary" && len(view.panels) > 1 && panelLineBudget(width, height, len(view.panels), detail) < rowNeed(view.panels, detail) {
			detail = "summary"
		}
		shown, label, _ = pageByLines(view.panels, detail, view.page, panelLineBudget(width, height, len(view.panels), detail))
		if detail != "full" {
			shown = dropSummaries(shown)
		}
	}
	titleRole := "text"
	if focused {
		titleRole = "accent"
	}
	head := fg(theme, titleRole).Render(view.bay.Title)
	if label != "" {
		head += "  " + fg(theme, "text").Render(label)
		if mark := pageTimer(tick, theme); mark != "" {
			head += "  " + mark
		}
	}
	var body string
	if markets {
		body = renderMarketFrame(view.bay, shown, columns, theme, width, panelFocus, origin, now, flashes)
	} else {
		body = renderFrame(view.bay, shown, theme, width, height, panelFocus, now, detail, flashes)
	}
	cell := head + "\n" + body
	if width < 1 {
		return cell
	}
	style := lipgloss.NewStyle().Width(width).MaxWidth(width)
	if height > 0 {
		style = style.Height(height).MaxHeight(height)
	}
	return style.Render(cell)
}

func focusInBay(views []bayView, bayIndex, focus int) (bool, int) {
	offset := 0
	for i := 0; i < bayIndex && i < len(views); i++ {
		offset += panelSlots(views[i])
	}
	slots := panelSlots(views[bayIndex])
	if focus >= offset && focus < offset+slots {
		return true, focus - offset
	}
	return false, -1
}

func panelSlots(view bayView) int {
	if len(view.panels) == 0 {
		return 1
	}
	return len(view.panels)
}

func columnCount(width int) int {
	switch {
	case width < 100:
		return 1
	case width < 160:
		return 2
	case width < 240:
		return 3
	default:
		return 4
	}
}

func flowColumns(blocks []string, cols int) string {
	if cols < 2 || len(blocks) < 2 {
		return lipgloss.JoinVertical(lipgloss.Left, blocks...)
	}
	columns := make([][]string, cols)
	for i, block := range blocks {
		columns[i%cols] = append(columns[i%cols], block)
	}
	rendered := make([]string, 0, cols)
	for _, column := range columns {
		if len(column) == 0 {
			continue
		}
		rendered = append(rendered, lipgloss.JoinVertical(lipgloss.Left, column...))
	}
	return lipgloss.JoinHorizontal(lipgloss.Top, rendered...)
}

func renderMarketFrame(bay Bay, panels []Panel, columns [][]int, theme Theme, width, focus, origin int, now time.Time, flashes map[string]time.Time) string {
	if len(panels) == 0 {
		return renderFrame(bay, panels, theme, width, 0, focus, now, "full", flashes)
	}
	if len(columns) == 0 {
		columns = [][]int{make([]int, len(panels))}
		for i := range panels {
			columns[0][i] = i
		}
	}
	used := len(columns)
	if used < 1 {
		used = 1
	}
	dense := false
	inner := width/used - 4
	if inner < 8 {
		dense = true
		inner = width/used - 2
	}
	if inner < 8 {
		inner = 8
	}
	content := boxContentWidth(inner, dense)
	localFocus := -1
	if focus >= origin && focus < origin+len(panels) {
		localFocus = focus - origin
	}
	rendered := make([]string, 0, used)
	for _, col := range columns {
		blocks := make([]string, 0, len(col))
		for _, idx := range col {
			if idx < 0 || idx >= len(panels) {
				continue
			}
			body := panelBody(panels[idx], theme, now, bay.RefreshSeconds, 0, "full", content, 0, flashes)
			blocks = append(blocks, panelBox(body, theme, inner, dense, idx == localFocus))
		}
		if len(blocks) == 0 {
			continue
		}
		rendered = append(rendered, lipgloss.JoinVertical(lipgloss.Left, blocks...))
	}
	if len(rendered) == 0 {
		return ""
	}
	return lipgloss.JoinHorizontal(lipgloss.Top, rendered...)
}

func domainForBay(id string) string {
	switch id {
	case "storm":
		return "weather"
	case "field", "far", "fantasy", "sideline":
		return "sports"
	default:
		return id
	}
}

func boxContentWidth(outer int, dense bool) int {
	pad := 1
	if dense {
		pad = 0
	}
	content := outer - pad*2
	if content < 1 {
		return 1
	}
	return content
}

func panelBox(body string, theme Theme, width int, dense, focused bool) string {
	pad := 1
	if dense {
		pad = 0
	}
	border := theme.Roles["border"]
	if focused {
		border = theme.Roles["accent"]
	}
	return lipgloss.NewStyle().
		Width(width).
		Border(lipgloss.NormalBorder()).
		BorderForeground(lipgloss.Color(border)).
		Foreground(lipgloss.Color(theme.Roles["text"])).
		Background(lipgloss.Color(theme.Roles["surface"])).
		Padding(0, pad).
		Render(body)
}

func fitItem(item Item, width int) Item {
	item.Title = fitLine(item.Title, width)
	summary, _ := item.Fields["summary"].(string)
	if summary == "" {
		return item
	}
	summary = strings.Join(strings.Fields(summary), " ")
	fields := make(map[string]any, len(item.Fields))
	for key, value := range item.Fields {
		fields[key] = value
	}
	fields["summary"] = fitLine(summary, width)
	item.Fields = fields
	return item
}

func fitLine(text string, width int) string {
	if width < 1 || ansi.StringWidth(text) <= width {
		return text
	}
	return ansi.Truncate(text, width, "…")
}

func fitBlock(text string, width int) string {
	if width < 1 || text == "" {
		return text
	}
	lines := strings.Split(text, "\n")
	for i, line := range lines {
		if ansi.StringWidth(line) > width {
			lines[i] = ansi.Truncate(line, width, "…")
		}
	}
	return strings.Join(lines, "\n")
}

func clipLines(text string, n int) string {
	if n < 1 {
		return ""
	}
	lines := strings.Split(text, "\n")
	if len(lines) <= n {
		return text
	}
	return strings.Join(lines[:n], "\n")
}

func panelBody(panel Panel, theme Theme, now time.Time, refresh, limit int, detail string, width, lineBudget int, flashes map[string]time.Time) string {
	lines := []string{headerLine(panel, theme, now, refresh)}
	items := panel.Items
	if limit > 0 && len(items) > limit {
		items = items[:limit]
	}
	if len(items) == 0 {
		lines = append(lines, fg(theme, "muted").Render(panel.Domain+" has no items"))
	}
	used := 0
	lastRegion := ""
	for i, item := range items {
		var block []string
		if i > 0 && item.Row == "headline" {
			block = append(block, "")
		}
		item = fitItem(item, width)
		if detail == "full" && item.Row == "observation" {
			region, _ := item.Fields["region"].(string)
			if _, extreme := item.Fields["extreme"]; !extreme && region != "" && region != lastRegion {
				block = append(block, fg(theme, "accent").Render(region))
				lastRegion = region
			}
		}
		block = append(block, strings.Split(renderItem(item, theme, now, width, flashes), "\n")...)
		if lineBudget > 0 && used+len(block) > lineBudget {
			if used > 0 {
				break
			}
			if len(block) > lineBudget {
				block = block[:lineBudget]
			}
		}
		lines = append(lines, block...)
		used += len(block)
		if lineBudget > 0 && used >= lineBudget {
			break
		}
	}
	return fitBlock(strings.Join(lines, "\n"), width)
}

func headerLine(panel Panel, theme Theme, now time.Time, refresh int) string {
	parts := []string{fg(theme, "text").Render(panel.Title)}
	if mark := liveMark(panel, now, refresh); mark != "" {
		role := "accent"
		if mark == "○" {
			role = "muted"
		}
		parts = append(parts, fg(theme, role).Render(mark))
	}
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

func pageTimer(tick int, theme Theme) string {
	if rotationSeconds < 2 {
		return ""
	}
	span := tick % rotationSeconds
	if span < 0 {
		span = 0
	}
	color := mixHex(theme.Roles["up"], theme.Roles["down"], float64(span)/float64(rotationSeconds-1))
	return lipgloss.NewStyle().Foreground(lipgloss.Color(color)).Render("●")
}

func mixHex(from, to string, t float64) string {
	fr, fg, fb, ok1 := parseHex(from)
	tr, tg, tb, ok2 := parseHex(to)
	if !ok1 || !ok2 {
		return from
	}
	if t < 0 {
		t = 0
	}
	if t > 1 {
		t = 1
	}
	r := fr + int(float64(tr-fr)*t)
	g := fg + int(float64(tg-fg)*t)
	b := fb + int(float64(tb-fb)*t)
	return fmt.Sprintf("#%02x%02x%02x", r, g, b)
}

func parseHex(value string) (r, g, b int, ok bool) {
	if len(value) != 7 || value[0] != '#' {
		return 0, 0, 0, false
	}
	raw, err := strconv.ParseUint(value[1:], 16, 24)
	if err != nil {
		return 0, 0, 0, false
	}
	return int(raw >> 16), int((raw >> 8) & 0xff), int(raw & 0xff), true
}

func liveMark(panel Panel, now time.Time, refresh int) string {
	if panel.Stale || now.IsZero() || panel.UpdatedAt == "" {
		return ""
	}
	parsed, err := time.Parse(time.RFC3339, panel.UpdatedAt)
	if err != nil {
		return ""
	}
	interval := refresh
	margin := time.Duration(0)
	if panel.RefreshSeconds > 0 {
		interval = panel.RefreshSeconds
		margin = 10 * time.Second
	}
	if interval < 1 {
		interval = 60
	}
	if now.Sub(parsed) <= time.Duration(interval)*time.Second+margin {
		return "●"
	}
	return "○"
}

func renderItem(item Item, theme Theme, now time.Time, width int, flashes map[string]time.Time) string {
	switch item.Row {
	case "quote":
		return renderQuote(item, theme, now, width, flashes)
	case "headline":
		return renderHeadline(item, theme, now)
	case "score":
		return renderScore(item, theme, now)
	case "alert":
		return renderAlert(item, theme, now)
	case "clock":
		return renderClock(item, theme)
	case "fantasy":
		return renderFantasy(item, theme, now)
	case "follow":
		return renderFollow(item, theme)
	case "standing":
		return renderStanding(item, theme)
	case "observation":
		return renderObservation(item, theme, now)
	case "forecast":
		return renderForecast(item, theme, now)
	default:
		return renderHeadline(item, theme, now)
	}
}

func dropSummaries(panels []Panel) []Panel {
	out := make([]Panel, len(panels))
	for i, panel := range panels {
		items := make([]Item, len(panel.Items))
		for j, item := range panel.Items {
			if _, ok := item.Fields["summary"]; ok {
				fields := make(map[string]any, len(item.Fields))
				for key, value := range item.Fields {
					if key != "summary" {
						fields[key] = value
					}
				}
				item.Fields = fields
			}
			items[j] = item
		}
		panel.Items = items
		out[i] = panel
	}
	return out
}

func renderHeadline(item Item, theme Theme, now time.Time) string {
	desk, _ := item.Fields["desk"].(string)
	family, _ := item.Fields["family"].(string)
	if desk == "" {
		desk = family
	}
	title := fg(theme, "text").Render(item.Title)
	meta := metaLine([]string{desk, item.Source, formatObserved(item.ObservedAt), ageLabel(item.ObservedAt, now)}, theme)
	summary, _ := item.Fields["summary"].(string)
	if summary == "" {
		return title + "\n" + meta
	}
	return title + "\n" + fg(theme, "muted").Render(summary) + "\n" + meta
}

const quoteFlash = 2 * time.Second

func quoteIdentity(item Item) string {
	if item.ID != "" {
		return item.ID
	}
	symbol, _ := item.Fields["symbol"].(string)
	return symbol
}

func shownPrice(fields map[string]any) (string, bool) {
	raw, ok := fields["price"]
	if !ok || raw == nil {
		return "", false
	}
	price, ok := asFloat(raw)
	if !ok {
		return "", false
	}
	return trimFloat(price), true
}

func noteQuotePrices(seen map[string]string, flashes map[string]time.Time, panels []Panel, now time.Time) {
	if flashes != nil && !now.IsZero() {
		for key, until := range flashes {
			if !until.After(now) {
				delete(flashes, key)
			}
		}
	}
	if seen == nil {
		return
	}
	for _, panel := range panels {
		for _, item := range panel.Items {
			if item.Row != "quote" {
				continue
			}
			key := quoteIdentity(item)
			price, ok := shownPrice(item.Fields)
			if key == "" || !ok {
				continue
			}
			if prev, exists := seen[key]; exists && prev != price && flashes != nil && !now.IsZero() {
				flashes[key] = now.Add(quoteFlash)
			}
			seen[key] = price
		}
	}
}

func quoteFlashing(item Item, flashes map[string]time.Time, now time.Time) bool {
	if flashes == nil || now.IsZero() {
		return false
	}
	until, ok := flashes[quoteIdentity(item)]
	return ok && now.Before(until)
}

func renderQuote(item Item, theme Theme, now time.Time, width int, flashes map[string]time.Time) string {
	symbol, _ := item.Fields["symbol"].(string)
	if symbol == "" {
		symbol = item.Title
	}
	priceRole := "text"
	if quoteFlashing(item, flashes, now) {
		priceRole = "accent"
	}
	var parts []quotePart
	parts = append(parts, quotePart{symbol, priceRole})
	if raw, ok := item.Fields["price"]; ok && raw != nil {
		if price, ok := asFloat(raw); ok {
			parts = append(parts, quotePart{trimFloat(price), priceRole})
		}
	}
	if change, role := formatChange(item.Fields); change != "" {
		parts = append(parts, quotePart{change, role})
		if bar := changeBar(item.Fields); bar != "" {
			parts = append(parts, quotePart{bar, role})
		}
	}
	if delayed, _ := item.Fields["delayed"].(bool); delayed {
		parts = append(parts, quotePart{"delayed", "muted"})
	}
	core := len(parts)
	if item.Source != "" {
		parts = append(parts, quotePart{item.Source, "muted"})
	}
	if age := ageLabel(item.ObservedAt, now); age != "" {
		parts = append(parts, quotePart{age, "muted"})
	}
	for len(parts) > core && quotePlainWidth(parts) > width && width > 0 {
		parts = parts[:len(parts)-1]
	}
	line := quoteStyled(parts, theme)
	if width > 0 && quotePlainWidth(parts) > width {
		line = fg(theme, "text").Render(fitLine(quotePlain(parts), width))
	}
	return line
}

type quotePart struct {
	text string
	role string
}

func quotePlain(parts []quotePart) string {
	texts := make([]string, len(parts))
	for i, part := range parts {
		texts[i] = part.text
	}
	return strings.Join(texts, "  ")
}

func quotePlainWidth(parts []quotePart) int {
	return ansi.StringWidth(quotePlain(parts))
}

func quoteStyled(parts []quotePart, theme Theme) string {
	styled := make([]string, len(parts))
	for i, part := range parts {
		styled[i] = fg(theme, part.role).Render(part.text)
	}
	return strings.Join(styled, "  ")
}

func changeBar(fields map[string]any) string {
	raw, ok := fields["change"]
	if !ok || raw == nil {
		return ""
	}
	change, ok := asFloat(raw)
	if !ok {
		return ""
	}
	n := int(math.Round(math.Abs(change)))
	if n < 1 {
		n = 1
	}
	if n > 8 {
		n = 8
	}
	return strings.Repeat("▬", n)
}

func renderFollow(item Item, theme Theme) string {
	state := "not followed"
	if followed, _ := item.Fields["followed"].(bool); followed {
		state = "following"
	}
	tier, _ := item.Fields["tier"].(string)
	country, _ := item.Fields["country"].(string)
	flag, _ := item.Fields["flag"].(string)
	family, _ := item.Fields["family"].(string)
	title := item.Title
	if glyph := sportGlyph(family); glyph != "" {
		title = glyph + "  " + title
	}
	line := fg(theme, "text").Render(title) + "  " + fg(theme, "accent").Render(state)
	if flag != "" {
		role := "muted"
		if flag == "active" {
			role = "up"
		}
		line += "  " + fg(theme, role).Render(flag)
	}
	return line + "\n" + metaLine([]string{country, seasonLabel(item), tier, item.Source}, theme)
}

func seasonLabel(item Item) string {
	var parts []string
	start, _ := item.Fields["season_start"].(string)
	end, _ := item.Fields["season_end"].(string)
	switch {
	case start != "" && end != "":
		parts = append(parts, start+" – "+end)
	case start != "":
		parts = append(parts, "from "+start)
	default:
		if season, _ := item.Fields["season"].(string); season != "" {
			parts = append(parts, "season "+season)
		}
	}
	if last, _ := item.Fields["last_event"].(string); last != "" {
		parts = append(parts, "last "+last)
	}
	if next, _ := item.Fields["next_event"].(string); next != "" {
		parts = append(parts, "next "+next)
	}
	return strings.Join(parts, " · ")
}

func phaseRole(state string) string {
	switch {
	case strings.HasPrefix(state, "in progress"):
		return "up"
	case strings.HasPrefix(state, "final"):
		return "muted"
	default:
		return "warn"
	}
}

func renderScore(item Item, theme Theme, now time.Time) string {
	home, _ := item.Fields["home"].(string)
	away, _ := item.Fields["away"].(string)
	score, _ := item.Fields["score"].(string)
	state, _ := item.Fields["state"].(string)
	tier, _ := item.Fields["tier"].(string)
	excerpt, _ := item.Fields["excerpt"].(string)
	factualLine, _ := item.Fields["factual_line"].(string)
	text := fg(theme, "text")
	family, _ := item.Fields["family"].(string)
	glyph := sportGlyph(family)
	if excerpt != "" {
		quoted := text.Render("\"" + excerpt + "\"")
		return quoted + "\n" + metaLine([]string{item.Source}, theme)
	}
	league, _ := item.Fields["league"].(string)
	line := ""
	if glyph != "" {
		line = text.Render(glyph) + "  "
	}
	line += text.Render(home)
	if score != "" {
		line += "  " + text.Render(score)
	}
	if away != "" {
		line += "  " + text.Render(away)
	}
	if league != "" {
		line += "  " + fg(theme, "muted").Render(league)
	}
	if state != "" {
		line += "  " + fg(theme, phaseRole(state)).Render(state)
	}
	tail := []string{item.Source}
	if tier == "delayed" {
		tail = append([]string{"delayed"}, tail...)
	}
	if factual, _ := item.Fields["factual"].(bool); factual {
		tail = append(tail, "factual line")
	}
	if factualLine != "" {
		line += "\n" + text.Render(factualLine)
	}
	tail = append(tail, ageLabel(item.ObservedAt, now))
	return line + "\n" + metaLine(tail, theme)
}

func sportGlyph(family string) string {
	switch family {
	case "baseball":
		return "⚾"
	case "basketball":
		return "🏀"
	case "american-football", "canadian-football":
		return "🏈"
	case "football":
		return "⚽"
	case "ice-hockey":
		return "🏒"
	case "cricket":
		return "🏏"
	case "rugby-league", "rugby-union":
		return "🏉"
	case "tennis":
		return "🎾"
	case "motorsport":
		return "🏎️"
	default:
		return ""
	}
}

func renderStanding(item Item, theme Theme) string {
	team, _ := item.Fields["team"].(string)
	if team == "" {
		team = item.Title
	}
	rank, _ := item.Fields["rank"].(string)
	line, _ := item.Fields["line"].(string)
	family, _ := item.Fields["family"].(string)
	parts := []string{}
	if glyph := sportGlyph(family); glyph != "" {
		parts = append(parts, glyph)
	}
	if rank != "" {
		parts = append(parts, rank)
	}
	parts = append(parts, team)
	if line != "" {
		parts = append(parts, line)
	}
	return fg(theme, "text").Render(strings.Join(parts, "  "))
}

func weatherGlyph(condition string) string {
	switch strings.ToLower(condition) {
	case "clear":
		return "☀"
	case "mainly clear":
		return "🌤"
	case "partly cloudy":
		return "⛅"
	case "overcast":
		return "☁"
	case "fog":
		return "🌫"
	case "drizzle":
		return "🌦"
	case "rain", "showers":
		return "🌧"
	case "snow":
		return "🌨"
	case "thunderstorm":
		return "⛈"
	default:
		return ""
	}
}

func renderObservation(item Item, theme Theme, now time.Time) string {
	place, _ := item.Fields["place"].(string)
	if extreme, _ := item.Fields["extreme"].(string); extreme != "" {
		place = extreme + "  " + place
	}
	condition, _ := item.Fields["condition"].(string)
	text := fg(theme, "text")
	var detail []string
	if glyph := weatherGlyph(condition); glyph != "" {
		detail = append(detail, glyph)
	}
	if raw, ok := item.Fields["temperature_c"]; ok && raw != nil {
		if temp, ok := asFloat(raw); ok {
			detail = append(detail, trimFloat(temp)+"°C")
		}
	}
	if condition != "" {
		detail = append(detail, condition)
	}
	if raw, ok := item.Fields["apparent_temperature_c"]; ok && raw != nil {
		if feels, ok := asFloat(raw); ok {
			detail = append(detail, "feels "+trimFloat(feels)+"°C")
		}
	}
	if raw, ok := item.Fields["humidity_pct"]; ok && raw != nil {
		if humidity, ok := asFloat(raw); ok {
			detail = append(detail, trimFloat(humidity)+"%")
		}
	}
	if raw, ok := item.Fields["wind_speed_kmh"]; ok && raw != nil {
		if wind, ok := asFloat(raw); ok {
			detail = append(detail, trimFloat(wind)+" km/h")
		}
	}
	body := text.Render(place)
	if len(detail) > 0 {
		body += "\n" + text.Render(strings.Join(detail, "  "))
	}
	return body + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt), ageLabel(item.ObservedAt, now)}, theme)
}

func renderForecast(item Item, theme Theme, now time.Time) string {
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
	if glyph := weatherGlyph(condition); glyph != "" || len(temps) > 0 || condition != "" {
		detail := strings.Join(temps, " ")
		if glyph := weatherGlyph(condition); glyph != "" {
			if detail != "" {
				detail += "  "
			}
			detail += glyph
		}
		if condition != "" {
			if detail != "" {
				detail += "  "
			}
			detail += condition
		}
		line += "\n" + text.Render(detail)
	}
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt), ageLabel(item.ObservedAt, now)}, theme)
}

func renderFantasy(item Item, theme Theme, now time.Time) string {
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
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt), ageLabel(item.ObservedAt, now)}, theme)
}

func renderAlert(item Item, theme Theme, now time.Time) string {
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
	return line + "\n" + metaLine([]string{item.Source, formatObserved(item.ObservedAt), ageLabel(item.ObservedAt, now)}, theme)
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

func ageLabel(raw string, now time.Time) string {
	if now.IsZero() || raw == "" {
		return ""
	}
	parsed, err := time.Parse(time.RFC3339, raw)
	if err != nil {
		return ""
	}
	age := now.Sub(parsed)
	if age < 0 {
		age = 0
	}
	switch {
	case age < time.Minute:
		return strconv.Itoa(int(age.Seconds())) + "s"
	case age < time.Hour:
		return strconv.Itoa(int(age.Minutes())) + "m"
	case age < 48*time.Hour:
		return strconv.Itoa(int(age.Hours())) + "h"
	default:
		return strconv.Itoa(int(age.Hours()/24)) + "d"
	}
}
