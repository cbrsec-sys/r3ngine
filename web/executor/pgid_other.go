//go:build !linux

package main

import (
	"os/exec"
	"time"
)

// setCmdProcessGroup is a no-op on non-Linux platforms.
// The process group / SIGKILL behaviour is Linux-specific; the executor
// always runs inside a Linux Docker container in production.
func setCmdProcessGroup(cmd *exec.Cmd) {
	cmd.WaitDelay = 5 * time.Second
}
