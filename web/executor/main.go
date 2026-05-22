package main

import (
	"bytes"
	"context"
	"fmt"
	"io"
	"os"
	"os/exec"
	"syscall"
	"time"

	"go.temporal.io/sdk/activity"
	"go.temporal.io/sdk/client"
	"go.temporal.io/sdk/worker"
)

type ToolExecutionInput struct {
	Command []string `json:"command"`
	ScanID  int      `json:"scan_id"`
}

type ToolExecutionResult struct {
	Stdout     string  `json:"stdout"`
	Stderr     string  `json:"stderr"`
	ExitCode   int     `json:"exit_code"`
	TimeTakenS float64 `json:"time_taken_s"`
}

// SubprocessActivity executes the tool and sends heartbeats back to Temporal
func SubprocessActivity(ctx context.Context, input ToolExecutionInput) (ToolExecutionResult, error) {
	activity.GetLogger(ctx).Info("Starting subprocess tool execution", "command", input.Command)

	if len(input.Command) == 0 {
		return ToolExecutionResult{ExitCode: 1}, fmt.Errorf("empty command")
	}

	cmd := exec.CommandContext(ctx, input.Command[0], input.Command[1:]...)

	var stdoutBuf, stderrBuf bytes.Buffer
	
	// MultiWriter to write to both the buffer and os.Stdout/os.Stderr (so they appear in docker logs)
	cmd.Stdout = io.MultiWriter(&stdoutBuf, os.Stdout)
	cmd.Stderr = io.MultiWriter(&stderrBuf, os.Stderr)

	start := time.Now()
	if err := cmd.Start(); err != nil {
		return ToolExecutionResult{
			Stderr:   err.Error(),
			ExitCode: -1,
		}, err
	}

	// Keep heartbeating to Temporal every 5 seconds to prevent activity timeout
	stopHeartbeat := make(chan bool)
	go func() {
		ticker := time.NewTicker(5 * time.Second)
		defer ticker.Stop()
		for {
			select {
			case <-ticker.C:
				activity.RecordHeartbeat(ctx, fmt.Sprintf("running: %v elapsed", time.Since(start)))
			case <-stopHeartbeat:
				return
			}
		}
	}()
	defer close(stopHeartbeat)

	// Wait for tool completion
	err := cmd.Wait()
	timeTaken := time.Since(start).Seconds()

	var exitCode int
	if err != nil {
		if exitError, ok := err.(*exec.ExitError); ok {
			ws := exitError.Sys().(syscall.WaitStatus)
			exitCode = ws.ExitStatus()
		} else {
			exitCode = -2
		}
	}

	return ToolExecutionResult{
		Stdout:     stdoutBuf.String(),
		Stderr:     stderrBuf.String(),
		ExitCode:   exitCode,
		TimeTakenS: timeTaken,
	}, nil
}

func main() {
	temporalHost := os.Getenv("TEMPORAL_HOST")
	if temporalHost == "" {
		temporalHost = "temporal:7233"
	}
	namespace := os.Getenv("TEMPORAL_NAMESPACE")
	if namespace == "" {
		namespace = "default"
	}

	var c client.Client
	var err error
	maxRetries := 30
	retryInterval := 2 * time.Second

	for i := 1; i <= maxRetries; i++ {
		c, err = client.Dial(client.Options{
			HostPort:  temporalHost,
			Namespace: namespace,
		})
		if err == nil {
			break
		}
		fmt.Printf("Failed to connect to Temporal (attempt %d/%d): %v. Retrying in %v...\n", i, maxRetries, err, retryInterval)
		time.Sleep(retryInterval)
	}
	if err != nil {
		panic(fmt.Sprintf("failed reaching server: %v", err))
	}
	defer c.Close()

	w := worker.New(c, "go-executor-queue", worker.Options{})

	// Register subprocess command worker activity
	w.RegisterActivityWithOptions(SubprocessActivity, activity.RegisterOptions{
		Name: "RunToolSubprocessActivity",
	})

	err = w.Run(worker.InterruptCh())
	if err != nil {
		panic(err)
	}
}
