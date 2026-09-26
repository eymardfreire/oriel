package main

import (
	"os/exec"
	"strings"
)

func arrangement(desk Desk) string {
	lines := []string{"desk " + desk.ID}
	for _, bay := range desk.Bays {
		lines = append(lines, bay.ID+" — "+bay.Role)
	}
	return strings.Join(lines, "\n")
}

func startDesk(desk Desk, start func(bayID string) error) (string, error) {
	for _, bay := range desk.Bays {
		if err := start(bay.ID); err != nil {
			return "", err
		}
	}
	return arrangement(desk), nil
}

func applySuggestion(panels []Panel, deskID string) ([]Panel, string) {
	kept := make([]Panel, len(panels))
	copy(kept, panels)
	return kept, deskID
}

func launchProcesses(exe, server string, desk Desk) (string, error) {
	return startDesk(desk, func(bayID string) error {
		command := launchCommand(exe, server, bayID)
		return command.Start()
	})
}

func launchCommand(exe, server, bayID string) *exec.Cmd {
	command := bayCommand(exe, server, bayID)
	command.Stdout = nil
	command.Stderr = nil
	return command
}

func bayCommand(exe, server, bayID string) *exec.Cmd {
	command := exec.Command(exe, "-bay", bayID, "-server", server)
	setNewConsole(command)
	return command
}
