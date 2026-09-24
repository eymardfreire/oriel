package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type model struct {
	bay        Bay
	theme      Theme
	panels     []Panel
	width      int
	height     int
	top        int
	live       bool
	server     string
	root       string
	suggestion Suggestion
}

func (m model) Init() tea.Cmd {
	if !m.live || m.bay.RefreshSeconds < 1 {
		return nil
	}
	return scheduleRefresh(m.bay.RefreshSeconds)
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.width = msg.Width
		m.height = msg.Height
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c", "esc":
			return m, tea.Quit
		case "j", "down":
			if m.top < len(m.panels)-1 {
				m.top++
			}
		case "k", "up":
			if m.top > 0 {
				m.top--
			}
		case "a":
			if m.suggestion.DeskID == "" {
				break
			}
			kept, deskID := applySuggestion(m.panels, m.suggestion.DeskID)
			m.panels = kept
			desk, err := loadDesk(m.root, deskID)
			if err != nil {
				break
			}
			exe, err := os.Executable()
			if err != nil {
				break
			}
			text, err := launchProcesses(exe, m.server, desk)
			if err == nil {
				fmt.Fprintln(os.Stderr, text)
			}
		}
	case tickMsg:
		if !m.live {
			return m, nil
		}
		return m, tea.Batch(fetchPanelsCmd(m.server, m.bay.ID), scheduleRefresh(m.bay.RefreshSeconds))
	case panelsMsg:
		m.panels = mergeRefresh(m.panels, msg.panels, msg.err)
		if m.top >= len(m.panels) {
			m.top = 0
		}
	}
	return m, nil
}

func (m model) View() string {
	width := m.width
	if width <= 0 {
		width = 80
	}
	panels := m.panels
	if m.top > 0 && m.top < len(panels) {
		panels = panels[m.top:]
	}
	body := renderBay(m.bay, panels, m.theme, width)
	if m.suggestion.DeskID != "" {
		body += "\n" + suggestionLine(m.suggestion)
	}
	if m.width <= 0 || m.height <= 0 {
		return body
	}
	return lipgloss.NewStyle().
		Background(lipgloss.Color(m.theme.Roles["bg"])).
		Width(m.width).
		Height(m.height).
		Render(body)
}

func main() {
	bayFlag := flag.String("bay", defaultBay, "bay to open")
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
	bay, theme, panels, err := openBay(root, *bayFlag, *themeFlag)
	if err != nil {
		fail(err)
	}
	live := false
	if bay.ID == "brief" && !*fixtureFlag {
		observation, ferr := fetchPanel(*serverFlag, "weather-observation")
		panels = applyBriefWeather(panels, observation, ferr)
	}
	if shouldLive(bay.ID, *fixtureFlag) {
		fetched, ferr := fetchBayPanels(*serverFlag, bay.ID)
		panels, live = chooseWiresPanels(panels, fetched, ferr)
		if !live {
			fmt.Fprintf(os.Stderr, "oriel: %s server unreachable; showing fixtures\n", bay.ID)
		}
	}
	suggestion := Suggestion{}
	if !*fixtureFlag {
		if fetched, serr := fetchSuggestion(*serverFlag); serr == nil {
			suggestion = fetched
		}
	}
	program := tea.NewProgram(model{
		bay:        bay,
		theme:      theme,
		panels:     panels,
		live:       live,
		server:     *serverFlag,
		root:       root,
		suggestion: suggestion,
	}, tea.WithAltScreen())
	if _, err := program.Run(); err != nil {
		fail(err)
	}
}

type tickMsg time.Time

type panelsMsg struct {
	panels []Panel
	err    error
}

func scheduleRefresh(seconds int) tea.Cmd {
	return tea.Tick(time.Duration(seconds)*time.Second, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

func fetchPanelsCmd(server, bayID string) tea.Cmd {
	return func() tea.Msg {
		panels, err := fetchBayPanels(server, bayID)
		return panelsMsg{panels: panels, err: err}
	}
}

func fail(err error) {
	fmt.Fprintln(os.Stderr, "oriel:", err)
	os.Exit(1)
}
