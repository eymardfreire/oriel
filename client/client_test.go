package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"testing"

	"github.com/charmbracelet/lipgloss"
	"github.com/muesli/termenv"
)

func TestMain(m *testing.M) {
	lipgloss.SetColorProfile(termenv.TrueColor)
	os.Exit(m.Run())
}

func TestShippedThemesUseDesignHex(t *testing.T) {
	root := testRoot(t)
	want := map[string]map[string]string{
		"night":  {"mode": "dark", "bg": "#141414", "text": "#e6e6e6", "muted": "#8a8a8a", "accent": "#7aa2f7", "up": "#7dcea0", "down": "#e07a7a"},
		"day":    {"mode": "light", "bg": "#f7f6f3", "text": "#1c1c1c", "accent": "#2f5d9f"},
		"wire":   {"mode": "dark", "bg": "#0c0c0c", "accent": "#f0c14a"},
		"paper":  {"mode": "light", "bg": "#f3efe6", "accent": "#8c3a2f"},
		"fog":    {"mode": "dark", "bg": "#1a1d21", "text": "#c5c8ce"},
		"signal": {"mode": "dark", "bg": "#000000", "text": "#ffffff", "accent": "#4da3ff"},
	}
	ids := mustIDs(t, filepath.Join(root, "catalog", "themes"))
	if strings.Join(ids, ",") != "day,fog,night,paper,signal,wire" {
		t.Fatalf("themes = %v", ids)
	}
	for id, expect := range want {
		theme, err := loadTheme(root, id)
		if err != nil {
			t.Fatal(err)
		}
		if theme.Mode != expect["mode"] {
			t.Errorf("%s mode = %s", id, theme.Mode)
		}
		for role, hex := range expect {
			if role == "mode" {
				continue
			}
			if theme.Roles[role] != hex {
				t.Errorf("%s %s = %s, want %s", id, role, theme.Roles[role], hex)
			}
		}
	}
}

func TestShippedDesks(t *testing.T) {
	root := testRoot(t)
	ids := mustIDs(t, filepath.Join(root, "catalog", "desks"))
	if strings.Join(ids, ",") != "brief,fantasy,far,field,markets,storm,three,trade,wires" {
		t.Fatalf("desks = %v", ids)
	}
	for _, id := range ids {
		desk, err := loadDesk(root, id)
		if err != nil {
			t.Fatal(err)
		}
		if id == "three" {
			got := bayIDs(desk)
			if strings.Join(got, ",") != "wires,markets,field" {
				t.Fatalf("three bays = %v", got)
			}
			continue
		}
		if len(desk.Bays) != 1 || desk.Bays[0].ID != id {
			t.Errorf("desk %s bays = %+v", id, desk.Bays)
		}
	}
	fantasy, err := loadDesk(root, "fantasy")
	if err != nil {
		t.Fatal(err)
	}
	if bayIDs(fantasy)[0] == "field" {
		t.Fatal("fantasy desk includes the field bay")
	}
}

func TestFixturesAreSampleData(t *testing.T) {
	root := testRoot(t)
	want := map[string]string{
		"fixture-wires-headline":      "headline",
		"fixture-markets-quote":       "quote",
		"fixture-weather-observation": "observation",
		"fixture-sports-row":          "score",
		"fixture-fantasy-lineup":      "fantasy",
		"fixture-trade-headline":      "headline",
		"fixture-weather-forecast":    "forecast",
		"fixture-weather-alert":       "alert",
		"fixture-weather-news":        "headline",
	}
	ids := mustIDs(t, filepath.Join(root, "fixtures"))
	if len(ids) != len(want) {
		t.Fatalf("fixtures = %v", ids)
	}
	for id, row := range want {
		raw, err := os.ReadFile(filepath.Join(root, "fixtures", id+".json"))
		if err != nil {
			t.Fatal(err)
		}
		if strings.Contains(string(raw), "#") {
			t.Fatalf("%s contains a color", id)
		}
		panel, err := loadPanel(root, id)
		if err != nil {
			t.Fatal(err)
		}
		if !panel.Fixture || panel.Stale || panel.StaleReason != "" {
			t.Fatalf("%s fixture=%v stale=%v reason=%q", id, panel.Fixture, panel.Stale, panel.StaleReason)
		}
		if len(panel.Items) != 1 || panel.Items[0].Row != row {
			t.Fatalf("%s items = %+v", id, panel.Items)
		}
	}
}

