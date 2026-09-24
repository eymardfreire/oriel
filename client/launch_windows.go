//go:build windows

package main

import (
	"os/exec"
	"syscall"
)

func setNewConsole(command *exec.Cmd) {
	command.SysProcAttr = &syscall.SysProcAttr{CreationFlags: 0x00000010}
}
