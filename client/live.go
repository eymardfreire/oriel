package main

import (
	"bytes"
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
	case "wires", "markets", "trade", "storm", "field", "far", "fantasy", "sideline":
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

func visibleSuggestion(suggestion Suggestion, deskBays, shown []string) Suggestion {
	if suggestion.DeskID == "" || len(deskBays) == 0 {
		return suggestion
	}
	have := map[string]bool{}
	for _, id := range shown {
		have[id] = true
	}
	for _, id := range deskBays {
		if !have[id] {
			return suggestion
		}
	}
	return Suggestion{}
}

func suggestionLine(suggestion Suggestion) string {
	if suggestion.DeskID == "" {
		return ""
	}
	return "suggestion  " + suggestion.DeskID + " — " + suggestion.Reason + ". Press a to open it."
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

func postSideline(baseURL, sport string, follow bool) ([]Panel, error) {
	payload, err := json.Marshal(map[string]any{"sport": sport, "follow": follow})
	if err != nil {
		return nil, err
	}
	return postJSON(strings.TrimRight(baseURL, "/")+"/bays/sideline/focus", payload)
}

func postFollow(baseURL, competitionID string, follow bool) ([]Panel, error) {
	payload, err := json.Marshal(map[string]any{"competition_id": competitionID, "follow": follow})
	if err != nil {
		return nil, err
	}
	return postJSON(strings.TrimRight(baseURL, "/")+"/bays/field/follows", payload)
}

func postJSON(endpoint string, payload []byte) ([]Panel, error) {
	request, err := http.NewRequest(http.MethodPost, endpoint, bytes.NewReader(payload))
	if err != nil {
		return nil, err
	}
	request.Header.Set("Content-Type", "application/json")
	client := &http.Client{Timeout: liveServerTimeout}
	response, err := client.Do(request)
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
	var decoded struct {
		Panels []Panel `json:"panels"`
	}
	if err := json.Unmarshal(body, &decoded); err != nil {
		return nil, err
	}
	if decoded.Panels == nil {
		decoded.Panels = []Panel{}
	}
	return decoded.Panels, nil
}

type briefSelection struct {
	Place  string `json:"place"`
	Outlet string `json:"outlet"`
	Family string `json:"family"`
	Items  []Item `json:"items"`
}

func fetchBriefSelection(baseURL string) (briefSelection, error) {
	return briefJSON(http.MethodGet, strings.TrimRight(baseURL, "/")+"/bays/brief/selection", nil)
}

func postBriefSelection(baseURL, slot, id string) (briefSelection, error) {
	payload, err := json.Marshal(map[string]string{"slot": slot, "id": id})
	if err != nil {
		return briefSelection{}, err
	}
	return briefJSON(http.MethodPost, strings.TrimRight(baseURL, "/")+"/bays/brief/selection", payload)
}

func briefJSON(method, endpoint string, payload []byte) (briefSelection, error) {
	var request *http.Request
	var err error
	if payload == nil {
		request, err = http.NewRequest(method, endpoint, nil)
	} else {
		request, err = http.NewRequest(method, endpoint, bytes.NewReader(payload))
		if err == nil {
			request.Header.Set("Content-Type", "application/json")
		}
	}
	if err != nil {
		return briefSelection{}, err
	}
	client := &http.Client{Timeout: liveServerTimeout}
	response, err := client.Do(request)
	if err != nil {
		return briefSelection{}, err
	}
	defer response.Body.Close()
	body, err := io.ReadAll(io.LimitReader(response.Body, 1<<20))
	if err != nil {
		return briefSelection{}, err
	}
	if response.StatusCode != http.StatusOK {
		return briefSelection{}, fmt.Errorf("server returned %s", response.Status)
	}
	var selection briefSelection
	if err := json.Unmarshal(body, &selection); err != nil {
		return briefSelection{}, err
	}
	return selection, nil
}

func briefChoicesFrom(items []Item) []followChoice {
	choices := make([]followChoice, 0, len(items))
	for _, item := range items {
		if item.Row != "follow" {
			continue
		}
		id, _ := item.Fields["choice_id"].(string)
		slot, _ := item.Fields["slot"].(string)
		followed, _ := item.Fields["followed"].(bool)
		choices = append(choices, followChoice{ID: id, Name: item.Title, Followed: followed, Slot: slot})
	}
	return choices
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
	return applyBriefPlace(fixtures, observation, err, "")
}

func applyBriefPlace(current []Panel, observation Panel, err error, placeID string) []Panel {
	if err != nil || !observationConfigured(observation) {
		return current
	}
	items := homeItems(observation)
	if placeID != "" {
		items = placeObservation(observation, placeID)
	}
	if !usableObservation(items) {
		return current
	}
	observation.Items = items
	out := make([]Panel, len(current))
	copy(out, current)
	for i, panel := range out {
		if panel.Domain == "weather" {
			out[i] = observation
			return out
		}
	}
	return current
}

func applyBriefOutlet(current []Panel, live []Panel, err error, outletID string) []Panel {
	if outletID == "" {
		return applyBriefLead(current, "wires", live, err)
	}
	if err != nil {
		return current
	}
	item, panel, ok := newestOutlet(live, outletID)
	if !ok {
		return current
	}
	panel.Items = []Item{item}
	panel.Fixture = false
	return replaceDomain(current, "wires", panel)
}

func applyBriefFamily(current []Panel, live []Panel, err error, family string) []Panel {
	if family == "" {
		return applyBriefLead(current, "markets", live, err)
	}
	if err != nil {
		return current
	}
	for _, panel := range live {
		if panel.ID != "markets-"+family || len(panel.Items) == 0 {
			continue
		}
		panel.Items = panel.Items[:1]
		panel.Fixture = false
		return replaceDomain(current, "markets", panel)
	}
	return current
}

func applyBriefLead(panels []Panel, domain string, live []Panel, err error) []Panel {
	if err != nil {
		return panels
	}
	var chosen Panel
	found := false
	for _, panel := range live {
		if panel.Domain != domain || len(panel.Items) == 0 {
			continue
		}
		chosen = panel
		chosen.Items = panel.Items[:1]
		chosen.Fixture = false
		found = true
		break
	}
	if !found {
		return panels
	}
	out := append([]Panel(nil), panels...)
	for i, panel := range out {
		if panel.Domain == domain {
			out[i] = chosen
			return out
		}
	}
	return panels
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

func placeObservation(panel Panel, placeID string) []Item {
	want := "observation:" + placeID
	kept := make([]Item, 0, 1)
	for _, item := range panel.Items {
		if item.ID == want {
			kept = append(kept, item)
		}
	}
	return kept
}

func usableObservation(items []Item) bool {
	for _, item := range items {
		if item.Title == "Observation unavailable" {
			continue
		}
		if _, ok := item.Fields["temperature_c"]; ok {
			return true
		}
		if condition, _ := item.Fields["condition"].(string); condition != "" {
			return true
		}
	}
	return false
}

func newestOutlet(live []Panel, outletID string) (Item, Panel, bool) {
	var best Item
	var from Panel
	found := false
	prefix := outletID + ":"
	for _, panel := range live {
		if panel.Domain != "wires" {
			continue
		}
		for _, item := range panel.Items {
			if !strings.HasPrefix(item.ID, prefix) {
				continue
			}
			if !found || item.ObservedAt > best.ObservedAt {
				best = item
				from = panel
				found = true
			}
		}
	}
	return best, from, found
}

func replaceDomain(current []Panel, domain string, chosen Panel) []Panel {
	out := append([]Panel(nil), current...)
	for i, panel := range out {
		if panel.Domain == domain {
			out[i] = chosen
			return out
		}
	}
	return current
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
