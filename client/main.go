package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type bayView struct {
	bay          Bay
	panels       []Panel
	live         bool
	page         int
	briefPlace   string
	briefOutlet  string
	briefFamily  string
	briefChoices []followChoice
}

type model struct {
	views        []bayView
	theme        Theme
	width        int
	height       int
	focus        int
	live         bool
	board        bool
	settings     bool
	seconds      int
	navigating   bool
	server       string
	root         string
	suggestion   Suggestion
	now          time.Time
	themeIDs     []string
	bayIDs       []string
	enabled      map[string]bool
	fixture      bool
	layouts      []boardLayout
	slot         int
	notice       string
	saving       bool
	follows      bool
	sideline     bool
	briefPick    bool
	followDigits string
	followCursor int
	paused       bool
	seenPrice    map[string]string
	flashes      map[string]time.Time
	guidePage    int
	guideCursor  int
	guideScroll  int
}

func (m model) Init() tea.Cmd {
	cmds := []tea.Cmd{scheduleClock()}
	if m.live {
		seconds := 30
		if len(m.views) > 0 && m.views[0].bay.RefreshSeconds > 0 {
			seconds = m.views[0].bay.RefreshSeconds
		}
		cmds = append(cmds, scheduleRefresh(seconds))
	}
	return tea.Batch(cmds...)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	case clockMsg:
		if !m.paused {
			m.now = time.Time(msg)
			m.tickRotation()
		}
		return m, scheduleClock()
	case tea.KeyMsg:
		return m.onKey(msg.String())
	case tickMsg:
		if !m.live || m.paused {
			if m.live {
				return m, scheduleRefresh(m.refreshSeconds())
			}
			return m, nil
		}
		cmds := []tea.Cmd{scheduleRefresh(m.refreshSeconds())}
		for _, view := range m.views {
			if view.live {
				cmds = append(cmds, fetchPanelsCmd(m.server, view.bay.ID))
			}
		}
		return m, tea.Batch(cmds...)
	case panelsMsg:
		m.replaceBay(msg.bayID, msg.panels, msg.err)
	case followResult:
		if msg.err != nil {
			m.notice = "follow was rejected"
			return m, nil
		}
		bayID := msg.bayID
		if bayID == "" {
			bayID = "field"
		}
		m.replaceBay(bayID, msg.panels, nil)
		word := "unfollowed"
		if msg.follow {
			word = "followed"
		}
		m.notice = word + " " + msg.name
	case briefResult:
		if msg.err != nil {
			if msg.name == "" {
				m.notice = "brief list is unavailable"
			} else {
				m.notice = "brief choice was rejected"
			}
			return m, nil
		}
		m.applyBrief(msg)
		if msg.name != "" {
			m.notice = "selected " + msg.name
		}
	}
	return m, nil
}

