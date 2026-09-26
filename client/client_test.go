package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"

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
		"night":  {"mode": "dark", "bg": "#0e1116", "text": "#e8eef7", "muted": "#8b9bb0", "accent": "#7eb6ff", "up": "#3dd68c", "down": "#ff6b6b"},
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
	if !strings.Contains(up, roleSequence(theme, "up")+"+1.25") || !strings.Contains(up, "▬") || strings.Contains(up, "█") {
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
	if !shouldLive("field", false) || !shouldLive("far", false) || !shouldLive("fantasy", false) || !shouldLive("sideline", false) || shouldLive("fantasy", true) {
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
	if !strings.Contains(line, "three") || !strings.Contains(line, "New York session is open") || !strings.Contains(line, "suggestion") || !strings.Contains(line, "Press a") {
		t.Fatalf("line = %q", line)
	}
	kept, desk := applySuggestion(panels, "three")
	if desk != "three" || kept[0].ID != panels[0].ID || len(kept) != 1 {
		t.Fatal("apply changed the running panels")
	}
}

func TestColumnBandsAndWeatherGlyph(t *testing.T) {
	if columnCount(80) != 1 || columnCount(120) != 2 || columnCount(180) != 3 || columnCount(260) != 4 {
		t.Fatalf("bands = %d %d %d %d", columnCount(80), columnCount(120), columnCount(180), columnCount(260))
	}
	if weatherGlyph("rain") == "" || weatherGlyph("") != "" {
		t.Fatal("glyph mapping")
	}
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	rain := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Observation", Domain: "weather",
		Items: []Item{{Row: "observation", Source: "Open-Meteo", Fields: map[string]any{
			"place": "Tampa", "condition": "rain", "temperature_c": 22.5, "humidity_pct": 80.0,
		}}},
	}}, theme, 80))
	if !strings.Contains(rain, "🌧") || !strings.Contains(rain, "80%") || strings.Contains(rain, "km/h") {
		t.Fatalf("observation = %s", rain)
	}
	quiet := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Markets", Domain: "markets",
		Items: []Item{{Row: "quote", Fields: map[string]any{"symbol": "SPX", "price": 1.0}}},
	}}, theme, 80))
	if strings.Contains(quiet, "█") || strings.Contains(quiet, "▬") {
		t.Fatal("missing change drew a bar")
	}
	blank := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Markets", Domain: "markets",
		Items: []Item{{Row: "quote", Title: "FTSE 100", Fields: map[string]any{"symbol": "FTSE"}}},
	}}, theme, 80))
	if !strings.Contains(blank, "FTSE") || strings.Contains(blank, "█") || strings.Contains(blank, "▬") || strings.Contains(blank, "0") {
		t.Fatalf("missing quote = %s", blank)
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

func TestLiveMarkUsesServerPoll(t *testing.T) {
	updated := time.Date(2026, 9, 24, 16, 0, 0, 0, time.UTC)
	panel := Panel{UpdatedAt: updated.Format(time.RFC3339), RefreshSeconds: 60}
	if liveMark(panel, updated.Add(60*time.Second), 30) != "●" {
		t.Fatal("mark went hollow inside the server poll")
	}
	if liveMark(panel, updated.Add(71*time.Second), 30) != "○" {
		t.Fatal("mark stayed filled past the server poll plus margin")
	}
	panel.Stale = true
	if liveMark(panel, updated, 30) != "" {
		t.Fatal("stale panel showed a live mark")
	}
	fallback := Panel{UpdatedAt: updated.Format(time.RFC3339)}
	if liveMark(fallback, updated.Add(31*time.Second), 30) != "○" {
		t.Fatal("missing refresh_seconds did not use the bay refresh")
	}
}

func TestSuggestionHiddenWhenDeskIsShown(t *testing.T) {
	suggestion := Suggestion{DeskID: "markets", Reason: "New York session is open"}
	hidden := visibleSuggestion(suggestion, []string{"markets"}, []string{"markets"})
	if suggestionLine(hidden) != "" {
		t.Fatal("suggestion stayed visible on the markets bay")
	}
	shown := visibleSuggestion(suggestion, []string{"markets"}, []string{"wires"})
	line := suggestionLine(shown)
	if !strings.Contains(line, "markets") || !strings.Contains(line, "Press a") {
		t.Fatalf("line = %q", line)
	}
	partial := visibleSuggestion(Suggestion{DeskID: "three", Reason: "session"}, []string{"wires", "markets", "field"}, []string{"wires"})
	if partial.DeskID != "three" {
		t.Fatal("hid a desk that is only partly shown")
	}
}

func TestLaunchDetachesOutput(t *testing.T) {
	command := launchCommand("oriel", "http://127.0.0.1:8787", "markets")
	if command.Stdout != nil || command.Stderr != nil {
		t.Fatal("launched process writes into the current window")
	}
}

func TestBoardApplySwapsToTheSuggestedDesk(t *testing.T) {
	root := testRoot(t)
	path := prefsPath(root)
	original, _ := os.ReadFile(path)
	t.Cleanup(func() {
		if original == nil {
			_ = os.Remove(path)
			return
		}
		_ = os.WriteFile(path, original, 0o644)
	})
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	desk, err := loadDesk(root, "markets")
	if err != nil {
		t.Fatal(err)
	}
	wires, err := loadView(root, "http://127.0.0.1:1", "wires", "night", true)
	if err != nil {
		t.Fatal(err)
	}
	m := model{
		root: root, server: "http://127.0.0.1:1", theme: theme, board: true, fixture: true,
		views: []bayView{wires}, enabled: map[string]bool{"wires": true},
	}
	m.swapBoard(desk)
	if len(m.views) != 1 || m.views[0].bay.ID != "markets" {
		t.Fatalf("views = %v", m.shownBayIDs())
	}
	if m.enabled["wires"] || !m.enabled["markets"] {
		t.Fatal("board still shows wires")
	}
}

func TestBayRectanglesAndRotation(t *testing.T) {
	cases := []struct{ bays, width, cols, rows int }{
		{1, 80, 1, 1}, {1, 120, 1, 1}, {1, 180, 1, 1}, {1, 260, 1, 1},
		{2, 80, 1, 2}, {2, 120, 2, 1}, {2, 180, 2, 1}, {2, 260, 2, 1},
		{4, 80, 1, 4}, {4, 120, 2, 2}, {4, 180, 3, 2}, {4, 260, 4, 1},
		{6, 80, 1, 6}, {6, 120, 2, 3}, {6, 180, 3, 2}, {6, 240, 4, 2}, {6, 260, 4, 2},
		{9, 80, 1, 9}, {9, 120, 2, 5}, {9, 180, 3, 3}, {9, 260, 4, 3},
	}
	for _, tc := range cases {
		cols, rows := bayGrid(tc.bays, tc.width)
		if cols != tc.cols || rows != tc.rows || cols > columnCount(tc.width) {
			t.Fatalf("%d bays at %d columns = %dx%d, want %dx%d", tc.bays, tc.width, cols, rows, tc.cols, tc.rows)
		}
	}
	items := make([]Item, 40)
	for i := range items {
		items[i] = Item{ID: strconv.Itoa(i), Title: strconv.Itoa(i), Row: "headline"}
	}
	if itemPages(40, 10) != 4 {
		t.Fatal("page count")
	}
	seen := map[string]bool{}
	var labels []string
	page := 0
	for i := 0; i < 4; i++ {
		labels = append(labels, strconv.Itoa(page+1)+"/4")
		for _, item := range pageItems(items, page, 10) {
			seen[item.ID] = true
		}
		page = nextPage(page, 4, false)
	}
	if len(seen) != 40 || strings.Join(labels, " ") != "1/4 2/4 3/4 4/4" {
		t.Fatalf("seen=%d labels=%v", len(seen), labels)
	}
	if nextPage(1, 4, true) != 1 {
		t.Fatal("focused bay advanced")
	}
	view := bayView{bay: Bay{Title: "Wires", Layout: "stack"}, panels: []Panel{{Title: "World", Domain: "wires", Items: items}}}
	m := model{width: 80, height: 30, views: []bayView{view}, navigating: true}
	m.seconds = 15
	m.tickRotation()
	if m.views[0].page != 0 {
		t.Fatal("focused bay rotated")
	}
	m.seconds = 31
	m.tickRotation()
	if m.views[0].page != 1 {
		t.Fatalf("page = %d", m.views[0].page)
	}
}

func TestStormGroupsRegionsAndSkipsAMissingExtreme(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	panel := Panel{Title: "Observation", Domain: "weather", Items: []Item{
		{Row: "observation", Source: "Open-Meteo", Fields: map[string]any{"extreme": "hottest", "place": "Cairo", "temperature_c": 30.0}},
		{Row: "observation", Source: "Open-Meteo", Fields: map[string]any{"place": "London", "region": "Europe", "temperature_c": 12.0}},
		{Row: "observation", Source: "Open-Meteo", Fields: map[string]any{"place": "Tokyo", "region": "Asia", "temperature_c": 18.0}},
	}}
	full := stripANSI(renderBay(Bay{Title: "Storm", Layout: "stack"}, []Panel{panel}, theme, 80))
	if !strings.Contains(full, "hottest  Cairo") || !strings.Contains(full, "Europe") || !strings.Contains(full, "Asia") {
		t.Fatalf("full = %s", full)
	}
	if strings.Contains(full, "windiest") {
		t.Fatal("invented a windiest row")
	}
}

func TestHeadlineSummaryRendersAtFullDetailOnly(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	item := Item{Title: "Tariff notice", Row: "headline", Source: "WTO", Fields: map[string]any{
		"summary": "Hello there", "family": "policy",
	}}
	full := stripANSI(renderHeadline(item, theme, time.Time{}))
	if !strings.Contains(full, "Tariff notice") || !strings.Contains(full, "Hello there") || !strings.Contains(full, "WTO") {
		t.Fatalf("full = %s", full)
	}
	bare := stripANSI(renderHeadline(Item{Title: "Older", Row: "headline", Source: "BBC"}, theme, time.Time{}))
	if strings.Contains(bare, "Hello there") || !strings.Contains(bare, "Older") {
		t.Fatalf("bare = %s", bare)
	}
	view := bayView{bay: Bay{Title: "Trade", Layout: "stack"}, panels: []Panel{{
		Title: "Policy", Domain: "trade", Items: []Item{item},
	}}}
	compact := stripANSI(renderBayCell(view, theme, 40, 10, false, -1, 0, time.Time{}, nil))
	if strings.Contains(compact, "Hello there") {
		t.Fatalf("compact showed the summary: %s", compact)
	}
}

func TestLayoutsSaveLoadEmptyAndRestart(t *testing.T) {
	layouts := saveLayout(nil, 3, []string{"wires", "markets"}, "wire")
	got, ok := layoutAt(layouts, 3)
	if !ok || got.Theme != "wire" || strings.Join(got.Bays, ",") != "wires,markets" {
		t.Fatalf("slot 3 = %+v ok=%v", got, ok)
	}
	if _, ok := layoutAt(layouts, 7); ok {
		t.Fatal("slot 7 should be empty")
	}
	m := model{board: true, layouts: layouts, views: []bayView{{bay: Bay{ID: "storm"}}}, theme: Theme{ID: "night"}}
	updated, _ := m.onKey("7")
	next := updated.(model)
	if next.notice != "slot 7 is empty" || next.views[0].bay.ID != "storm" || next.theme.ID != "night" {
		t.Fatalf("empty load changed the board: %+v", next.notice)
	}
	if cycleSlot(layouts, 3, 1) != 3 || cycleSlot(layouts, 0, 1) != 3 {
		t.Fatal("cycle missed the only occupied slot")
	}
	layouts = saveLayout(layouts, 2, []string{"field"}, "paper")
	dir := t.TempDir()
	saveBoardPrefs(dir, boardPrefs{Theme: "night", Bays: []string{"wires"}, Layouts: layouts, Slot: 2})
	loaded := loadBoardPrefs(dir)
	again, ok := layoutAt(loaded.Layouts, 2)
	if !ok || loaded.Slot != 2 || again.Theme != "paper" || strings.Join(again.Bays, ",") != "field" {
		t.Fatalf("restart = %+v", loaded)
	}
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	line := stripANSI(statusLine(time.Time{}, "Wires", "live", Suggestion{}, theme, 7, "slot 7 is empty", true, ""))
	if !strings.Contains(line, "slot 7") || !strings.Contains(line, "slot 7 is empty") {
		t.Fatalf("status = %s", line)
	}
}

func TestFarDeskEmptyStateNamesTheReason(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	plain := stripANSI(renderBay(Bay{Layout: "stack", Title: "Far Desk"}, []Panel{{
		Title: "Far Desk", Domain: "sports",
		Items: []Item{{Title: "No far-coverage competition is configured", Row: "headline", Source: "Oriel"}},
	}}, theme, 80))
	if !strings.Contains(plain, "No far-coverage competition is configured") {
		t.Fatalf("far empty = %q", plain)
	}
}

func TestRefineFollowsTheFocusedBay(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	if refineHint("field") != "f follows" || refineHint("sideline") != "f sports" || refineHint("brief") != "f brief" || refineHint("far") != "" {
		t.Fatalf("hints = %q %q %q %q", refineHint("field"), refineHint("sideline"), refineHint("brief"), refineHint("far"))
	}
	wiresHint := stripANSI(statusLine(time.Time{}, "Wires", "live", Suggestion{}, theme, 0, "", true, refineHint("wires")))
	briefHint := stripANSI(statusLine(time.Time{}, "Brief", "live", Suggestion{}, theme, 0, "", true, refineHint("brief")))
	if strings.Contains(wiresHint, "f follows") || strings.Contains(wiresHint, "f sports") || strings.Contains(wiresHint, "f brief") {
		t.Fatalf("wires hint advertised f: %s", wiresHint)
	}
	if !strings.Contains(briefHint, "f brief") {
		t.Fatalf("brief hint = %s", briefHint)
	}
	views := []bayView{
		{bay: Bay{ID: "wires", Title: "Wires"}, panels: []Panel{{Title: "World"}}},
		{bay: Bay{ID: "field", Title: "Field"}, panels: []Panel{{
			Title: "Follows",
			Items: []Item{{Title: "Major League Baseball", Row: "follow", Fields: map[string]any{"competition_id": "mlb", "followed": false}}},
		}}},
		{bay: Bay{ID: "sideline", Title: "Sideline"}, panels: []Panel{{
			Title: "Sports",
			Items: []Item{{Title: "Football", Row: "follow", Fields: map[string]any{"sport": "football", "followed": false}}},
		}}},
		{bay: Bay{ID: "brief", Title: "Brief"}, panels: []Panel{{Title: "Observation"}}},
		{bay: Bay{ID: "far", Title: "Far Desk"}, panels: []Panel{{
			Title: "Far Desk",
			Items: []Item{{Title: "No far-coverage competition is configured", Row: "headline"}},
		}}},
	}
	open := func(focus int) model {
		m := model{views: views, theme: theme, board: true, width: 120, height: 40, focus: focus}
		updated, _ := m.onKey("f")
		return updated.(model)
	}
	wires := open(0)
	if wires.follows || wires.sideline || wires.briefPick || !strings.Contains(wires.notice, "nothing to choose") || strings.Contains(stripANSI(wires.View()), "j/k move") {
		t.Fatalf("wires opened a list: %q", wires.notice)
	}
	field := open(1)
	if !field.follows || field.sideline || field.briefPick || !strings.Contains(stripANSI(field.View()), "Major League Baseball") {
		t.Fatal("field did not open follows")
	}
	sideline := open(2)
	plain := stripANSI(sideline.View())
	if sideline.follows || !sideline.sideline || sideline.briefPick || !strings.Contains(plain, "Football") || strings.Contains(plain, "Major League Baseball") {
		t.Fatal("sideline did not open sports")
	}
	brief := open(3)
	if brief.follows || brief.sideline || !brief.briefPick {
		t.Fatal("brief opened another bay's list")
	}
	far := open(4)
	farPlain := stripANSI(far.View())
	if far.follows || far.sideline || far.briefPick || !strings.Contains(far.notice, "nothing to choose") || !strings.Contains(farPlain, "No far-coverage competition is configured") || strings.Contains(farPlain, "j/k move") {
		t.Fatalf("far = %q %q", far.notice, farPlain)
	}
}

func TestWideBayFitsMoreItemsThanANarrowOne(t *testing.T) {
	narrow := itemRoom(80, 40, 6, "full")
	wide := itemRoom(240, 40, 6, "full")
	if wide <= narrow {
		t.Fatalf("wide room %d, narrow room %d", wide, narrow)
	}
	if mixHex("#00ff00", "#ff0000", 0) != "#00ff00" || mixHex("#00ff00", "#ff0000", 1) != "#ff0000" {
		t.Fatal("page timer colors")
	}
}

func TestPauseHoldsThePageAndResumesAtNow(t *testing.T) {
	items := make([]Item, 30)
	for i := range items {
		items[i] = Item{Title: strconv.Itoa(i), Row: "headline"}
	}
	m := model{views: []bayView{{bay: Bay{Title: "Wires"}, panels: []Panel{{Title: "World", Items: items}}}}, width: 80, height: 24}
	paused, _ := m.onKey("p")
	held := paused.(model)
	if !held.paused || held.notice != "paused" {
		t.Fatal("p did not pause")
	}
	held.seconds = 15
	held.tickRotation()
	if held.views[0].page != 0 || held.seconds != 15 {
		t.Fatal("paused bay advanced")
	}
	resumed, _ := held.onKey("p")
	next := resumed.(model)
	if next.paused || next.notice != "" || next.seconds != 0 || next.now.IsZero() {
		t.Fatalf("resume = paused %v notice %q seconds %d", next.paused, next.notice, next.seconds)
	}
}

func TestNarrowBriefStacksAndKeepsTheLiveLead(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	bay, err := loadBay(root, "brief")
	if err != nil {
		t.Fatal(err)
	}
	panels := mustFixturePanels(t, root, bay)
	live := []Panel{{
		Domain: "markets", Title: "Indices",
		Items: []Item{
			{Title: "S&P 500", Row: "quote", Fields: map[string]any{"symbol": "SPX", "price": 5800.0, "change": 12.0, "delayed": true}},
			{Title: "Dow", Row: "quote", Fields: map[string]any{"symbol": "DJI", "price": 1.0}},
		},
	}}
	kept := applyBriefLead(panels, "markets", nil, fmt.Errorf("down"))
	if kept[2].Items[0].Fields["symbol"] != "FIX" {
		t.Fatal("brief dropped the quote while markets was down")
	}
	swapped := applyBriefLead(panels, "markets", live, nil)
	if swapped[2].Title != "Indices" || len(swapped[2].Items) != 1 || swapped[2].Items[0].Fields["symbol"] != "SPX" {
		t.Fatalf("brief quote = %+v", swapped[2])
	}
	narrow := stripANSI(renderBay(bay, swapped, theme, 60))
	for _, line := range strings.Split(narrow, "\n") {
		if strings.Contains(line, "Weather") && strings.Contains(line, "Indices") {
			t.Fatalf("narrow brief kept three columns:\n%s", narrow)
		}
	}
	if strings.Contains(narrow, "FIX") {
		t.Fatal("narrow brief still shows the fixture quote")
	}
	wide := stripANSI(renderBay(bay, swapped, theme, 160))
	together := false
	for _, line := range strings.Split(wide, "\n") {
		if strings.Contains(line, "Weather") && strings.Contains(line, "Indices") {
			together = true
		}
	}
	if !together {
		t.Fatalf("wide brief did not keep the strip:\n%s", wide)
	}
}

func TestBayBottomKeepsItsBorder(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	now := time.Date(2026, 9, 25, 23, 15, 0, 0, time.UTC)
	quotes := make([]Item, 24)
	for i := range quotes {
		quotes[i] = Item{
			Row: "quote", Source: "Yahoo Finance", ObservedAt: "2026-09-25T20:00:00Z",
			Fields: map[string]any{
				"symbol": fmt.Sprintf("S%02d", i), "price": 771.35, "change": 4.17, "delayed": true,
			},
		}
	}
	markets := bayView{bay: Bay{ID: "markets", Title: "Markets"}, panels: []Panel{
		{Title: "Funds", Domain: "markets", Items: quotes[:12]},
		{Title: "FX", Domain: "markets", Items: quotes[12:]},
	}}
	headline := "Coastal Flood Warning issued September 25 at 4:44PM EDT until September 27 at 6:00PM EDT by NWS Upton NY"
	storm := bayView{bay: Bay{ID: "storm", Title: "Storm"}, panels: []Panel{
		{Title: "Observation", Domain: "weather", Items: []Item{{
			Row: "observation", Source: "Open-Meteo", ObservedAt: "2026-09-25T23:15:00Z",
			Fields: map[string]any{
				"place": "Toronto", "region": "North America", "condition": "mainly clear",
				"temperature_c": 15.9, "apparent_temperature_c": 14.4, "humidity_pct": 63.0, "wind_speed_kmh": 7.6,
			},
		}}},
		{Title: "Alerts", Domain: "weather", Items: []Item{{
			Row: "alert", Title: headline, Source: "National Weather Service", ObservedAt: "2026-09-25T20:44:00Z",
			Fields: map[string]any{"severity": "Severe", "headline": headline},
		}}},
	}}
	const cellW, cellH = 100, 22
	top := stripANSI(renderBayCell(markets, theme, cellW, cellH, false, -1, 0, now, nil))
	bottom := stripANSI(renderBayCell(storm, theme, cellW, cellH, false, -1, 0, now, nil))
	if n := len(strings.Split(top, "\n")); n > cellH {
		t.Fatalf("markets cell drew %d lines", n)
	}
	if n := len(strings.Split(bottom, "\n")); n > cellH {
		t.Fatalf("storm cell drew %d lines", n)
	}
	if !strings.Contains(lastInk(top), "└") {
		t.Fatalf("markets bottom was clipped:\n%s", top)
	}
	if !strings.Contains(lastInk(bottom), "└") {
		t.Fatalf("storm bottom was clipped:\n%s", bottom)
	}
	for _, line := range strings.Split(top, "\n") {
		switch strings.TrimSpace(line) {
		case "Finance", "Yahoo", "3h", "Frankfurter":
			t.Fatalf("quote wrapped onto %q\n%s", strings.TrimSpace(line), top)
		}
	}
	for _, line := range strings.Split(bottom, "\n") {
		if strings.TrimSpace(line) == "km/h" {
			t.Fatalf("observation wrapped:\n%s", bottom)
		}
	}
	board := stripANSI(renderBoard([]bayView{markets, storm}, theme, 200, 48, 0, 0, now, nil))
	if n := len(strings.Split(board, "\n")); n > 47 {
		t.Fatalf("board drew %d lines into the status row", n)
	}
}

func lastInk(text string) string {
	lines := strings.Split(text, "\n")
	for i := len(lines) - 1; i >= 0; i-- {
		if strings.TrimSpace(lines[i]) != "" {
			return lines[i]
		}
	}
	return ""
}

func TestHeadlineGapAndClipStayOnScreen(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	items := []Item{
		{Title: "First headline that is deliberately much longer than a narrow column can show on one row", Row: "headline", Fields: map[string]any{"summary": "A long summary that would wrap for many lines and push the status line off the window if it were printed whole."}},
		{Title: "Second", Row: "headline"},
	}
	plain := stripANSI(panelBody(Panel{Title: "World", Domain: "wires", Items: items}, theme, time.Time{}, 30, 0, "full", 40, 0, nil))
	if !strings.Contains(plain, "First headline") || !strings.Contains(plain, "\n\n") || !strings.Contains(plain, "…") {
		t.Fatalf("headline spacing = %q", plain)
	}
	view := bayView{bay: Bay{Title: "Wires", Layout: "stack"}, panels: []Panel{{Title: "World", Domain: "wires", Items: items}}}
	board := renderBoard([]bayView{view}, theme, 80, 20, 0, 0, time.Time{}, nil)
	if len(strings.Split(board, "\n")) > 18 {
		t.Fatalf("board spilled past the status row: %d lines", len(strings.Split(board, "\n")))
	}
}

func TestShortPanelStaysFilledOnALongPage(t *testing.T) {
	short := Panel{Title: "FX", Domain: "markets", Items: []Item{{Title: "Euro"}, {Title: "Yen"}}}
	long := Panel{Title: "Crypto", Domain: "markets"}
	for i := 0; i < 48; i++ {
		long.Items = append(long.Items, Item{Title: "c" + strconv.Itoa(i)})
	}
	shown, label, pages := visiblePanels([]Panel{short, long}, "full", 41, 1)
	if pages != 48 || label != "42/48" || len(shown[0].Items) != 1 || shown[0].Items[0].Title != "Yen" {
		t.Fatalf("short panel blanked on a long page: %d %s %+v", pages, label, shown[0].Items)
	}
}

func TestBoardClipsExtraBaysAndHomeRestoresTheSet(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	views := make([]bayView, 6)
	ids := []string{"brief", "wires", "markets", "far", "field", "trade"}
	for i, id := range ids {
		items := make([]Item, 30)
		for n := range items {
			items[n] = Item{Title: id + " item", Row: "headline", Source: "Fixture"}
		}
		views[i] = bayView{bay: Bay{ID: id, Title: id, Layout: "stack"}, panels: []Panel{{Title: id, Domain: id, Items: items}}}
	}
	plain := stripANSI(renderBoard(views, theme, 240, 40, 0, 0, time.Time{}, nil))
	lines := strings.Split(plain, "\n")
	if len(lines) > 39 {
		t.Fatalf("six bays drew %d lines", len(lines))
	}
	if !strings.Contains(plain, "brief") || !strings.Contains(plain, "trade") {
		t.Fatalf("grid dropped a bay: %s", plain)
	}
	prefs := filepath.Join(root, "client", "state", "board.json")
	original, readErr := os.ReadFile(prefs)
	t.Cleanup(func() {
		if readErr != nil {
			_ = os.Remove(prefs)
			return
		}
		_ = os.WriteFile(prefs, original, 0o644)
	})
	m := model{
		board: true, fixture: true, root: root, theme: theme, width: 120, height: 30,
		views:  []bayView{{bay: Bay{ID: "field", Title: "Field"}}},
		server: "http://127.0.0.1:1",
	}
	updated, _ := m.onKey("h")
	home := updated.(model)
	if strings.Join(home.shownBayIDs(), ",") != "wires,markets,storm,trade" || home.notice != "home" {
		t.Fatalf("home = %v %q", home.shownBayIDs(), home.notice)
	}
}

func TestFieldFollowPickerTogglesACompetition(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	var posted struct {
		CompetitionID string `json:"competition_id"`
		Follow        bool   `json:"follow"`
	}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/bays/field/follows" || r.Method != http.MethodPost {
			http.NotFound(w, r)
			return
		}
		if err := json.NewDecoder(r.Body).Decode(&posted); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		fmt.Fprintf(w, `{"id":"field","panels":[{"id":"field-scores","domain":"sports","title":"Field","updated_at":"2026-09-24T16:00:00Z","stale":false,"stale_reason":"","items":[{"id":"mlb","title":"Fixture Away Fixture Home","source":"MLB Stats API","source_url":"","observed_at":"2026-09-24T16:00:00Z","row":"score","fields":{"home":"Fixture Home","away":"Fixture Away","score":"0-1","state":"in progress","tier":"live"}}]},{"id":"field-follows","domain":"sports","title":"Follows","updated_at":"2026-09-24T16:00:00Z","stale":false,"stale_reason":"","items":[{"id":"follow-mlb","title":"Major League Baseball","source":"Oriel","source_url":"","observed_at":"2026-09-24T16:00:00Z","row":"follow","fields":{"competition_id":"mlb","tier":"live","followed":%t}}]}]}`, posted.Follow)
	}))
	defer server.Close()
	view := bayView{bay: Bay{ID: "field", Title: "Field"}, panels: []Panel{
		{ID: "field-scores", Title: "Field", Domain: "sports", Items: []Item{{Title: "Choose follows", Row: "headline", Source: "Oriel"}}},
		{ID: "field-follows", Title: "Follows", Domain: "sports", Items: []Item{{
			Title: "Major League Baseball", Row: "follow", Source: "Oriel",
			Fields: map[string]any{"competition_id": "mlb", "tier": "live", "followed": false},
		}}},
	}}
	m := model{views: []bayView{view}, theme: theme, server: server.URL, width: 80, height: 24}
	opened, _ := m.onKey("f")
	picker := opened.(model)
	if !picker.follows || !strings.Contains(stripANSI(picker.View()), "Major League Baseball") || strings.Contains(stripANSI(picker.View()), "0-1") {
		t.Fatal("picker did not list the competition without a score")
	}
	cmdModel, cmd := picker.onKey("1")
	if cmd == nil {
		t.Fatal("digit did not post a follow")
	}
	updated, _ := cmdModel.Update(cmd())
	after := updated.(model)
	first, firstReady, firstValid := followPick("1", 15, false)
	confirmed, confirmedReady, confirmedValid := followPick("1", 15, true)
	twelfth, twelfthReady, twelfthValid := followPick("12", 15, false)
	if first != 0 || firstReady || !firstValid || !confirmedReady || !confirmedValid || confirmed != 0 {
		t.Fatal("enter did not confirm competition 1")
	}
	if twelfth != 11 || !twelfthReady || !twelfthValid {
		t.Fatal("multi-digit follow pick")
	}
	if _, _, valid := followPick("16", 15, true); valid {
		t.Fatal("out of range follow pick")
	}
	if posted.CompetitionID != "mlb" || !posted.Follow || after.notice != "followed Major League Baseball" {
		t.Fatalf("follow = %+v %q", posted, after.notice)
	}
	plain := stripANSI(renderBay(after.views[0].bay, after.views[0].panels, theme, 80))
	if !strings.Contains(plain, "0-1") || !strings.Contains(plain, "following") {
		t.Fatalf("field after follow = %q", plain)
	}
	empty := stripANSI(renderBay(Bay{Layout: "stack"}, []Panel{{
		Title: "Field", Domain: "sports",
		Items: []Item{{Title: "Choose follows", Row: "headline", Source: "Oriel"}},
	}}, theme, 80))
	if strings.Contains(empty, "0-1") || strings.Contains(empty, "Fixture") {
		t.Fatalf("empty follows invented a score: %q", empty)
	}
}