func TestBriefDefaultsToNightAndThemeFlagOverrides(t *testing.T) {
	root := testRoot(t)
	if resolveTheme("", "") != "night" {
		t.Fatal("empty theme did not fall back to night")
	}
	_, theme, panels, err := openBay(root, "brief", "")
	if err != nil {
		t.Fatal(err)
	}
	if theme.ID != "night" {
		t.Fatalf("theme = %s", theme.ID)
	}
	if len(panels) != 3 {
		t.Fatalf("brief panels = %d", len(panels))
	}
	day, err := openThemed(root, "markets", "day")
	if err != nil {
		t.Fatal(err)
	}
	if day.ID != "day" || day.Mode != "light" {
		t.Fatalf("override = %+v", day)
	}
	if _, _, _, err := openBay(root, "three", ""); err == nil || !strings.Contains(err.Error(), "desk") {
		t.Fatalf("three error = %v", err)
	}
}

func TestHairlineFixtureOmitsStaleMarker(t *testing.T) {
	root := testRoot(t)
	bay, theme, panels, err := openBay(root, "wires", "")
	if err != nil {
		t.Fatal(err)
	}
	out := renderBay(bay, panels, theme, 80)
	plain := stripANSI(out)
	if !strings.Contains(plain, "Fixture headline") || !strings.Contains(plain, "fixture") {
		t.Fatalf("plain = %q", plain)
	}
	if strings.Contains(plain, "stale") {
		t.Fatalf("fresh panel showed stale: %q", plain)
	}
	if !strings.Contains(out, "┌") {
		t.Fatal("expected a hairline border")
	}
	if strings.HasPrefix(strings.TrimLeft(plain, "\n"), "Oriel") {
		t.Fatal("rendered a chrome bar")
	}
}

func TestQuoteDirectionUsesThemeRoles(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	up := renderBay(Bay{Layout: "stack"}, []Panel{quotePanel(1.25)}, theme, 80)
	if !strings.Contains(up, roleSequence(theme, "up")+"+1.25") {
		t.Fatal("positive change did not use the up role")
	}
	down := renderBay(Bay{Layout: "stack"}, []Panel{quotePanel(-2)}, theme, 80)
	if !strings.Contains(down, roleSequence(theme, "down")+"-2") {
		t.Fatal("negative change did not use the down role")
	}
	missing := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title:  "Markets",
		Domain: "markets",
		Items: []Item{{
			Title:  "Quote",
			Row:    "quote",
			Source: "Oriel fixture",
			Fields: map[string]any{"symbol": "FIX", "price": 100.0},
		}},
	}}, theme, 80))
	if !strings.Contains(missing, "FIX") || !strings.Contains(missing, "100") {
		t.Fatalf("missing change row = %q", missing)
	}
	if regexp.MustCompile(`(^|[^\d])0([^\d]|$)`).MatchString(missing) {
		t.Fatalf("fabricated a zero change: %q", missing)
	}
}

func TestEmptyBayNamesTheDomain(t *testing.T) {
	root := testRoot(t)
	bay, theme, panels, err := openBay(root, "storm", "")
	if err != nil {
		t.Fatal(err)
	}
	plain := stripANSI(renderBay(bay, panels, theme, 60))
	if !strings.Contains(plain, "Fixture Place") || !strings.Contains(plain, "fixture") {
		t.Fatalf("storm fixture = %q", plain)
	}
	far, theme, panels, err := openBay(root, "far", "")
	if err != nil {
		t.Fatal(err)
	}
	plain = stripANSI(renderBay(far, panels, theme, 60))
	if !strings.Contains(plain, "sports has no items") {
		t.Fatalf("far empty = %q", plain)
	}
}