func (m model) onKey(key string) (tea.Model, tea.Cmd) {
	switch key {
	case "q", "ctrl+c":
		return m, tea.Quit
	case "esc":
		if m.picking() {
			m.closePickers()
			return m, nil
		}
		if m.settings {
			m.settings = false
			return m, nil
		}
		return m, tea.Quit
	case "?":
		m.closePickers()
		m.settings = !m.settings
		if m.settings {
			m.guidePage = 0
			m.guideCursor = 0
			m.guideScroll = 0
		}
		return m, nil
	case "h":
		if m.board && !m.settings && !m.picking() {
			m.saving = false
			m.goHome()
			return m, nil
		}
	case "f":
		return m.openRefine()
	case "enter":
		if m.settings {
			if m.board && m.guidePage == 2 && m.guideCursor >= 0 && m.guideCursor < len(m.bayIDs) {
				m.toggleBay(m.bayIDs[m.guideCursor])
			} else if m.board {
				m.guidePage = 2
				m.guideScroll = 0
			}
			return m, nil
		}
		if m.follows && m.followDigits != "" {
			return m.commitFollow(m.followDigits, true)
		}
		if m.follows {
			return m.toggleFollow(m.followCursor)
		}
		if m.sideline {
			return m.toggleSideline(m.followCursor)
		}
		if m.briefPick {
			return m.selectBrief(m.followCursor)
		}
		if refineHint(m.focusedBayID()) != "" {
			return m.openRefine()
		}
		m.notice = "nothing to select"
		return m, nil
	case "p":
		if m.settings || m.picking() {
			break
		}
		m.paused = !m.paused
		m.saving = false
		if m.paused {
			m.notice = "paused"
			return m, nil
		}
		m.notice = ""
		m.now = time.Now()
		m.seconds = 0
		return m, nil
	case "t":
		m.theme = m.cycledTheme()
		if m.board {
			m.persist()
		}
		return m, nil
	case "j", "down":
		if m.picking() {
			m.stepPicker(1)
			return m, nil
		}
		if m.settings {
			m.stepGuide(1)
			return m, nil
		}
		m.moveFocus(1, 0)
	case "k", "up":
		if m.picking() {
			m.stepPicker(-1)
			return m, nil
		}
		if m.settings {
			m.stepGuide(-1)
			return m, nil
		}
		m.moveFocus(-1, 0)
	case "left":
		if m.settings {
			m.stepGuidePage(-1)
			return m, nil
		}
		if !m.picking() {
			m.moveFocus(0, -1)
		}
	case "right":
		if m.settings {
			m.stepGuidePage(1)
			return m, nil
		}
		if !m.picking() {
			m.moveFocus(0, 1)
		}
	case "s":
		if m.board && !m.settings && !m.picking() {
			m.saving = true
			m.notice = ""
			return m, nil
		}
	case "[":
		if m.board && !m.settings && !m.picking() {
			m.saving = false
			if next := cycleSlot(m.layouts, m.slot, -1); next > 0 {
				m.loadCurrentSlot(next)
			}
			return m, nil
		}
	case "]":
		if m.board && !m.settings && !m.picking() {
			m.saving = false
			if next := cycleSlot(m.layouts, m.slot, 1); next > 0 {
				m.loadCurrentSlot(next)
			}
			return m, nil
		}
	case "a":
		suggestion := m.currentSuggestion()
		if m.settings || m.picking() || suggestion.DeskID == "" {
			break
		}
		desk, err := loadDesk(m.root, suggestion.DeskID)
		if err != nil {
			break
		}
		if m.board {
			m.swapBoard(desk)
			break
		}
		exe, err := os.Executable()
		if err != nil {
			break
		}
		_, _ = launchProcesses(exe, m.server, desk)
	default:
		if m.picking() && len(key) == 1 && key[0] >= '0' && key[0] <= '9' {
			return m.commitFollow(m.followDigits+key, false)
		}
		if m.board && !m.settings && !m.picking() && len(key) == 1 && key[0] >= '1' && key[0] <= '9' {
			slot := int(key[0] - '0')
			if m.saving {
				m.saveCurrentSlot(slot)
			} else {
				m.loadCurrentSlot(slot)
			}
			return m, nil
		}
		if m.saving {
			m.saving = false
		}
		if m.settings && m.board && !m.picking() && len(key) == 1 && key[0] >= '1' && key[0] <= '9' {
			index := int(key[0] - '1')
			if index < len(m.bayIDs) {
				m.guidePage = 2
				m.guideScroll = 0
				m.guideCursor = index
			}
			return m, nil
		}
	}
	return m, nil
}

func (m model) openRefine() (tea.Model, tea.Cmd) {
	if m.saving {
		m.saving = false
	}
	m.settings = false
	m.followDigits = ""
	m.notice = ""
	switch m.focusedBayID() {
	case "field":
		m.sideline = false
		m.briefPick = false
		m.follows = !m.follows
	case "sideline":
		m.follows = false
		m.briefPick = false
		m.sideline = !m.sideline
	case "brief":
		m.follows = false
		m.sideline = false
		if m.briefPick {
			m.briefPick = false
			return m, nil
		}
		m.briefPick = true
		if len(m.briefChoices()) == 0 && !m.fixture {
			return m, fetchBriefCmd(m.server)
		}
		return m, nil
	default:
		m.closePickers()
		m.notice = m.focusedBayTitle() + " has nothing to choose"
	}
	return m, nil
}

