//go:build linux

package main

import (
	"os/exec"
	"syscall"
	"time"
)

// setCmdProcessGroup puts the command in its own process group (pgid = cmd.Process.Pid)
// so that when Temporal cancels the activity, SIGKILL is sent to the whole group,
// killing bash and all child processes (nuclei, amass, etc.) instead of only bash.
func setCmdProcessGroup(cmd *exec.Cmd) {
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}
	cmd.Cancel = func() error {
		if cmd.Process != nil {
			return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		}
		return nil
	}
	cmd.WaitDelay = 5 * time.Second
}
