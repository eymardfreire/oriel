//go:build !windows

package main

import "os/exec"

func setNewConsole(command *exec.Cmd) {}