func bayOrigin(views []bayView, bayIndex int) int {
	offset := 0
	for i := 0; i < bayIndex && i < len(views); i++ {
		offset += panelSlots(views[i])
	}
	return offset
}

func (m *model) moveFocus(dRow, dCol int) {
	n := len(m.views)
	if n == 0 || (dRow == 0 && dCol == 0) {
		return
	}
	width := m.width
	if width < 40 {
		width = 80
	}
	cols, rows := bayGrid(n, width)
	bay := m.focusedBay()
	if bay < 0 || bay >= n {
		bay = 0
	}
	row, col := bay/cols, bay%cols
	if dCol != 0 {
		rowCount := cols
		if remain := n - row*cols; remain < rowCount {
			rowCount = remain
		}
		if rowCount < 1 {
			return
		}
		col += dCol
		if col < 0 {
			col = rowCount - 1
		} else if col >= rowCount {
			col = 0
		}
	}
	if dRow != 0 {
		nextRow := row + dRow
		if nextRow < 0 {
			nextRow = rows - 1
		} else if nextRow >= rows {
			nextRow = 0
		}
		if nextRow*cols+col >= n {
			return
		}
		row = nextRow
	}
	next := row*cols + col
	if next < 0 || next >= n || next == bay {
		return
	}
	m.focus = bayOrigin(m.views, next)
	m.navigating = true
}

func (m *model) stepGuidePage(delta int) {
	pages := guidePageCount(m.board)
	if pages < 1 {
		return
	}
	m.guidePage = (m.guidePage + delta%pages + pages) % pages
	m.guideScroll = 0
}

func (m *model) stepGuide(delta int) {
	if m.board && m.guidePage == 2 {
		n := len(m.bayIDs)
		if n < 1 {
			return
		}
		m.guideCursor = (m.guideCursor + delta + n) % n
		return
	}
	lines := guideLines(m.guidePage, m.board, m.bayIDs, m.enabled, m.guideCursor)
	room := guideRoom(m.height) - 1
	if room < 1 {
		room = 1
	}
	maxScroll := len(lines) - room
	if maxScroll < 0 {
		maxScroll = 0
	}
	next := m.guideScroll + delta
	if next < 0 || next > maxScroll {
		m.stepGuidePage(delta)
		return
	}
	m.guideScroll = next
}

func (m *model) cycledTheme() Theme {
	next := nextTheme(m.themeIDs, m.theme.ID)
	theme, err := loadTheme(m.root, next)
	if err != nil {
		return m.theme
	}
	return theme
}

func (m *model) toggleBay(id string) {
	if m.enabled[id] {
		kept := m.views[:0]
		for _, view := range m.views {
			if view.bay.ID != id {
				kept = append(kept, view)
			}
		}
		m.views = kept
		m.enabled[id] = false
	} else if view, err := loadView(m.root, m.server, id, "", false); err == nil {
		m.views = append(m.views, view)
		m.enabled[id] = true
		if view.live {
			m.live = true
		}
	}
	if m.focus >= len(m.flatPanels()) {
		m.focus = 0
	}
	m.persist()
}

func (m *model) goHome() {
	bays := make([]DeskBay, len(defaultBoardBays))
	for i, id := range defaultBoardBays {
		bays[i] = DeskBay{ID: id}
	}
	m.slot = 0
	m.swapBoard(Desk{ID: "home", Title: "Home", Bays: bays})
	m.notice = "home"
}