func TestEnterConfirmsTheFirstCompetitionWhenTensExist(t *testing.T) {
	items := make([]Item, 12)
	for i := range items {
		items[i] = Item{
			Title: "League " + strconv.Itoa(i+1), Row: "follow", Source: "Oriel",
			Fields: map[string]any{"competition_id": "id-" + strconv.Itoa(i+1), "followed": i == 0},
		}
	}
	m := model{views: []bayView{{bay: Bay{ID: "field"}, panels: []Panel{{Title: "Follows", Items: items}}}}, follows: true}
	held, cmd := m.onKey("1")
	if cmd != nil {
		t.Fatal("1 posted while 10 and above were still possible")
	}
	waiting := held.(model)
	if waiting.followDigits != "1" || waiting.followCursor != 0 {
		t.Fatalf("pending = %q cursor %d", waiting.followDigits, waiting.followCursor)
	}
	chosen, cmd := waiting.onKey("enter")
	if cmd == nil {
		t.Fatal("enter did not toggle Major League Baseball's slot")
	}
	_ = chosen
}

func TestSportGlyphUsesTheFamily(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	plain := stripANSI(renderFollow(Item{
		Title: "Major League Baseball", Row: "follow",
		Fields: map[string]any{"family": "baseball", "followed": true, "tier": "live"},
	}, theme))
	if !strings.Contains(plain, "⚾") || !strings.Contains(plain, "Major League Baseball") || strings.Contains(plain, "MLB") {
		t.Fatalf("follow = %s", plain)
	}
}