func TestStaleMarkerUsesStaleRole(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	panel, err := loadPanel(root, "fixture-wires-headline")
	if err != nil {
		t.Fatal(err)
	}
	panel.Stale = true
	panel.StaleReason = "timeout"
	out := renderBay(Bay{ID: "wires", Title: "Wires", Layout: "stack"}, []Panel{panel}, theme, 80)
	if !strings.Contains(stripANSI(out), "stale timeout") {
		t.Fatalf("stale header missing: %q", stripANSI(out))
	}
	if !strings.Contains(out, roleSequence(theme, "stale")+"stale timeout") {
		t.Fatal("stale marker did not use the stale role")
	}
}

func roleSequence(theme Theme, role string) string {
	return strings.TrimSuffix(fg(theme, role).Render("X"), "X\x1b[0m")
}

func quotePanel(change float64) Panel {
	return Panel{
		Title:  "Markets",
		Domain: "markets",
		Items: []Item{{
			Title:  "Quote",
			Row:    "quote",
			Source: "Oriel fixture",
			Fields: map[string]any{"symbol": "FIX", "price": 100.0, "change": change},
		}},
	}
}

func openThemed(root, bayID, themeID string) (Theme, error) {
	_, theme, _, err := openBay(root, bayID, themeID)
	return theme, err
}

func bayIDs(desk Desk) []string {
	ids := make([]string, len(desk.Bays))
	for i, bay := range desk.Bays {
		ids[i] = bay.ID
	}
	return ids
}

func mustIDs(t *testing.T, dir string) []string {
	t.Helper()
	ids, err := listIDs(dir)
	if err != nil {
		t.Fatal(err)
	}
	sort.Strings(ids)
	return ids
}

func testRoot(t *testing.T) string {
	t.Helper()
	cwd, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	root, err := findRoot(cwd)
	if err != nil {
		t.Fatal(err)
	}
	return root
}

var ansiPattern = regexp.MustCompile(`\x1b\[[0-9;]*m`)

func stripANSI(value string) string {
	return ansiPattern.ReplaceAllString(value, "")
}