func (m *model) swapBoard(desk Desk) {
	views := make([]bayView, 0, len(desk.Bays))
	enabled := map[string]bool{}
	for _, bay := range desk.Bays {
		view, err := loadView(m.root, m.server, bay.ID, m.theme.ID, m.fixture)
		if err != nil {
			continue
		}
		views = append(views, view)
		enabled[bay.ID] = true
	}
	if len(views) == 0 {
		return
	}
	m.views = views
	m.enabled = enabled
	m.focus = 0
	live := false
	for _, view := range views {
		if view.live {
			live = true
		}
	}
	m.live = live
	m.persist()
}

func (m model) shownBayIDs() []string {
	ids := make([]string, 0, len(m.views))
	for _, view := range m.views {
		ids = append(ids, view.bay.ID)
	}
	return ids
}

func (m model) currentSuggestion() Suggestion {
	if m.suggestion.DeskID == "" {
		return m.suggestion
	}
	desk, err := loadDesk(m.root, m.suggestion.DeskID)
	if err != nil {
		return m.suggestion
	}
	bays := make([]string, len(desk.Bays))
	for i, bay := range desk.Bays {
		bays[i] = bay.ID
	}
	return visibleSuggestion(m.suggestion, bays, m.shownBayIDs())
}

func (m *model) saveCurrentSlot(slot int) {
	m.layouts = saveLayout(m.layouts, slot, m.shownBayIDs(), m.theme.ID)
	m.slot = slot
	m.notice = ""
	m.saving = false
	m.persist()
}

func (m *model) loadCurrentSlot(slot int) {
	layout, ok := layoutAt(m.layouts, slot)
	if !ok {
		m.notice = fmt.Sprintf("slot %d is empty", slot)
		m.saving = false
		return
	}
	m.notice = ""
	m.saving = false
	m.slot = slot
	if theme, err := loadTheme(m.root, layout.Theme); err == nil {
		m.theme = theme
	}
	m.applyBays(layout.Bays)
}

func (m *model) applyBays(ids []string) {
	views := make([]bayView, 0, len(ids))
	enabled := map[string]bool{}
	for _, id := range ids {
		view, err := loadView(m.root, m.server, id, m.theme.ID, m.fixture)
		if err != nil {
			continue
		}
		views = append(views, view)
		enabled[id] = true
	}
	if len(views) == 0 {
		return
	}
	m.views = views
	m.enabled = enabled
	m.focus = 0
	live := false
	for _, view := range views {
		if view.live {
			live = true
		}
	}
	m.live = live
	m.persist()
}

func (m model) persist() {
	ids := m.shownBayIDs()
	saveBoardPrefs(m.root, boardPrefs{Theme: m.theme.ID, Bays: ids, Layouts: normalizeLayouts(m.layouts), Slot: m.slot})
}

func (m *model) tickRotation() {
	if m.paused {
		return
	}
	m.seconds++
	if m.seconds%rotationSeconds != 0 {
		return
	}
	cellW, cellH := m.cellSize()
	focused := -1
	if m.navigating {
		focused = m.focusedBay()
	}
	for i := range m.views {
		pages := bayPageCount(m.views[i], cellW, cellH)
		m.views[i].page = nextPage(m.views[i].page, pages, i == focused)
	}
	m.navigating = false
}

func (m model) cellSize() (int, int) {
	width := m.width
	if width < 40 {
		width = 80
	}
	count := len(m.views)
	if count < 1 {
		count = 1
	}
	cols, rows := bayGrid(count, width)
	bodyH := m.height - 2
	cellH := 0
	if bodyH >= rows && rows > 0 {
		cellH = bodyH / rows
	}
	return width / cols, cellH
}

func (m model) focusedBay() int {
	for i := range m.views {
		if inside, _ := focusInBay(m.views, i, m.focus); inside {
			return i
		}
	}
	return 0
}

func (m model) refreshSeconds() int {
	for _, view := range m.views {
		if view.bay.RefreshSeconds > 0 {
			return view.bay.RefreshSeconds
		}
	}
	return 30
}