func TestDensityFillsTheCellAndKeepsAQuoteOnOneLine(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	now := time.Date(2026, 9, 24, 18, 0, 0, 0, time.UTC)
	quotes := make([]Item, 24)
	for i := range quotes {
		quotes[i] = Item{
			Row: "quote", Source: "Frankfurter", ObservedAt: "2026-09-24T17:00:00Z",
			Fields: map[string]any{"symbol": "Q" + strconv.Itoa(i), "price": float64(i + 1), "change": 1.0, "delayed": true},
		}
	}
	quotes[3].Fields = map[string]any{"symbol": "NONE"}
	panel := Panel{Title: "Crypto", Domain: "markets", Items: quotes}
	tall := stripANSI(renderBayCell(bayView{bay: Bay{Title: "Markets", Layout: "stack"}, panels: []Panel{panel}}, theme, 80, 30, false, -1, 0, now, nil))
	short := stripANSI(renderBayCell(bayView{bay: Bay{Title: "Markets", Layout: "stack"}, panels: []Panel{panel}}, theme, 80, 12, false, -1, 0, now, nil))
	if strings.Count(tall, "Q") <= strings.Count(short, "Q") {
		t.Fatalf("tall cell did not show more quotes\n%s\n%s", tall, short)
	}
	if strings.Contains(tall, "\n\n\n") {
		t.Fatalf("blank remainder in a tall quote cell\n%s", tall)
	}
	if !strings.Contains(tall, "NONE") || strings.Contains(tall, "NONE  0") {
		t.Fatalf("missing price = %s", tall)
	}
	narrow := stripANSI(renderQuote(quotes[0], theme, now, 18, nil))
	if strings.Contains(narrow, "\n") || !strings.Contains(narrow, "Q0") || !strings.Contains(narrow, "1") {
		t.Fatalf("narrow quote = %q", narrow)
	}
	if strings.Contains(narrow, "Frankfurter") || strings.Contains(narrow, "1h") {
		t.Fatalf("narrow quote kept the tail: %q", narrow)
	}
	wide := stripANSI(renderQuote(quotes[0], theme, now, 80, nil))
	if strings.Contains(wide, "\n") || !strings.Contains(wide, "Frankfurter") || !strings.Contains(wide, "delayed") {
		t.Fatalf("wide quote = %q", wide)
	}
	indices := make([]Item, 4)
	for i := range indices {
		indices[i] = Item{Row: "quote", Fields: map[string]any{"symbol": "IDX" + strconv.Itoa(i), "price": 10.0}}
	}
	crypto := make([]Item, 20)
	for i := range crypto {
		crypto[i] = Item{Row: "quote", Fields: map[string]any{"symbol": "C" + strconv.Itoa(i), "price": 2.0}}
	}
	both := stripANSI(renderBayCell(bayView{bay: Bay{Title: "Markets", Layout: "stack"}, panels: []Panel{
		{Title: "Indices", Domain: "markets", Items: indices},
		{Title: "Crypto", Domain: "markets", Items: crypto},
	}}, theme, 80, 36, false, -1, 0, now, nil))
	for i := 0; i < 4; i++ {
		if !strings.Contains(both, "IDX"+strconv.Itoa(i)) {
			t.Fatalf("index missing: %s", both)
		}
	}
	if !strings.Contains(both, "C0") || !strings.Contains(both, "C1") {
		t.Fatalf("crypto did not fill beside the short family\n%s", both)
	}
	places := make([]Item, 12)
	for i := range places {
		places[i] = Item{Row: "observation", Source: "Open-Meteo", Fields: map[string]any{
			"place": "P" + strconv.Itoa(i), "region": "Europe", "temperature_c": float64(10 + i),
		}}
	}
	places[2].Fields = map[string]any{"place": "Blank", "region": "Europe"}
	storm := stripANSI(renderBayCell(bayView{bay: Bay{Title: "Storm", Layout: "stack"}, panels: []Panel{
		{Title: "Observation", Domain: "weather", Items: places},
	}}, theme, 100, 40, false, -1, 0, now, nil))
	if !strings.Contains(storm, "P0") || !strings.Contains(storm, "P4") || !strings.Contains(storm, "Blank") {
		t.Fatalf("storm cell = %s", storm)
	}
	blankAt := strings.Index(storm, "Blank")
	if blankAt < 0 || strings.Contains(storm[blankAt:blankAt+12], "°C") {
		t.Fatalf("blank temperature = %s", storm)
	}
	headlines := []Item{
		{Title: "First", Row: "headline", Source: "BBC", Fields: map[string]any{"summary": "One line only"}},
		{Title: "Second", Row: "headline", Source: "BBC", Fields: map[string]any{"summary": "Still one line"}},
	}
	wires := stripANSI(panelBody(Panel{Title: "World", Domain: "wires", Items: headlines}, theme, time.Time{}, 30, 0, "full", 40, 0, nil))
	if strings.Count(wires, "\n\n") != 1 || strings.Count(wires, "One line only") != 1 {
		t.Fatalf("headline gap = %q", wires)
	}
	if strings.Contains(wires, "One line only\n") && strings.Contains(strings.Split(wires, "One line only\n")[1], "line only") {
		t.Fatalf("summary wrapped: %q", wires)
	}
}

