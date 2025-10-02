package ui

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
	"time"

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
	Type                  string `json:"type"` // "chat" or "agent"
	Message               string `json:"message"`
	Provider              string `json:"provider"`
	Model                 string `json:"model"`
	CustomSystemMessage   string `json:"custom_system_message,omitempty"`
}

type Session struct {
	Name                string        `json:"name"`
	Timestamp           string        `json:"timestamp"`
	MessageCount        int           `json:"message_count"`
	SuccessCount        int           `json:"success_count"`
	FailureCount        int           `json:"failure_count"`
	ConversationHistory []ChatMessage `json:"conversation_history"`
}

type Automation struct {
	ID                    string            `json:"id"`
	Name                  string            `json:"name"`
	Description           string            `json:"description"`
	Task                  string            `json:"task"`
	Category              string            `json:"category"`
	Tags                  []string          `json:"tags"`
	LLMProvider           string            `json:"llm_provider"`
	LLMModel              string            `json:"llm_model"`
	CustomSystemMessage   string            `json:"custom_system_message,omitempty"`
	ConversationHistory   []ChatMessage     `json:"conversation_history"`
	CreatedAt             string            `json:"created_at"`
	ExecutionCount        int               `json:"execution_count"`
	SuccessCount          int               `json:"success_count"`
	FailureCount          int               `json:"failure_count"`
	LastExecutedAt        string            `json:"last_executed_at"`
	RuntimeParameters     map[string]interface{} `json:"runtime_parameters,omitempty"`
}

type AutomationTemplate struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Task        string                 `json:"task"`
	Category    string                 `json:"category"`
	Tags        []string               `json:"tags"`
	Parameters  map[string]interface{} `json:"parameters,omitempty"`
}

type AutomationSchedule struct {
	CronExpression string `json:"cron_expression"`
	Enabled        bool   `json:"enabled"`
	NextRun        string `json:"next_run"`
	LastRun        string `json:"last_run"`
}

type AutomationHistory struct {
	ExecutionID  string `json:"execution_id"`
	ExecutedAt   string `json:"executed_at"`
	Status       string `json:"status"`
	Duration     int    `json:"duration"`
	ErrorMessage string `json:"error_message,omitempty"`
}

type ScheduledAutomation struct {
	AutomationID   string                `json:"automation_id"`
	Name           string                `json:"name"`
	Schedules      []AutomationSchedule  `json:"schedules"`
	NextExecution  string                `json:"next_execution"`
	LastExecution  string                `json:"last_execution"`
}

type SearchResult struct {
	Automations []Automation `json:"automations"`
	Total       int          `json:"total"`
}

type ProviderTestResult struct {
	Provider  string `json:"provider"`
	Status    string `json:"status"`
	Message   string `json:"message"`
	Latency   int    `json:"latency"`
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
		runtime.EventsEmit(a.ctx, "connection-error", err.Error())
	} else {
		runtime.EventsEmit(a.ctx, "connection-success", "WebSocket connected")
	}
	
	// Start forwarding Python logs to frontend
	go a.forwardLogs()
	
	// Start heartbeat to keep connection alive
	go a.startHeartbeat()
}

// startHeartbeat sends periodic ping messages to keep WebSocket alive
func (a *App) startHeartbeat() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			if a.wsClient != nil && a.wsClient.IsConnected() {
				pingMsg := map[string]string{"type": "ping"}
				if message, err := json.Marshal(pingMsg); err == nil {
					a.wsClient.Send(message)
				}
			}
		}
	}
}

func (a *App) OnShutdown(ctx context.Context) {
	if a.wsClient != nil {
		a.wsClient.Close()
	}
}