func (m *model) replaceBay(bayID string, panels []Panel, err error) {
	for i, view := range m.views {
		if view.bay.ID != bayID {
			continue
		}
		m.views[i].panels = mergeRefresh(view.panels, panels, err)
		if err == nil {
			if m.seenPrice == nil {
				m.seenPrice = map[string]string{}
			}
			if m.flashes == nil {
				m.flashes = map[string]time.Time{}
			}
			noteQuotePrices(m.seenPrice, m.flashes, m.views[i].panels, m.now)
		}
	}
	if m.focus >= len(m.flatPanels()) {
		m.focus = 0
	}
}

func (m model) flatPanels() []Panel {
	var panels []Panel
	for _, view := range m.views {
		for _, panel := range view.panels {
			if m.board && panel.Title != "" {
				panel.Title = view.bay.Title + " · " + panel.Title
			}
			panels = append(panels, panel)
		}
	}
	return panels
}

func (m model) focusedTitle() string {
	panels := m.flatPanels()
	if len(panels) == 0 {
		if m.board {
			return "Board"
		}
		return "Oriel"
	}
	if m.focus < 0 || m.focus >= len(panels) {
		return panels[0].Title
	}
	return panels[m.focus].Title
}

func (m model) liveWord() string {
	if !m.live {
		return "fixture"
	}
	for _, view := range m.views {
		for _, panel := range view.panels {
			if panel.Stale {
				return "stale"
			}
		}
	}
	return "live"
}

func (m model) View() string {
	width := m.width
	if width <= 0 {
		width = 80
	}
	var body string
	if m.settings {
		body = guideView(m.theme, m.guidePage, m.board, m.bayIDs, m.enabled, m.guideCursor, m.guideScroll, width, m.height)
	} else if m.follows {
		body = followsView(m.theme, "Follows", "A number moves to that row. enter follows or unfollows it.", m.fieldFollows(), m.followDigits, m.followCursor, width, fieldPickerStyle())
	} else if m.sideline {
		body = followsView(m.theme, "Sideline", "A number moves to that row. enter keeps or drops that sport. Most relevant is every sport.", m.sidelineChoices(), m.followDigits, m.followCursor, width, fieldPickerStyle())
	} else if m.briefPick {
		body = followsView(m.theme, "Brief", "A number moves to that row. enter selects it. The first row of each section is the default.", m.briefChoices(), m.followDigits, m.followCursor, width, briefPickerStyle())
	} else {
		body = renderBoard(m.views, m.theme, width, m.height, m.focus, m.seconds, m.now, m.flashes)
	}
	if m.height > 1 {
		body = clipLines(body, m.height-1)
	}
	body += "\n" + statusLine(m.now, m.focusedTitle(), m.liveWord(), m.currentSuggestion(), m.theme, m.slot, m.notice, m.board, refineHint(m.focusedBayID()))
	if m.width <= 0 || m.height <= 0 {
		return body
	}
	return lipgloss.NewStyle().
		Background(lipgloss.Color(m.theme.Roles["bg"])).
		Width(m.width).
		MaxWidth(m.width).
		Height(m.height).
		MaxHeight(m.height).
		Render(body)
}