func TestPagingBayKeepsThePageIndicator(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	now := time.Date(2026, 9, 25, 15, 0, 0, 0, time.UTC)
	markets := make([]Panel, 8)
	names := []string{"Indices", "Sectors", "Equities", "FX", "Rates", "Bonds", "Commodities", "Crypto"}
	for i, name := range names {
		items := make([]Item, 12)
		for n := range items {
			items[n] = Item{Row: "quote", Fields: map[string]any{"symbol": name[:1] + strconv.Itoa(n), "price": 1.0, "change": 1.0}}
		}
		markets[i] = Panel{Title: name, Domain: "markets", Items: items}
	}
	headlines := make([]Item, 40)
	for i := range headlines {
		headlines[i] = Item{Title: "Headline " + strconv.Itoa(i), Row: "headline", Source: "BBC"}
	}
	views := []bayView{
		{bay: Bay{ID: "markets", Title: "Markets"}, panels: markets},
		{bay: Bay{ID: "trade", Title: "Trade", Layout: "stack"}, panels: []Panel{{Title: "Policy", Domain: "trade", Items: headlines}}},
		{bay: Bay{ID: "wires", Title: "Wires", Layout: "stack"}, panels: []Panel{{Title: "World", Domain: "wires", Items: headlines}}},
	}
	raw := renderBoard(views, theme, 180, 36, 0, 4, now, nil)
	board := stripANSI(raw)
	lines := strings.Split(board, "\n")
	if len(lines) == 0 || !strings.Contains(lines[0], "Markets") || !strings.Contains(lines[0], "/") || !strings.Contains(lines[0], "●") {
		t.Fatalf("markets indicator missing\n%s", strings.Join(lines[:min(3, len(lines))], "\n"))
	}
	if !strings.Contains(lines[0], "Trade") || !strings.Contains(lines[0], "Wires") {
		t.Fatalf("other bay indicators missing\n%s", lines[0])
	}
	if !strings.Contains(raw, roleSequence(theme, "accent")+"Markets") {
		t.Fatal("focused bay title lost the accent")
	}
	if strings.Contains(raw, roleSequence(theme, "accent")+"1/") || !strings.Contains(raw, roleSequence(theme, "text")+"1/") {
		t.Fatal("page label took the focus color")
	}
}

