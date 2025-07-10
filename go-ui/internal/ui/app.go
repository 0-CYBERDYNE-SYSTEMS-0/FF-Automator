package ui

import (
	"context"
	"encoding/json"
	"fmt"
	"log"

	"github.com/macOS-use/go-ui/internal/backend"
	"github.com/macOS-use/go-ui/internal/websocket"
	"github.com/wailsapp/wails/v2/pkg/runtime"
)

type App struct {
	ctx           context.Context
	pythonManager *backend.PythonManager
	wsClient      *websocket.Client
}

type Provider struct {
	Name      string   `json:"name"`
	Models    []string `json:"models"`
	Available bool     `json:"available"`
}

type ChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type TaskRequest struct {
	Type     string `json:"type"` // "chat" or "agent"
	Message  string `json:"message"`
	Provider string `json:"provider"`
	Model    string `json:"model"`
}

func NewApp() *App {
	return &App{}
}

func (a *App) OnStartup(ctx context.Context, pythonManager *backend.PythonManager) {
	a.ctx = ctx
	a.pythonManager = pythonManager
	
	// Initialize WebSocket client
	a.wsClient = websocket.NewClient(pythonManager.GetBackendURL())
	
	// Set up WebSocket message handler
	a.wsClient.OnMessage(func(message []byte) {
		// Emit message to frontend
		runtime.EventsEmit(a.ctx, "backend-message", string(message))
	})
	
	// Connect to WebSocket
	if err := a.wsClient.Connect(); err != nil {
		log.Printf("Failed to connect to WebSocket: %v", err)
	}
	
	// Start forwarding Python logs to frontend
	go a.forwardLogs()
}

func (a *App) OnShutdown(ctx context.Context) {
	if a.wsClient != nil {
		a.wsClient.Close()
	}
}

// GetProviders returns available LLM providers
func (a *App) GetProviders() ([]Provider, error) {
	// This would make an HTTP request to the Python backend
	// For now, returning mock data
	return []Provider{
		{Name: "OpenAI", Models: []string{"gpt-4", "gpt-4o", "gpt-3.5-turbo"}, Available: true},
		{Name: "Anthropic", Models: []string{"claude-3-opus", "claude-3-sonnet"}, Available: true},
		{Name: "Google", Models: []string{"gemini-pro", "gemini-pro-vision"}, Available: true},
	}, nil
}

// SendTask sends a task to the Python backend
func (a *App) SendTask(request TaskRequest) error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	message, err := json.Marshal(request)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// StopTask interrupts the current task
func (a *App) StopTask() error {
	stopMsg := map[string]string{"type": "stop"}
	message, err := json.Marshal(stopMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// GetSessions returns saved sessions
func (a *App) GetSessions() ([]string, error) {
	// This would make an HTTP request to the Python backend
	return []string{"session1", "session2"}, nil
}

// LoadSession loads a saved session
func (a *App) LoadSession(name string) error {
	// Implementation would load session from backend
	return nil
}

// SaveSession saves the current session
func (a *App) SaveSession(name string) error {
	// Implementation would save session to backend
	return nil
}

// forwardLogs forwards Python backend logs to the frontend
func (a *App) forwardLogs() {
	logChan := a.pythonManager.GetLogs()
	for log := range logChan {
		runtime.EventsEmit(a.ctx, "backend-log", log)
	}
}