func main() {
	bayFlag := flag.String("bay", defaultBay, "bay to open")
	boardFlag := flag.Bool("board", false, "one window of selected bays")
	deskFlag := flag.String("desk", "", "start one process per bay for a desk and print the arrangement")
	themeFlag := flag.String("theme", "", "theme id (default: the bay theme, or night)")
	serverFlag := flag.String("server", "http://127.0.0.1:8787", "Oriel server for a live bay")
	fixtureFlag := flag.Bool("fixture", false, "render fixture panels instead of the live bay")
	flag.Parse()

	cwd, err := os.Getwd()
	if err != nil {
		fail(err)
	}
	root, err := findRoot(cwd)
	if err != nil {
		fail(err)
	}
	if *deskFlag != "" {
		desk, derr := loadDesk(root, *deskFlag)
		if derr != nil {
			fail(derr)
		}
		exe, derr := os.Executable()
		if derr != nil {
			fail(derr)
		}
		text, derr := launchProcesses(exe, *serverFlag, desk)
		if derr != nil {
			fail(derr)
		}
		fmt.Println(text)
		return
	}
	themeIDs, _ := listIDs(filepath.Join(root, "catalog", "themes"))
	bayIDs, _ := listIDs(filepath.Join(root, "catalog", "bays"))
	sort.Strings(themeIDs)
	sort.Strings(bayIDs)

	var views []bayView
	theme := Theme{}
	board := *boardFlag
	var layouts []boardLayout
	var slot int
	if board {
		prefs := loadBoardPrefs(root)
		layouts = prefs.Layouts
		slot = prefs.Slot
		themeName := prefs.Theme
		if *themeFlag != "" {
			themeName = *themeFlag
		}
		theme, err = loadTheme(root, themeName)
		if err != nil {
			fail(err)
		}
		for _, id := range prefs.Bays {
			view, verr := loadView(root, *serverFlag, id, themeName, *fixtureFlag)
			if verr != nil {
				fmt.Fprintf(os.Stderr, "oriel: %s\n", verr)
				continue
			}
			views = append(views, view)
		}
	} else {
		view, verr := loadView(root, *serverFlag, *bayFlag, *themeFlag, *fixtureFlag)
		if verr != nil {
			fail(verr)
		}
		views = []bayView{view}
		theme, err = loadTheme(root, resolveTheme(*themeFlag, view.bay.Theme))
		if err != nil {
			fail(err)
		}
	}
	live := false
	enabled := map[string]bool{}
	for _, view := range views {
		enabled[view.bay.ID] = true
		if view.live {
			live = true
		}
	}
	suggestion := Suggestion{}
	if !*fixtureFlag {
		if fetched, serr := fetchSuggestion(*serverFlag); serr == nil {
			suggestion = fetched
		}
	}
	program := tea.NewProgram(model{
		views:      views,
		theme:      theme,
		live:       live,
		board:      board,
		server:     *serverFlag,
		root:       root,
		suggestion: suggestion,
		fixture:    *fixtureFlag,
		now:        time.Now(),
		themeIDs:   themeIDs,
		bayIDs:     bayIDs,
		enabled:    enabled,
		layouts:    layouts,
		slot:       slot,
	}, tea.WithAltScreen())
	if _, err := program.Run(); err != nil {
		fail(err)
	}
}

func loadView(root, server, id, themeFlag string, fixture bool) (bayView, error) {
	bay, _, panels, err := openBay(root, id, themeFlag)
	if err != nil {
		return bayView{}, err
	}
	live := false
	if bay.ID == "brief" && !fixture {
		place, outlet, family := "", "", ""
		var choices []followChoice
		if sel, serr := fetchBriefSelection(server); serr == nil {
			place, outlet, family = sel.Place, sel.Outlet, sel.Family
			choices = briefChoicesFrom(sel.Items)
		}
		observation, ferr := fetchPanel(server, "weather-observation")
		panels = applyBriefPlace(panels, observation, ferr, place)
		wires, werr := fetchBayPanels(server, "wires")
		panels = applyBriefOutlet(panels, wires, werr, outlet)
		markets, merr := fetchBayPanels(server, "markets")
		panels = applyBriefFamily(panels, markets, merr, family)
		return bayView{
			bay: bay, panels: panels, live: false,
			briefPlace: place, briefOutlet: outlet, briefFamily: family, briefChoices: choices,
		}, nil
	}
	if shouldLive(bay.ID, fixture) {
		fetched, ferr := fetchBayPanels(server, bay.ID)
		panels, live = chooseWiresPanels(panels, fetched, ferr)
		if !live {
			fmt.Fprintf(os.Stderr, "oriel: %s server unreachable; showing fixtures\n", bay.ID)
		}
	}
	return bayView{bay: bay, panels: panels, live: live}, nil
}