// GetProviders returns available LLM providers
func (a *App) GetProviders() ([]Provider, error) {
	// Create HTTP client with timeout
	client := &http.Client{
		Timeout: 30 * time.Second,
	}
	
	log.Println("Fetching providers from backend...")
	resp, err := client.Get(a.pythonManager.GetBackendURL() + "/api/providers")
	if err != nil {
		return nil, fmt.Errorf("failed to get providers: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("providers API returned status %d", resp.StatusCode)
	}

	var providers []Provider
	if err := json.NewDecoder(resp.Body).Decode(&providers); err != nil {
		return nil, fmt.Errorf("failed to decode providers: %v", err)
	}

	log.Printf("Successfully loaded %d providers", len(providers))
	return providers, nil
}

// InterruptChat interrupts the current chat
func (a *App) InterruptChat() error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	interruptMsg := map[string]string{"type": "interrupt_chat"}
	message, err := json.Marshal(interruptMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// RedirectChat redirects the current chat to a new task
func (a *App) RedirectChat(newTask string) error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	redirectMsg := map[string]interface{}{
		"type": "redirect_chat",
		"data": map[string]interface{}{
			"new_task": newTask,
		},
	}
	message, err := json.Marshal(redirectMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// AddTask adds a task to the chat queue
func (a *App) AddTask(task string) error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	addTaskMsg := map[string]interface{}{
		"type": "add_task",
		"data": map[string]interface{}{
			"task": task,
		},
	}
	message, err := json.Marshal(addTaskMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// SaveAutomationFromChat saves an automation from the current chat
func (a *App) SaveAutomationFromChat(name, description string) error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	saveMsg := map[string]interface{}{
		"type": "save_automation",
		"data": map[string]interface{}{
			"name":        name,
			"description": description,
		},
	}
	message, err := json.Marshal(saveMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// ExecuteAutomationViaWebSocket executes an automation via WebSocket
func (a *App) ExecuteAutomationViaWebSocket(automationID string, parameters map[string]interface{}) error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	executeMsg := map[string]interface{}{
		"type": "execute_automation",
		"data": map[string]interface{}{
			"automation_id": automationID,
			"parameters":    parameters,
		},
	}
	message, err := json.Marshal(executeMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// SendTask sends a task to the Python backend
func (a *App) SendTask(request TaskRequest) error {
	if a.wsClient == nil || !a.wsClient.IsConnected() {
		return fmt.Errorf("not connected to backend")
	}
	
	// Format message according to Python backend protocol
	var wsMessage map[string]interface{}
	
	if request.Type == "chat" {
		wsMessage = map[string]interface{}{
			"type": "chat_message",
			"data": map[string]interface{}{
				"message":               request.Message,
				"llm_provider":         request.Provider,
				"llm_model":            request.Model,
				"custom_system_message": request.CustomSystemMessage,
			},
		}
	} else if request.Type == "agent" {
		wsMessage = map[string]interface{}{
			"type": "agent_task",
			"data": map[string]interface{}{
				"task":                 request.Message,
				"max_steps":            100,
				"max_actions":          10,
				"llm_provider":         request.Provider,
				"llm_model":            request.Model,
				"custom_system_message": request.CustomSystemMessage,
			},
		}
	} else {
		return fmt.Errorf("unsupported task type: %s", request.Type)
	}
	
	message, err := json.Marshal(wsMessage)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// StopTask interrupts the current task
func (a *App) StopTask() error {
	stopMsg := map[string]string{"type": "stop_chat"}
	message, err := json.Marshal(stopMsg)
	if err != nil {
		return err
	}
	
	return a.wsClient.Send(message)
}

// GetSessions returns saved sessions
func (a *App) GetSessions() ([]Session, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/sessions")
	if err != nil {
		return nil, fmt.Errorf("failed to get sessions: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("sessions API returned status %d", resp.StatusCode)
	}

	var sessions []Session
	if err := json.NewDecoder(resp.Body).Decode(&sessions); err != nil {
		return nil, fmt.Errorf("failed to decode sessions: %v", err)
	}

	return sessions, nil
}

// LoadSession loads a saved session
func (a *App) LoadSession(name string) (*Session, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/sessions/" + name)
	if err != nil {
		return nil, fmt.Errorf("failed to load session: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("session API returned status %d", resp.StatusCode)
	}

	var session Session
	if err := json.NewDecoder(resp.Body).Decode(&session); err != nil {
		return nil, fmt.Errorf("failed to decode session: %v", err)
	}

	return &session, nil
}

// SaveSession saves the current session
func (a *App) SaveSession(session Session) error {
	jsonData, err := json.Marshal(session)
	if err != nil {
		return fmt.Errorf("failed to marshal session: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/sessions", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to save session: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("save session API returned status %d", resp.StatusCode)
	}

	return nil
}

// DeleteSession deletes a saved session
func (a *App) DeleteSession(name string) error {
	req, err := http.NewRequest("DELETE", a.pythonManager.GetBackendURL()+"/api/sessions/"+name, nil)
	if err != nil {
		return fmt.Errorf("failed to create delete request: %v", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to delete session: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("delete session API returned status %d", resp.StatusCode)
	}

	return nil
}

// GetAutomations returns saved automations
func (a *App) GetAutomations() ([]Automation, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/automations")
	if err != nil {
		return nil, fmt.Errorf("failed to get automations: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("automations API returned status %d", resp.StatusCode)
	}

	var automations []Automation
	if err := json.NewDecoder(resp.Body).Decode(&automations); err != nil {
		return nil, fmt.Errorf("failed to decode automations: %v", err)
	}

	return automations, nil
}

// GetAutomation returns a specific automation by ID
func (a *App) GetAutomation(id string) (*Automation, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/automations/" + id)
	if err != nil {
		return nil, fmt.Errorf("failed to get automation: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("automation API returned status %d", resp.StatusCode)
	}

	var automation Automation
	if err := json.NewDecoder(resp.Body).Decode(&automation); err != nil {
		return nil, fmt.Errorf("failed to decode automation: %v", err)
	}

	return &automation, nil
}

// SaveAutomation saves a new automation
func (a *App) SaveAutomation(automation Automation) error {
	jsonData, err := json.Marshal(automation)
	if err != nil {
		return fmt.Errorf("failed to marshal automation: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/automations", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to save automation: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("save automation API returned status %d", resp.StatusCode)
	}

	return nil
}

// DeleteAutomation deletes an automation
func (a *App) DeleteAutomation(id string) error {
	req, err := http.NewRequest("DELETE", a.pythonManager.GetBackendURL()+"/api/automations/"+id, nil)
	if err != nil {
		return fmt.Errorf("failed to create delete request: %v", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to delete automation: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("delete automation API returned status %d", resp.StatusCode)
	}

	return nil
}

// ExecuteAutomation executes an automation
func (a *App) ExecuteAutomation(id string, parameters map[string]interface{}) error {
	requestData := map[string]interface{}{
		"automation_id":       id,
		"runtime_parameters": parameters,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return fmt.Errorf("failed to marshal execute request: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/automations/"+id+"/execute", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to execute automation: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("execute automation API returned status %d", resp.StatusCode)
	}

	return nil
}

// GetAutomationTemplates returns available automation templates
func (a *App) GetAutomationTemplates() ([]AutomationTemplate, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/automation-templates")
	if err != nil {
		return nil, fmt.Errorf("failed to get automation templates: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("automation templates API returned status %d", resp.StatusCode)
	}

	var templates []AutomationTemplate
	if err := json.NewDecoder(resp.Body).Decode(&templates); err != nil {
		return nil, fmt.Errorf("failed to decode automation templates: %v", err)
	}

	return templates, nil
}

// CreateAutomationFromTemplate creates an automation from a template
func (a *App) CreateAutomationFromTemplate(templateName string, parameters map[string]interface{}) error {
	jsonData, err := json.Marshal(parameters)
	if err != nil {
		return fmt.Errorf("failed to marshal template parameters: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/automation-templates/"+templateName, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to create automation from template: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("create automation from template API returned status %d", resp.StatusCode)
	}

	return nil
}

// GetAutomationCategories returns available automation categories
func (a *App) GetAutomationCategories() ([]string, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/automation-categories")
	if err != nil {
		return nil, fmt.Errorf("failed to get automation categories: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("automation categories API returned status %d", resp.StatusCode)
	}

	var categories []string
	if err := json.NewDecoder(resp.Body).Decode(&categories); err != nil {
		return nil, fmt.Errorf("failed to decode automation categories: %v", err)
	}

	return categories, nil
}

// GetAutomationTags returns available automation tags
func (a *App) GetAutomationTags() ([]string, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/automation-tags")
	if err != nil {
		return nil, fmt.Errorf("failed to get automation tags: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("automation tags API returned status %d", resp.StatusCode)
	}

	var tags []string
	if err := json.NewDecoder(resp.Body).Decode(&tags); err != nil {
		return nil, fmt.Errorf("failed to decode automation tags: %v", err)
	}

	return tags, nil
}

// TestProvider tests a provider connection
func (a *App) TestProvider(provider string) (*ProviderTestResult, error) {
	requestData := map[string]string{
		"provider": provider,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal test request: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/providers/test", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to test provider: %v", err)
	}
	defer resp.Body.Close()

	var result ProviderTestResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode test result: %v", err)
	}

	return &result, nil
}

// SearchAutomations searches for automations
func (a *App) SearchAutomations(query, category string, tags []string) (*SearchResult, error) {
	url := a.pythonManager.GetBackendURL() + "/api/automations/search"
	params := make([]string, 0)
	
	if query != "" {
		params = append(params, "q="+query)
	}
	if category != "" {
		params = append(params, "category="+category)
	}
	for _, tag := range tags {
		params = append(params, "tags="+tag)
	}
	
	if len(params) > 0 {
		url += "?" + strings.Join(params, "&")
	}

	resp, err := http.Get(url)
	if err != nil {
		return nil, fmt.Errorf("failed to search automations: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("search API returned status %d", resp.StatusCode)
	}

	var result SearchResult
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("failed to decode search result: %v", err)
	}

	return &result, nil
}

// DuplicateAutomation duplicates an existing automation
func (a *App) DuplicateAutomation(automationID, newName string) error {
	requestData := map[string]string{
		"new_name": newName,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return fmt.Errorf("failed to marshal duplicate request: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/automations/"+automationID+"/duplicate", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to duplicate automation: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("duplicate automation API returned status %d", resp.StatusCode)
	}

	return nil
}

// GetAutomationHistory gets execution history for an automation
func (a *App) GetAutomationHistory(automationID string) ([]AutomationHistory, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/automations/" + automationID + "/history")
	if err != nil {
		return nil, fmt.Errorf("failed to get automation history: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("history API returned status %d", resp.StatusCode)
	}

	var history []AutomationHistory
	if err := json.NewDecoder(resp.Body).Decode(&history); err != nil {
		return nil, fmt.Errorf("failed to decode history: %v", err)
	}

	return history, nil
}

// ScheduleAutomation schedules an automation
func (a *App) ScheduleAutomation(automationID, cronExpression string, enabled bool) error {
	requestData := map[string]interface{}{
		"cron_expression": cronExpression,
		"enabled":         enabled,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return fmt.Errorf("failed to marshal schedule request: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/automations/"+automationID+"/schedule", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to schedule automation: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("schedule automation API returned status %d", resp.StatusCode)
	}

	return nil
}

// RemoveAutomationSchedule removes a schedule from an automation
func (a *App) RemoveAutomationSchedule(automationID string, scheduleIndex int) error {
	req, err := http.NewRequest("DELETE", a.pythonManager.GetBackendURL()+"/api/automations/"+automationID+"/schedule/"+fmt.Sprintf("%d", scheduleIndex), nil)
	if err != nil {
		return fmt.Errorf("failed to create delete request: %v", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to remove schedule: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("remove schedule API returned status %d", resp.StatusCode)
	}

	return nil
}

// GetScheduledAutomations gets all scheduled automations
func (a *App) GetScheduledAutomations() ([]ScheduledAutomation, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/scheduled-automations")
	if err != nil {
		return nil, fmt.Errorf("failed to get scheduled automations: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("scheduled automations API returned status %d", resp.StatusCode)
	}

	var scheduled []ScheduledAutomation
	if err := json.NewDecoder(resp.Body).Decode(&scheduled); err != nil {
		return nil, fmt.Errorf("failed to decode scheduled automations: %v", err)
	}

	return scheduled, nil
}

// RefinePrompt refines a prompt using AI
func (a *App) RefinePrompt(prompt, provider, model string) (string, error) {
	requestData := map[string]string{
		"prompt":   prompt,
		"provider": provider,
		"model":    model,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return "", fmt.Errorf("failed to marshal refine request: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/refine-prompt", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to refine prompt: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("refine prompt API returned status %d", resp.StatusCode)
	}

	var result map[string]string
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("failed to decode refine result: %v", err)
	}

	return result["refined_prompt"], nil
}

// SendChatMessage sends a message via alternative chat endpoint
func (a *App) SendChatMessage(message, provider, model, systemMessage string) error {
	requestData := map[string]interface{}{
		"message":               message,
		"llm_provider":         provider,
		"llm_model":            model,
		"custom_system_message": systemMessage,
	}

	jsonData, err := json.Marshal(requestData)
	if err != nil {
		return fmt.Errorf("failed to marshal chat request: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/chat/send", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to send chat message: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("chat send API returned status %d", resp.StatusCode)
	}

	return nil
}

// GetBackendURL returns the Python backend URL for direct fetch calls from frontend
func (a *App) GetBackendURL() string {
	return a.pythonManager.GetBackendURL()
}

// Context Bucket methods
type ContextBucketItem struct {
	ID          string `json:"id"`
	Type        string `json:"type"`
	Title       string `json:"title"`
	Content     string `json:"content"`
	Priority    string `json:"priority"`
	Tags        []string `json:"tags"`
	CreatedAt   string `json:"created_at"`
	TokenCount  int    `json:"token_count"`
}

type ContextBucketSummary struct {
	TotalItems    int     `json:"total_items"`
	TotalTokens   int     `json:"total_tokens"`
	MaxTokens     int     `json:"max_tokens"`
	UsagePercent  float64 `json:"usage_percent"`
}

// GetContextBucketItems returns all context bucket items
func (a *App) GetContextBucketItems() ([]ContextBucketItem, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/context-bucket/items")
	if err != nil {
		return nil, fmt.Errorf("failed to get context bucket items: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("context bucket items API returned status %d", resp.StatusCode)
	}

	var items []ContextBucketItem
	if err := json.NewDecoder(resp.Body).Decode(&items); err != nil {
		return nil, fmt.Errorf("failed to decode context bucket items: %v", err)
	}

	return items, nil
}

// GetContextBucketSummary returns context bucket summary statistics
func (a *App) GetContextBucketSummary() (*ContextBucketSummary, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/context-bucket/summary")
	if err != nil {
		return nil, fmt.Errorf("failed to get context bucket summary: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("context bucket summary API returned status %d", resp.StatusCode)
	}

	var summary ContextBucketSummary
	if err := json.NewDecoder(resp.Body).Decode(&summary); err != nil {
		return nil, fmt.Errorf("failed to decode context bucket summary: %v", err)
	}

	return &summary, nil
}

// AddContextBucketItem adds a new item to the context bucket
func (a *App) AddContextBucketItem(item ContextBucketItem) error {
	jsonData, err := json.Marshal(item)
	if err != nil {
		return fmt.Errorf("failed to marshal context bucket item: %v", err)
	}

	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/context-bucket/items", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return fmt.Errorf("failed to add context bucket item: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		return fmt.Errorf("add context bucket item API returned status %d", resp.StatusCode)
	}

	return nil
}

// DeleteContextBucketItem removes an item from the context bucket
func (a *App) DeleteContextBucketItem(id string) error {
	req, err := http.NewRequest("DELETE", a.pythonManager.GetBackendURL()+"/api/context-bucket/items/"+id, nil)
	if err != nil {
		return fmt.Errorf("failed to create delete request: %v", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to delete context bucket item: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("delete context bucket item API returned status %d", resp.StatusCode)
	}

	return nil
}

// ClearContextBucket removes all items from the context bucket
func (a *App) ClearContextBucket() error {
	req, err := http.NewRequest("DELETE", a.pythonManager.GetBackendURL()+"/api/context-bucket/items", nil)
	if err != nil {
		return fmt.Errorf("failed to create clear request: %v", err)
	}

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to clear context bucket: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("clear context bucket API returned status %d", resp.StatusCode)
	}

	return nil
}

// ExportContextBucket exports all context bucket items
func (a *App) ExportContextBucket() ([]byte, error) {
	resp, err := http.Get(a.pythonManager.GetBackendURL() + "/api/context-bucket/export")
	if err != nil {
		return nil, fmt.Errorf("failed to export context bucket: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("export context bucket API returned status %d", resp.StatusCode)
	}

	data, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read export data: %v", err)
	}

	return data, nil
}

// ImportContextBucket imports items into the context bucket
func (a *App) ImportContextBucket(data []byte) error {
	resp, err := http.Post(a.pythonManager.GetBackendURL()+"/api/context-bucket/import", "application/json", bytes.NewBuffer(data))
	if err != nil {
		return fmt.Errorf("failed to import context bucket: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("import context bucket API returned status %d", resp.StatusCode)
	}

	return nil
}

// forwardLogs forwards Python backend logs to the frontend
func (a *App) forwardLogs() {
	logChan := a.pythonManager.GetLogs()
	for log := range logChan {
		runtime.EventsEmit(a.ctx, "backend-log", log)
	}
}