func TestLiveWiresPayloadRendersOutletAndTime(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/bays/wires" {
			t.Errorf("path = %s", r.URL.Path)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"id": "wires",
			"panels": [{
				"id": "wires-technology",
				"domain": "wires",
				"title": "Technology",
				"updated_at": "2026-09-23T22:01:17Z",
				"stale": false,
				"stale_reason": "",
				"items": [{
					"id": "bbc-technology:1",
					"title": "Live headline",
					"source": "BBC News",
					"source_url": "https://example.test/story",
					"observed_at": "2026-09-23T22:01:17Z",
					"row": "headline",
					"fields": {"desk": "technology"}
				}]
			}]
		}`))
	}))
	defer server.Close()

	bay, err := loadBay(root, "wires")
	if err != nil {
		t.Fatal(err)
	}
	fixtures := mustFixturePanels(t, root, bay)
	fetched, err := fetchBayPanels(server.URL, "wires")
	if err != nil {
		t.Fatal(err)
	}
	panels, live := chooseWiresPanels(fixtures, fetched, nil)
	if !live || len(panels) != 1 {
		t.Fatalf("live=%v panels=%d", live, len(panels))
	}
	plain := stripANSI(renderBay(bay, panels, theme, 80))
	if !strings.Contains(plain, "Live headline") || !strings.Contains(plain, "BBC News") {
		t.Fatalf("plain = %q", plain)
	}
	if !strings.Contains(plain, "technology") || !strings.Contains(plain, "2026-09-23 22:01 UTC") {
		t.Fatalf("plain = %q", plain)
	}
	if strings.Contains(plain, "fixture") || strings.Contains(plain, "stale") {
		t.Fatalf("live panel marked fixture or stale: %q", plain)
	}
}

func TestWiresFallsBackToFixturesAndKeepsThemOnRefreshFailure(t *testing.T) {
	root := testRoot(t)
	bay, err := loadBay(root, "wires")
	if err != nil {
		t.Fatal(err)
	}
	fixtures := mustFixturePanels(t, root, bay)
	panels, live := chooseWiresPanels(fixtures, nil, fmt.Errorf("connection refused"))
	if live || len(panels) != 1 || !panels[0].Fixture {
		t.Fatalf("live=%v panels=%+v", live, panels)
	}
	empty, live := chooseWiresPanels(fixtures, []Panel{}, nil)
	if !live || len(empty) != 0 {
		t.Fatalf("empty live payload fell back: live=%v len=%d", live, len(empty))
	}
	if !shouldLive("markets", false) || shouldLive("markets", true) || shouldLive("wires", true) || !shouldLive("wires", false) {
		t.Fatal("live selection changed")
	}
	if !shouldLive("trade", false) || shouldLive("trade", true) || shouldLive("storm", true) || !shouldLive("storm", false) {
		t.Fatal("trade live selection changed")
	}
	if !shouldLive("field", false) || !shouldLive("far", false) || !shouldLive("fantasy", false) || shouldLive("fantasy", true) {
		t.Fatal("sports live selection changed")
	}
	kept := mergeRefresh(panels, nil, fmt.Errorf("connection refused"))
	if len(kept) != 1 || !kept[0].Stale || kept[0].StaleReason != "server unreachable" {
		t.Fatalf("kept = %+v", kept)
	}
	if kept[0].Items[0].Title != panels[0].Items[0].Title {
		t.Fatal("refresh failure replaced the last payload")
	}
	plain := stripANSI(renderBay(Bay{ID: "wires", Title: "Wires", Layout: "stack"}, []Panel{{
		Domain: "wires",
		Title:  "Technology",
	}}, mustTheme(t, root), 60))
	if !strings.Contains(plain, "wires has no items") {
		t.Fatalf("empty = %q", plain)
	}
}

func mustFixturePanels(t *testing.T, root string, bay Bay) []Panel {
	t.Helper()
	panels := make([]Panel, 0, len(bay.Panels))
	for _, id := range bay.Panels {
		panel, err := loadPanel(root, id)
		if err != nil {
			t.Fatal(err)
		}
		panels = append(panels, panel)
	}
	return panels
}

func mustTheme(t *testing.T, root string) Theme {
	t.Helper()
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	return theme
}

func TestLiveMarketQuoteShowsDelayAndDirection(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/bays/markets" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"id": "markets",
			"panels": [{
				"id": "markets-fx",
				"domain": "markets",
				"title": "FX",
				"updated_at": "2026-09-23T00:00:00Z",
				"stale": false,
				"stale_reason": "",
				"items": [
					{
						"id": "fx:EURUSD",
						"title": "Euro / US dollar",
						"source": "Frankfurter",
						"source_url": "https://www.frankfurter.app/",
						"observed_at": "2026-09-23T00:00:00Z",
						"row": "quote",
						"fields": {"symbol": "EURUSD", "price": 1.1411, "change": -2, "delayed": true}
					},
					{
						"id": "fx:USDJPY",
						"title": "US dollar / Yen",
						"source": "Frankfurter",
						"source_url": "https://www.frankfurter.app/",
						"observed_at": "2026-09-23T00:00:00Z",
						"row": "quote",
						"fields": {"symbol": "USDJPY", "price": 157.92, "delayed": true}
					}
				]
			}]
		}`))
	}))
	defer server.Close()

	bay, err := loadBay(root, "markets")
	if err != nil {
		t.Fatal(err)
	}
	fixtures := mustFixturePanels(t, root, bay)
	fetched, err := fetchBayPanels(server.URL, "markets")
	if err != nil {
		t.Fatal(err)
	}
	panels, live := chooseWiresPanels(fixtures, fetched, nil)
	if !live {
		t.Fatal("expected the live markets payload")
	}
	out := renderBay(bay, panels, theme, 80)
	plain := stripANSI(out)
	if !strings.Contains(plain, "EURUSD") || !strings.Contains(plain, "1.1411") || !strings.Contains(plain, "Frankfurter") {
		t.Fatalf("plain = %q", plain)
	}
	if !strings.Contains(plain, "delayed") || strings.Contains(plain, "fixture") {
		t.Fatalf("delay marker = %q", plain)
	}
	if !strings.Contains(out, roleSequence(theme, "down")+"-2") {
		t.Fatal("negative change did not use the down role")
	}
	if !strings.Contains(plain, "USDJPY") || !strings.Contains(plain, "157.92") {
		t.Fatalf("missing price = %q", plain)
	}
	jpy := plain[strings.Index(plain, "USDJPY"):]
	if strings.Contains(jpy, "0.000") || strings.Contains(strings.Fields(jpy)[0]+strings.Fields(jpy)[1], "157.920") {
		t.Fatalf("fabricated a change: %q", jpy)
	}
}