func TestMarketsCellSpendsLeftoverLines(t *testing.T) {
	indices := []Item{
		{Title: "S&P", Row: "quote", Fields: map[string]any{"symbol": "SPX", "price": 10.0}},
		{Title: "Dow", Row: "quote", Fields: map[string]any{"symbol": "DJI", "price": 11.0}},
	}
	crypto := make([]Item, 40)
	for i := range crypto {
		crypto[i] = Item{Row: "quote", Fields: map[string]any{"symbol": "C" + strconv.Itoa(i), "price": 2.0}}
	}
	panels := []Panel{
		{Title: "Indices", Domain: "markets", Items: indices},
		{Title: "Crypto", Domain: "markets", Items: crypto},
	}
	shown, label, pages, _, _ := marketPage(panels, 80, 30, 0)
	plain := ""
	for _, panel := range shown {
		for _, item := range panel.Items {
			plain += item.Fields["symbol"].(string) + "\n"
		}
	}
	if !strings.Contains(plain, "SPX") || !strings.Contains(plain, "DJI") || !strings.Contains(plain, "C20") {
		t.Fatalf("leftover lines did not reach the longer family\n%s", plain)
	}
	if strings.Contains(plain, "C30") {
		t.Fatalf("page drew rows past the cell\n%s", plain)
	}
	if pages < 2 || label != "1/"+strconv.Itoa(pages) {
		t.Fatalf("overflow page = %d %s", pages, label)
	}
	root := testRoot(t)
	theme := mustTheme(t, root)
	fitted := stripANSI(renderQuote(Item{
		Row: "quote", Source: "Yahoo Finance",
		Fields: map[string]any{"symbol": "SPX", "price": 5000.0, "change": 2.0, "delayed": true},
	}, theme, time.Now(), 80, nil))
	if strings.Contains(fitted, "\n") || !strings.Contains(fitted, "▬") || strings.Contains(fitted, "█") {
		t.Fatalf("bar = %q", fitted)
	}
}

