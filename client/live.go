package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

const liveServerTimeout = 3 * time.Second

func shouldLive(bayID string, fixtureOnly bool) bool {
	if fixtureOnly {
		return false
	}
	switch bayID {
	case "wires", "markets", "trade", "storm", "field", "far", "fantasy":
		return true
	default:
		return false
	}
}

func chooseWiresPanels(fixtures []Panel, fetched []Panel, fetchErr error) (panels []Panel, live bool) {
	if fetchErr != nil {
		return fixtures, false
	}
	return fetched, true
}

type Suggestion struct {
	DeskID  string   `json:"desk_id"`
	Reason  string   `json:"reason"`
	Panels  []string `json:"panels"`
	Applied bool     `json:"applied"`
}

func suggestionLine(suggestion Suggestion) string {
	return "suggestion  " + suggestion.DeskID + "  " + suggestion.Reason
}

func fetchSuggestion(baseURL string) (Suggestion, error) {
	endpoint := strings.TrimRight(baseURL, "/") + "/suggestions"
	client := &http.Client{Timeout: liveServerTimeout}
	response, err := client.Get(endpoint)
	if err != nil {
		return Suggestion{}, err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 1<<20))
	if err != nil {
		return Suggestion{}, err
	}
	if response.StatusCode != http.StatusOK {
		return Suggestion{}, fmt.Errorf("server returned %s", response.Status)
	}
	var suggestion Suggestion
	if err := json.Unmarshal(body, &suggestion); err != nil {
		return Suggestion{}, err
	}
	return suggestion, nil
}

func fetchBayPanels(baseURL, bayID string) ([]Panel, error) {
	endpoint := strings.TrimRight(baseURL, "/") + "/bays/" + bayID
	client := &http.Client{Timeout: liveServerTimeout}
	response, err := client.Get(endpoint)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 4<<20))
	if err != nil {
		return nil, err
	}
	if response.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("server returned %s", response.Status)
	}
	var payload struct {
		Panels []Panel `json:"panels"`
	}
	if err := json.Unmarshal(body, &payload); err != nil {
		return nil, err
	}
	if payload.Panels == nil {
		payload.Panels = []Panel{}
	}
	return payload.Panels, nil
}

func fetchPanel(baseURL, panelID string) (Panel, error) {
	endpoint := strings.TrimRight(baseURL, "/") + "/panels/" + panelID
	client := &http.Client{Timeout: liveServerTimeout}
	response, err := client.Get(endpoint)
	if err != nil {
		return Panel{}, err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 1<<20))
	if err != nil {
		return Panel{}, err
	}
	if response.StatusCode != http.StatusOK {
		return Panel{}, fmt.Errorf("server returned %s", response.Status)
	}
	var panel Panel
	if err := json.Unmarshal(body, &panel); err != nil {
		return Panel{}, err
	}
	return panel, nil
}

func applyBriefWeather(fixtures []Panel, observation Panel, err error) []Panel {
	if err != nil || !observationConfigured(observation) {
		return fixtures
	}
	observation.Items = homeItems(observation)
	if len(observation.Items) == 0 {
		return fixtures
	}
	out := make([]Panel, len(fixtures))
	copy(out, fixtures)
	for i, panel := range out {
		if panel.Domain == "weather" {
			out[i] = observation
			return out
		}
	}
	return fixtures
}

func homeItems(panel Panel) []Item {
	kept := make([]Item, 0, len(panel.Items))
	for _, item := range panel.Items {
		home, _ := item.Fields["home"].(bool)
		if home {
			kept = append(kept, item)
		}
	}
	return kept
}

func observationConfigured(panel Panel) bool {
	for _, item := range panel.Items {
		configured, _ := item.Fields["configured"].(bool)
		if configured {
			return true
		}
	}
	return false
}

func mergeRefresh(previous []Panel, next []Panel, err error) []Panel {
	if err == nil {
		return next
	}
	if len(previous) == 0 {
		return previous
	}
	kept := make([]Panel, len(previous))
	for i, panel := range previous {
		panel.Stale = true
		if panel.StaleReason == "" {
			panel.StaleReason = "server unreachable"
		}
		kept[i] = panel
	}
	return kept
}