type tickMsg time.Time

type clockMsg time.Time

type panelsMsg struct {
	bayID  string
	panels []Panel
	err    error
}

func scheduleRefresh(seconds int) tea.Cmd {
	if seconds < 1 {
		seconds = 30
	}
	return tea.Tick(time.Duration(seconds)*time.Second, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func scheduleClock() tea.Cmd {
	return tea.Tick(time.Second, func(t time.Time) tea.Msg {
		return clockMsg(t)
	})
}

type followResult struct {
	bayID  string
	name   string
	follow bool
	panels []Panel
	err    error
}

func (m model) hasField() bool {
	return m.hasBay("field")
}

func (m model) hasBay(id string) bool {
	for _, view := range m.views {
		if view.bay.ID == id {
			return true
		}
	}
	return false
}

func (m model) focusedBayID() string {
	index := m.focusedBay()
	if index < 0 || index >= len(m.views) {
		return ""
	}
	return m.views[index].bay.ID
}

func (m model) focusedBayTitle() string {
	index := m.focusedBay()
	if index < 0 || index >= len(m.views) {
		return "This bay"
	}
	if title := m.views[index].bay.Title; title != "" {
		return title
	}
	if id := m.views[index].bay.ID; id != "" {
		return id
	}
	return "This bay"
}

func (m model) picking() bool {
	return m.follows || m.sideline || m.briefPick
}

func (m *model) closePickers() {
	m.follows = false
	m.sideline = false
	m.briefPick = false
}

func (m model) commitFollow(buffer string, confirm bool) (tea.Model, tea.Cmd) {
	choices := m.pickerChoices()
	index, ready, valid := followPick(buffer, len(choices), confirm)
	if !valid {
		m.followDigits = ""
		return m, nil
	}
	m.followCursor = index
	m.followDigits = buffer
	if !ready {
		return m, nil
	}
	return m.toggleFollow(index)
}

func (m model) pickerChoices() []followChoice {
	if m.sideline {
		return m.sidelineChoices()
	}
	if m.briefPick {
		return m.briefChoices()
	}
	return m.fieldFollows()
}

func (m *model) stepPicker(delta int) {
	m.followDigits = ""
	count := len(m.pickerChoices())
	if count < 1 {
		m.followCursor = 0
		return
	}
	m.followCursor = (m.followCursor + delta + count) % count
}

func (m model) toggleFollow(index int) (tea.Model, tea.Cmd) {
	if m.sideline {
		return m.toggleSideline(index)
	}
	if m.briefPick {
		return m.selectBrief(index)
	}
	choices := m.fieldFollows()
	if index < 0 || index >= len(choices) {
		return m, nil
	}
	m.followDigits = ""
	choice := choices[index]
	return m, postFollowCmd(m.server, choice.ID, choice.Name, !choice.Followed)
}

func (m model) toggleSideline(index int) (tea.Model, tea.Cmd) {
	choices := m.sidelineChoices()
	if index < 0 || index >= len(choices) {
		return m, nil
	}
	m.followDigits = ""
	choice := choices[index]
	return m, postSidelineCmd(m.server, choice.ID, choice.Name, !choice.Followed)
}

func (m model) fieldFollows() []followChoice {
	for _, view := range m.views {
		if view.bay.ID != "field" {
			continue
		}
		var choices []followChoice
		for _, panel := range view.panels {
			for _, item := range panel.Items {
				if item.Row != "follow" {
					continue
				}
				id, _ := item.Fields["competition_id"].(string)
				if id == "" {
					continue
				}
				followed, _ := item.Fields["followed"].(bool)
				choices = append(choices, followChoice{ID: id, Name: item.Title, Followed: followed})
			}
		}
		return choices
	}
	return nil
}

func (m model) sidelineChoices() []followChoice {
	for _, view := range m.views {
		if view.bay.ID != "sideline" {
			continue
		}
		var choices []followChoice
		for _, panel := range view.panels {
			for _, item := range panel.Items {
				if item.Row != "follow" {
					continue
				}
				id, _ := item.Fields["sport"].(string)
				if id == "" {
					continue
				}
				followed, _ := item.Fields["followed"].(bool)
				choices = append(choices, followChoice{ID: id, Name: item.Title, Followed: followed})
			}
		}
		return choices
	}
	return nil
}

func (m model) briefChoices() []followChoice {
	for _, view := range m.views {
		if view.bay.ID == "brief" {
			return view.briefChoices
		}
	}
	return nil
}

func (m model) selectBrief(index int) (tea.Model, tea.Cmd) {
	choices := m.briefChoices()
	if index < 0 || index >= len(choices) {
		return m, nil
	}
	m.followDigits = ""
	choice := choices[index]
	return m, postBriefCmd(m.server, choice.Slot, choice.ID, choice.Name)
}

func (m *model) applyBrief(msg briefResult) {
	for i, view := range m.views {
		if view.bay.ID != "brief" {
			continue
		}
		panels := applyBriefPlace(view.panels, msg.observation, msg.obsErr, msg.place)
		panels = applyBriefOutlet(panels, msg.wires, msg.wireErr, msg.outlet)
		panels = applyBriefFamily(panels, msg.markets, msg.marketErr, msg.family)
		m.views[i].panels = panels
		m.views[i].briefPlace = msg.place
		m.views[i].briefOutlet = msg.outlet
		m.views[i].briefFamily = msg.family
		m.views[i].briefChoices = msg.choices
		return
	}
}

type briefResult struct {
	name        string
	place       string
	outlet      string
	family      string
	choices     []followChoice
	observation Panel
	obsErr      error
	wires       []Panel
	wireErr     error
	markets     []Panel
	marketErr   error
	err         error
}

func fetchBriefCmd(server string) tea.Cmd {
	return func() tea.Msg {
		sel, err := fetchBriefSelection(server)
		if err != nil {
			return briefResult{err: err}
		}
		return composeBrief(server, sel, "")
	}
}

func postBriefCmd(server, slot, id, name string) tea.Cmd {
	return func() tea.Msg {
		sel, err := postBriefSelection(server, slot, id)
		if err != nil {
			return briefResult{name: name, err: err}
		}
		return composeBrief(server, sel, name)
	}
}

func composeBrief(server string, sel briefSelection, name string) briefResult {
	observation, obsErr := fetchPanel(server, "weather-observation")
	wires, wireErr := fetchBayPanels(server, "wires")
	markets, marketErr := fetchBayPanels(server, "markets")
	return briefResult{
		name:        name,
		place:       sel.Place,
		outlet:      sel.Outlet,
		family:      sel.Family,
		choices:     briefChoicesFrom(sel.Items),
		observation: observation,
		obsErr:      obsErr,
		wires:       wires,
		wireErr:     wireErr,
		markets:     markets,
		marketErr:   marketErr,
	}
}

func postFollowCmd(server, competitionID, name string, follow bool) tea.Cmd {
	return func() tea.Msg {
		panels, err := postFollow(server, competitionID, follow)
		return followResult{bayID: "field", name: name, follow: follow, panels: panels, err: err}
	}
}

func postSidelineCmd(server, sport, name string, follow bool) tea.Cmd {
	return func() tea.Msg {
		panels, err := postSideline(server, sport, follow)
		return followResult{bayID: "sideline", name: name, follow: follow, panels: panels, err: err}
	}
}

func fetchPanelsCmd(server, bayID string) tea.Cmd {
	return func() tea.Msg {
		panels, err := fetchBayPanels(server, bayID)
		return panelsMsg{bayID: bayID, panels: panels, err: err}
	}
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, "oriel:", err)
	os.Exit(1)
}