func TestLiveTradeShowsTitleSourceAndTime(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/bays/trade" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{
			"id": "trade",
			"panels": [{
				"id": "trade-policy",
				"domain": "trade",
				"title": "Policy",
				"updated_at": "2026-09-23T22:01:17Z",
				"stale": false,
				"stale_reason": "",
				"items": [{
					"id": "wto-news:1",
					"title": "Tariff notice",
					"source": "WTO",
					"source_url": "https://example.test/policy",
					"observed_at": "2026-09-23T22:01:17Z",
					"row": "headline",
					"fields": {"family": "policy"}
				}]
			}]
		}`))
	}))
	defer server.Close()

	bay, err := loadBay(root, "trade")
	if err != nil {
		t.Fatal(err)
	}
	fixtures := mustFixturePanels(t, root, bay)
	fetched, err := fetchBayPanels(server.URL, "trade")
	if err != nil {
		t.Fatal(err)
	}
	panels, live := chooseWiresPanels(fixtures, fetched, nil)
	if !live || panels[0].Items[0].Title != "Tariff notice" {
		t.Fatal("expected the live trade payload")
	}
	plain := stripANSI(renderBay(bay, panels, theme, 80))
	if !strings.Contains(plain, "Tariff notice") || !strings.Contains(plain, "WTO") {
		t.Fatalf("plain = %q", plain)
	}
	if !strings.Contains(plain, "2026-09-23 22:01 UTC") || strings.Contains(plain, "fixture") {
		t.Fatalf("plain = %q", plain)
	}
	offline, live := chooseWiresPanels(fixtures, nil, fmt.Errorf("connection refused"))
	if live || !offline[0].Fixture || offline[0].Items[0].Title != "Fixture trade item" {
		t.Fatalf("fallback = %+v live=%v", offline, live)
	}
}

func TestStormKeepsWeatherApartFromNews(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	brief, err := loadBay(root, "brief")
	if err != nil {
		t.Fatal(err)
	}
	for _, id := range brief.Panels {
		if id == "fixture-weather-news" {
			t.Fatal("brief includes weather news")
		}
	}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		if r.URL.Path == "/panels/weather-observation" {
			_, _ = w.Write([]byte(`{
				"id": "weather-observation",
				"domain": "weather",
				"title": "Observation",
				"updated_at": "2026-09-23T18:00:00Z",
				"stale": false,
				"stale_reason": "",
				"items": [
					{
						"id": "observation:home",
						"title": "Home",
						"source": "Open-Meteo",
						"source_url": "https://open-meteo.com/",
						"observed_at": "2026-09-23T18:00:00Z",
						"row": "observation",
						"fields": {"place": "Home", "temperature_c": 22.5, "condition": "mainly clear", "configured": true, "home": true}
					},
					{
						"id": "observation:camp",
						"title": "Camp",
						"source": "Open-Meteo",
						"source_url": "https://open-meteo.com/",
						"observed_at": "2026-09-23T18:00:00Z",
						"row": "observation",
						"fields": {"place": "Camp", "temperature_c": 10, "configured": true, "home": false}
					}
				]
			}`))
			return
		}
		if r.URL.Path != "/bays/storm" {
			http.NotFound(w, r)
			return
		}
		_, _ = w.Write([]byte(`{
			"id": "storm",
			"panels": [
				{"id": "weather-observation", "domain": "weather", "title": "Observation", "updated_at": "2026-09-23T18:00:00Z", "stale": false, "stale_reason": "", "items": [{"id": "o", "title": "Home", "source": "Open-Meteo", "source_url": "", "observed_at": "2026-09-23T18:00:00Z", "row": "observation", "fields": {"place": "Home", "temperature_c": 22.5, "configured": true}}]},
				{"id": "weather-forecast", "domain": "weather", "title": "Forecast", "updated_at": "2026-09-23T18:00:00Z", "stale": false, "stale_reason": "", "items": [{"id": "f", "title": "Home", "source": "Open-Meteo", "source_url": "", "observed_at": "2026-09-23T00:00:00Z", "row": "forecast", "fields": {"place": "Home", "period": "2026-09-24", "temperature_high_c": 26}}]},
				{"id": "weather-alerts", "domain": "weather", "title": "Alerts", "updated_at": "2026-09-23T18:00:00Z", "stale": false, "stale_reason": "", "items": [{"id": "a", "title": "Severe thunderstorm warning", "source": "NWS Test", "source_url": "", "observed_at": "2026-09-23T18:00:00Z", "row": "alert", "fields": {"severity": "Severe", "headline": "Severe thunderstorm warning"}}]},
				{"id": "weather-news", "domain": "weather-news", "title": "Weather news", "updated_at": "2026-09-23T18:00:00Z", "stale": false, "stale_reason": "", "items": [{"id": "n", "title": "Storm story", "source": "National Hurricane Center", "source_url": "https://example.test/storm", "observed_at": "2026-09-23T18:00:00Z", "row": "headline", "fields": {}}]}
			]
		}`))
	}))
	defer server.Close()

	bay, err := loadBay(root, "storm")
	if err != nil {
		t.Fatal(err)
	}
	fixtures := mustFixturePanels(t, root, bay)
	fetched, err := fetchBayPanels(server.URL, "storm")
	if err != nil {
		t.Fatal(err)
	}
	panels, live := chooseWiresPanels(fixtures, fetched, nil)
	if !live || len(panels) != 4 {
		t.Fatalf("live=%v panels=%d", live, len(panels))
	}
	out := renderBay(bay, panels, theme, 80)
	plain := stripANSI(out)
	if !strings.Contains(plain, "22.5") || !strings.Contains(plain, "26") || !strings.Contains(plain, "Storm story") {
		t.Fatalf("plain = %q", plain)
	}
	if !strings.Contains(out, roleSequence(theme, "down")+"Severe") {
		t.Fatal("severe alert did not use the down role")
	}
	briefPanels := mustFixturePanels(t, root, brief)
	kept := applyBriefWeather(briefPanels, Panel{}, fmt.Errorf("down"))
	if kept[0].Items[0].Title != "Fixture observation" {
		t.Fatal("brief replaced weather while the server was down")
	}
	observation, err := fetchPanel(server.URL, "weather-observation")
	if err != nil {
		t.Fatal(err)
	}
	swapped := applyBriefWeather(briefPanels, observation, nil)
	if swapped[0].Items[0].Fields["place"] != "Home" || len(swapped) != 3 || len(swapped[0].Items) != 1 {
		t.Fatalf("brief weather = %+v", swapped)
	}
	for _, panel := range swapped {
		if panel.Domain == "weather-news" {
			t.Fatal("brief gained weather news")
		}
	}
}

func TestSuggestionStaysUntilApplied(t *testing.T) {
	panels := []Panel{{ID: "fixture-wires-headline", Title: "Wires", Domain: "wires"}}
	line := suggestionLine(Suggestion{DeskID: "three", Reason: "New York session is open"})
	if !strings.Contains(line, "three") || !strings.Contains(line, "New York session is open") || !strings.Contains(line, "suggestion") {
		t.Fatalf("line = %q", line)
	}
	kept, desk := applySuggestion(panels, "three")
	if desk != "three" || kept[0].ID != panels[0].ID || len(kept) != 1 {
		t.Fatal("apply changed the running panels")
	}
}

func TestLauncherPrintsArrangementWithoutClaimingWindows(t *testing.T) {
	root := testRoot(t)
	three, err := loadDesk(root, "three")
	if err != nil {
		t.Fatal(err)
	}
	var started []string
	text, err := startDesk(three, func(bayID string) error {
		started = append(started, bayID)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(started, ",") != "wires,markets,field" {
		t.Fatalf("started = %v", started)
	}
	if !strings.Contains(text, "desk three") || !strings.Contains(text, "wires — Headlines") || strings.Contains(text, "fantasy") {
		t.Fatalf("arrangement = %q", text)
	}
	fantasy, err := loadDesk(root, "fantasy")
	if err != nil {
		t.Fatal(err)
	}
	started = nil
	text, err = startDesk(fantasy, func(bayID string) error {
		started = append(started, bayID)
		return nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(started, ",") != "fantasy" || strings.Contains(text, "field —") {
		t.Fatalf("fantasy launch = %q %v", text, started)
	}
}

func TestSportsRowsStayHonest(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	delayed := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Field", Domain: "sports",
		Items: []Item{{Title: "Match", Row: "score", Source: "Lagged board", Fields: map[string]any{
			"home": "Home Side", "away": "Away Side", "score": "1-0", "state": "in progress", "tier": "delayed",
		}}},
	}}, theme, 80))
	if !strings.Contains(delayed, "delayed") || !strings.Contains(delayed, "1-0") || !strings.Contains(delayed, "Lagged board") {
		t.Fatalf("delayed = %q", delayed)
	}
	scheduled := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Field", Domain: "sports",
		Items: []Item{{Title: "Match", Row: "score", Source: "Fixture board", Fields: map[string]any{
			"home": "Home Side", "away": "Away Side", "state": "scheduled 2026-09-24 18:00 UTC", "tier": "schedule",
		}}},
	}}, theme, 80))
	if strings.Contains(scheduled, "3-0") || !strings.Contains(scheduled, "Home Side") || !strings.Contains(scheduled, "18:00") {
		t.Fatalf("schedule = %q", scheduled)
	}
	far := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Far Desk", Domain: "sports",
		Items: []Item{{Title: "North defeated South 2-1", Row: "score", Source: "Village report", Fields: map[string]any{
			"home": "North", "away": "South", "score": "2-1", "state": "final", "tier": "far", "factual": true, "factual_line": "North defeated South 2-1",
		}}},
	}}, theme, 80))
	if !strings.Contains(far, "factual line") || !strings.Contains(far, "Village report") {
		t.Fatalf("far = %q", far)
	}
	quote := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Far Desk", Domain: "sports",
		Items: []Item{{Title: "clip", Row: "score", Source: "Village report", Fields: map[string]any{"excerpt": "North won the cup", "tier": "far"}}},
	}}, theme, 80))
	if !strings.Contains(quote, "\"North won the cup\"") || strings.Contains(quote, "defeated") {
		t.Fatalf("excerpt = %q", quote)
	}
	blank := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Pins", Domain: "sports",
		Items: []Item{{Title: "Scorer", Row: "fantasy", Source: "", Fields: map[string]any{"player": "Scorer", "position": "WR", "team": "FIX", "slot": "pin"}}},
	}}, theme, 80))
	if !strings.Contains(blank, "Scorer") || !strings.Contains(blank, "WR") || !strings.Contains(blank, "FIX") {
		t.Fatalf("blank points = %q", blank)
	}
	if strings.Contains(blank, "0") {
		t.Fatalf("invented points: %q", blank)
	}
	marked := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Lineup", Domain: "sports",
		Items: []Item{{Title: "First Back", Row: "fantasy", Source: "Sleeper", Fields: map[string]any{
			"player": "First Back", "position": "RB", "team": "FIX", "slot": "RB", "pinned": true, "points": 18.5, "week": 3,
		}}},
	}}, theme, 80))
	if !strings.Contains(marked, "pin") || !strings.Contains(marked, "18.5") || !strings.Contains(marked, "Sleeper") {
		t.Fatalf("pinned = %q", marked)
	}
}