func TestShortMarketsCellCyclesFamilies(t *testing.T) {
	panels := make([]Panel, 6)
	for i := range panels {
		panels[i] = Panel{
			Title: "Family " + strconv.Itoa(i), Domain: "markets",
			Items: []Item{{Row: "quote", Fields: map[string]any{"symbol": "F" + strconv.Itoa(i), "price": 1.0}}},
		}
	}
	first, _, pages, _, origin := marketPage(panels, 80, 16, 0)
	if pages < 2 || origin != 0 || len(first) >= len(panels) {
		t.Fatalf("short cell showed every family: pages %d origin %d shown %d", pages, origin, len(first))
	}
	last, _, _, _, lastOrigin := marketPage(panels, 80, 16, pages-1)
	if lastOrigin == 0 {
		t.Fatal("later page repeated the first families")
	}
	seen := map[string]bool{}
	for _, panel := range append(first, last...) {
		seen[panel.Title] = true
	}
	if seen["Family 0"] && seen["Family 5"] && len(first) == len(panels) {
		t.Fatal("both ends landed on one page")
	}
	if !seen["Family 0"] || !seen["Family 5"] {
		t.Fatalf("cycle missed an end: %v", seen)
	}
	root := testRoot(t)
	theme := mustTheme(t, root)
	wide := stripANSI(renderBayCell(bayView{bay: Bay{ID: "markets", Title: "Markets"}, panels: []Panel{
		{Title: "Indices", Domain: "markets", Items: []Item{
			{Row: "quote", Fields: map[string]any{"symbol": "SPX", "price": 5000.0, "change": 3.0, "delayed": true}},
			{Row: "quote", Fields: map[string]any{"symbol": "VIX", "price": 14.0, "change": -1.0, "delayed": true}},
		}},
		{Title: "FX", Domain: "markets", Items: []Item{
			{Row: "quote", Fields: map[string]any{"symbol": "EURUSD", "price": 1.14, "change": 0.2, "delayed": true}},
		}},
	}}, theme, 200, 24, true, 0, 0, time.Now(), nil))
	widest := 0
	for _, line := range strings.Split(wide, "\n") {
		if n := len([]rune(line)); n > widest {
			widest = n
		}
	}
	if widest < 180 || !strings.Contains(wide, "▬") || strings.Contains(wide, "█") {
		t.Fatalf("wide markets cell span %d\n%s", widest, wide)
	}
	barLine := ""
	for _, line := range strings.Split(wide, "\n") {
		if strings.Contains(line, "▬") {
			barLine = line
			break
		}
	}
	if strings.Contains(barLine, "│▬") || strings.Contains(barLine, "▬│") {
		t.Fatalf("bar meets the rule: %s", barLine)
	}
	counts := []int{17, 27, 21, 18, 11, 7, 16, 48}
	board := make([]Panel, len(counts))
	names := []string{"Indices", "Sectors", "Equities", "FX", "Rates", "Bonds", "Commodities", "Crypto"}
	for i, count := range counts {
		items := make([]Item, count)
		for n := range items {
			items[n] = Item{Row: "quote", Fields: map[string]any{"symbol": names[i][:1] + strconv.Itoa(n), "price": 1.0}}
		}
		board[i] = Panel{Title: names[i], Domain: "markets", Items: items}
	}
	shown, _, _, _, origin := marketPage(board, 240, 100, 0)
	if origin != 0 || len(shown) != len(board) {
		t.Fatalf("wide board hid a family: origin %d shown %d", origin, len(shown))
	}
	cryptoRows := 0
	for _, panel := range shown {
		if panel.Title == "Crypto" {
			cryptoRows = len(panel.Items)
		}
	}
	if cryptoRows < 40 {
		t.Fatalf("wide cell left crypto on a later page: %d rows", cryptoRows)
	}
}

