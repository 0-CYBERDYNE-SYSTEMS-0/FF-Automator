package backend

import (
	"bufio"
	"context"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"github.com/joho/godotenv"
)

type PythonManager struct {
	cmd          *exec.Cmd
	projectRoot  string
	envPath      string
	pythonPath   string
	backendURL   string
	logChan      chan string
}

func NewPythonManager() *PythonManager {
	// Get project root (parent of go-ui directory)
	wd, _ := os.Getwd()
	projectRoot := filepath.Join(wd, "..")
	
	return &PythonManager{
		projectRoot: projectRoot,
		envPath:     filepath.Join(projectRoot, ".env"),
		pythonPath:  filepath.Join(projectRoot, ".venv", "bin", "python"),
		backendURL:  "http://localhost:8080",
		logChan:     make(chan string, 100),
	}
}

func (pm *PythonManager) Start() error {
	// Load environment variables
	if err := godotenv.Load(pm.envPath); err != nil {
		log.Printf("Warning: Could not load .env file: %v", err)
	}

	// Check if Python venv exists
	if _, err := os.Stat(pm.pythonPath); os.IsNotExist(err) {
		return fmt.Errorf("Python virtual environment not found at %s. Please run 'uv venv && uv pip install --editable .' first", pm.pythonPath)
	}

	// Start the Python backend
	pm.cmd = exec.Command(pm.pythonPath, filepath.Join(pm.projectRoot, "web_interface", "api", "main.py"))
	pm.cmd.Dir = pm.projectRoot
	pm.cmd.Env = os.Environ()

	// Capture stdout and stderr
	stdout, err := pm.cmd.StdoutPipe()
	if err != nil {
		return err
	}
	stderr, err := pm.cmd.StderrPipe()
	if err != nil {
		return err
	}

	// Start log readers
	go pm.readLogs(stdout, "stdout")
	go pm.readLogs(stderr, "stderr")

	// Start the process
	if err := pm.cmd.Start(); err != nil {
		return fmt.Errorf("failed to start Python backend: %v", err)
	}

	log.Println("Python backend starting...")
	return nil
}

func (pm *PythonManager) Stop() error {
	if pm.cmd != nil && pm.cmd.Process != nil {
		// Send interrupt signal
		if err := pm.cmd.Process.Signal(os.Interrupt); err != nil {
			// If interrupt fails, kill the process
			return pm.cmd.Process.Kill()
		}
		
		// Wait for graceful shutdown
		done := make(chan error, 1)
		go func() {
			done <- pm.cmd.Wait()
		}()
		
		select {
		case <-done:
			return nil
		case <-time.After(5 * time.Second):
			// Force kill if not shut down after 5 seconds
			return pm.cmd.Process.Kill()
		}
	}
	return nil
}

func (pm *PythonManager) WaitForReady(ctx context.Context) error {
	client := &http.Client{Timeout: 2 * time.Second}
	
	ticker := time.NewTicker(500 * time.Millisecond)
	defer ticker.Stop()
	
	timeout := time.After(30 * time.Second)
	
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-timeout:
			return fmt.Errorf("timeout waiting for backend to start")
		case <-ticker.C:
			resp, err := client.Get(pm.backendURL + "/api/providers")
			if err == nil {
				resp.Body.Close()
				if resp.StatusCode == http.StatusOK {
					log.Println("Python backend is ready")
					return nil
				}
			}
		}
	}
}

func (pm *PythonManager) readLogs(pipe *os.File, source string) {
	scanner := bufio.NewScanner(pipe)
	for scanner.Scan() {
		line := scanner.Text()
		log.Printf("[Python %s] %s", source, line)
		
		// Send to log channel for UI display
		select {
		case pm.logChan <- fmt.Sprintf("[%s] %s", source, line):
		default:
			// Drop log if channel is full
		}
	}
}

func (pm *PythonManager) GetLogs() <-chan string {
	return pm.logChan
}

func (pm *PythonManager) GetBackendURL() string {
	return pm.backendURL
}