func TestFieldScoreColorsAndFollowSeason(t *testing.T) {
	root := testRoot(t)
	theme, err := loadTheme(root, "night")
	if err != nil {
		t.Fatal(err)
	}
	if phaseRole("in progress 12:04") != "up" || phaseRole("final") != "muted" || phaseRole("scheduled 2026-09-25 00:00 UTC") != "warn" {
		t.Fatal("phase roles")
	}
	live := renderScore(Item{
		Source: "TheSportsDB", Row: "score",
		Fields: map[string]any{"home": "Atlanta Falcons", "away": "Green Bay Packers", "score": "3-7", "state": "in progress 12:04", "league": "NFL", "tier": "delayed"},
	}, theme, time.Time{})
	done := renderScore(Item{
		Source: "OpenLigaDB", Row: "score",
		Fields: map[string]any{"home": "Arsenal", "away": "Chelsea", "score": "1-0", "state": "final", "league": "Premier League", "tier": "delayed"},
	}, theme, time.Time{})
	soon := renderScore(Item{
		Source: "OpenLigaDB", Row: "score",
		Fields: map[string]any{"home": "Arsenal", "away": "Chelsea", "state": "scheduled 2026-09-26 14:00 UTC", "league": "Premier League", "tier": "delayed"},
	}, theme, time.Time{})
	if !strings.Contains(live, "38;2;60;214;140min progress") || !strings.Contains(done, "38;2;139;155;176mfinal") || !strings.Contains(soon, "38;2;240;179;40mscheduled") {
		t.Fatal("score states did not use the phase colors")
	}
	plain := stripANSI(live + "\n" + soon)
	if !strings.Contains(plain, "NFL") || !strings.Contains(plain, "Premier League") || !strings.Contains(plain, "in progress 12:04") {
		t.Fatalf("score line = %q", plain)
	}
	follow := stripANSI(renderFollow(Item{
		Title: "Premier League", Source: "Oriel", Row: "follow",
		Fields: map[string]any{"country": "England", "season_start": "2026-08-21", "season_end": "2027-05-30", "flag": "active", "tier": "delayed", "followed": true},
	}, theme))
	if !strings.Contains(follow, "2026-08-21") || !strings.Contains(follow, "2027-05-30") || !strings.Contains(follow, "active") || !strings.Contains(follow, "England") {
		t.Fatalf("follow line = %q", follow)
	}
}

func TestWideMarketsCellSpreadsWhenEveryRowFits(t *testing.T) {
	panels := make([]Panel, 8)
	for i := range panels {
		panels[i] = Panel{
			Title: "Family " + strconv.Itoa(i), Domain: "markets",
			Items: []Item{
				{Row: "quote", Fields: map[string]any{"symbol": "A" + strconv.Itoa(i), "price": 1.0}},
				{Row: "quote", Fields: map[string]any{"symbol": "B" + strconv.Itoa(i), "price": 1.0}},
			},
		}
	}
	_, _, pages, columns, _ := marketPage(panels, 240, 40, 0)
	if pages != 1 || len(columns) < 3 {
		t.Fatalf("wide fit stayed narrow: pages %d columns %d", pages, len(columns))
	}
	_, _, shortPages, shortColumns, _ := marketPage(panels, 80, 16, 0)
	if shortPages < 2 || len(shortColumns) > 1 {
		t.Fatalf("short cell spread: pages %d columns %d", shortPages, len(shortColumns))
	}
}

func TestChangedQuoteFlashesThenRests(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	now := time.Date(2026, 9, 25, 16, 0, 0, 0, time.UTC)
	item := Item{ID: "equities:NVDA", Row: "quote", Fields: map[string]any{"symbol": "NVDA", "price": 100.0, "change": 1.5}}
	seen := map[string]string{}
	flashes := map[string]time.Time{}
	noteQuotePrices(seen, flashes, []Panel{{Items: []Item{item}}}, now)
	if len(flashes) != 0 {
		t.Fatal("first print flashed")
	}
	item.Fields["price"] = 101.25
	noteQuotePrices(seen, flashes, []Panel{{Items: []Item{item}}}, now)
	if flashes["equities:NVDA"].IsZero() {
		t.Fatal("changed price did not flash")
	}
	fresh := renderQuote(item, theme, now, 80, flashes)
	if !strings.Contains(fresh, roleSequence(theme, "accent")+"NVDA") || !strings.Contains(fresh, roleSequence(theme, "accent")+"101.25") {
		t.Fatalf("flash = %q", fresh)
	}
	if !strings.Contains(fresh, roleSequence(theme, "up")) {
		t.Fatal("flash hid the change color")
	}
	rested := renderQuote(item, theme, now.Add(3*time.Second), 80, flashes)
	if strings.Contains(rested, roleSequence(theme, "accent")+"NVDA") {
		t.Fatal("flash stayed on")
	}
	noteQuotePrices(seen, flashes, []Panel{{Items: []Item{item}}}, now.Add(3*time.Second))
	if _, on := flashes["equities:NVDA"]; on && flashes["equities:NVDA"].After(now.Add(3*time.Second)) {
		t.Fatal("unchanged price flashed again")
	}
}

func TestBriefSelectionChoosesAPlaceAndKeepsABlankPrice(t *testing.T) {
	root := testRoot(t)
	theme := mustTheme(t, root)
	bay, err := loadBay(root, "brief")
	if err != nil {
		t.Fatal(err)
	}
	panels := mustFixturePanels(t, root, bay)
	observation := Panel{
		ID: "weather-observation", Domain: "weather", Title: "Observation",
		Items: []Item{
			{ID: "observation:tampa", Title: "Tampa", Row: "observation", Fields: map[string]any{"place": "Tampa", "temperature_c": 23.6, "configured": true, "home": true}},
			{ID: "observation:london", Title: "London", Row: "observation", Fields: map[string]any{"place": "London", "temperature_c": 14.0, "configured": true, "home": false}},
			{ID: "observation:paris", Title: "Paris", Row: "observation", Fields: map[string]any{"place": "Paris", "configured": true, "home": false}},
		},
	}
	london := applyBriefPlace(panels, observation, nil, "london")
	if london[0].Items[0].Fields["place"] != "London" {
		t.Fatalf("place = %+v", london[0].Items[0].Fields)
	}
	kept := applyBriefPlace(london, observation, nil, "paris")
	if kept[0].Items[0].Fields["place"] != "London" {
		t.Fatal("a place with no observation replaced the last good row")
	}
	markets := []Panel{{
		ID: "markets-funds", Domain: "markets", Title: "Funds",
		Items: []Item{{ID: "funds:NOPRICE", Title: "Fund", Row: "quote", Fields: map[string]any{"symbol": "NOPRICE"}}},
	}}
	quoted := applyBriefFamily(panels, markets, nil, "funds")
	if quoted[2].Title != "Funds" || quoted[2].Items[0].Fields["symbol"] != "NOPRICE" {
		t.Fatalf("family = %+v", quoted[2])
	}
	line := stripANSI(renderQuote(quoted[2].Items[0], theme, time.Time{}, 40, nil))
	if !strings.Contains(line, "NOPRICE") || strings.Contains(line, "0") {
		t.Fatalf("blank price = %q", line)
	}

	var posted struct {
		Slot string `json:"slot"`
		ID   string `json:"id"`
	}
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		switch r.URL.Path {
		case "/bays/brief/selection":
			if r.Method == http.MethodPost {
				if err := json.NewDecoder(r.Body).Decode(&posted); err != nil {
					http.Error(w, err.Error(), http.StatusBadRequest)
					return
				}
			}
			fmt.Fprintf(w, `{"place":%q,"outlet":"","family":"","items":[{"id":"brief-place-default","title":"Home","source":"Oriel","source_url":"","observed_at":"2026-09-25T00:00:00Z","row":"follow","fields":{"slot":"place","choice_id":"","followed":false}},{"id":"brief-place-london","title":"London","source":"Oriel","source_url":"","observed_at":"2026-09-25T00:00:00Z","row":"follow","fields":{"slot":"place","choice_id":"london","followed":true}}]}`, posted.ID)
		case "/panels/weather-observation":
			_, _ = w.Write([]byte(`{"id":"weather-observation","domain":"weather","title":"Observation","updated_at":"2026-09-25T00:00:00Z","stale":false,"stale_reason":"","items":[{"id":"observation:london","title":"London","source":"Open-Meteo","source_url":"","observed_at":"2026-09-25T00:00:00Z","row":"observation","fields":{"place":"London","temperature_c":14,"configured":true,"home":false}}]}`))
		case "/bays/wires":
			http.Error(w, "down", http.StatusBadGateway)
		case "/bays/markets":
			_, _ = w.Write([]byte(`{"id":"markets","panels":[{"id":"markets-funds","domain":"markets","title":"Funds","updated_at":"2026-09-25T00:00:00Z","stale":false,"stale_reason":"","items":[{"id":"funds:NOPRICE","title":"Fund","source":"Yahoo Finance","source_url":"","observed_at":"2026-09-25T00:00:00Z","row":"quote","fields":{"symbol":"NOPRICE"}}]}]}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()
	m := model{
		views: []bayView{{
			bay: Bay{ID: "brief", Title: "Brief"}, panels: panels,
			briefChoices: []followChoice{{ID: "london", Name: "London", Slot: "place"}},
		}},
		theme: theme, server: server.URL, width: 80, height: 24, focus: 0,
	}
	opened, _ := m.onKey("f")
	picker := opened.(model)
	if !picker.briefPick || !strings.Contains(stripANSI(picker.View()), "London") {
		t.Fatal("brief list did not open")
	}
	chosen, cmd := picker.onKey("enter")
	if cmd == nil {
		t.Fatal("enter did not select the row")
	}
	updated, _ := chosen.Update(cmd())
	after := updated.(model)
	if posted.Slot != "place" || posted.ID != "london" || after.notice != "selected London" {
		t.Fatalf("select = %+v %q", posted, after.notice)
	}
	if after.views[0].panels[0].Items[0].Fields["place"] != "London" {
		t.Fatalf("brief place = %+v", after.views[0].panels[0].Items[0].Fields)
	}
	if after.views[0].panels[2].Items[0].Fields["symbol"] != "NOPRICE" {
		t.Fatalf("brief quote = %+v", after.views[0].panels[2].Items[0].Fields)
	}
}
