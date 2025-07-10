// App state
let currentMode = 'chat';
let isExecuting = false;
let providers = [];
let selectedProvider = null;
let selectedModel = null;
let currentSession = null;
let conversationHistory = [];
let sessions = [];
let automations = [];
let automationTemplates = [];

// DOM elements
const providerSelect = document.getElementById('provider');
const modelSelect = document.getElementById('model');
const chatMessages = document.getElementById('chat-messages');
const chatInput = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const stopBtn = document.getElementById('stop-btn');
const terminalOutput = document.getElementById('terminal-output');
const agentInput = document.getElementById('agent-input');
const executeBtn = document.getElementById('execute-btn');
const stopAgentBtn = document.getElementById('stop-agent-btn');
const connectionStatus = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');
const logContent = document.getElementById('log-content');
const logPanel = document.getElementById('log-panel');
const toggleLogsBtn = document.getElementById('toggle-logs');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadProviders();
    await loadSessions();
    await loadAutomations();
    setupEventListeners();
    setupWailsEvents();
});

// Setup event listeners
function setupEventListeners() {
    // Mode switching
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });
    
    // Provider/model selection
    providerSelect.addEventListener('change', onProviderChange);
    modelSelect.addEventListener('change', onModelChange);
    
    // Chat controls
    sendBtn.addEventListener('click', sendChatMessage);
    stopBtn.addEventListener('click', stopExecution);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Agent controls
    executeBtn.addEventListener('click', executeAgent);
    stopAgentBtn.addEventListener('click', stopExecution);
    agentInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            executeAgent();
        }
    });
    
    // Log panel
    toggleLogsBtn.addEventListener('click', () => {
        logPanel.classList.toggle('expanded');
        toggleLogsBtn.textContent = logPanel.classList.contains('expanded') ? '▲' : '▼';
    });

    // Session management
    const saveSessionBtn = document.getElementById('save-session');
    const loadSessionBtn = document.getElementById('load-session');
    const sessionSelect = document.getElementById('session-list');
    
    saveSessionBtn.addEventListener('click', saveCurrentSession);
    loadSessionBtn.addEventListener('click', loadSelectedSession);
    sessionSelect.addEventListener('change', onSessionSelectChange);
    
    // Automation management
    const saveAutomationBtn = document.getElementById('save-automation');
    const runAutomationBtn = document.getElementById('run-automation');
    const automationSelect = document.getElementById('automation-list');
    
    saveAutomationBtn.addEventListener('click', saveCurrentAutomation);
    runAutomationBtn.addEventListener('click', runSelectedAutomation);
    automationSelect.addEventListener('change', onAutomationSelectChange);
}

// Setup Wails event listeners
function setupWailsEvents() {
    // Backend messages
    window.runtime.EventsOn('backend-message', (message) => {
        const data = JSON.parse(message);
        handleBackendMessage(data);
    });
    
    // Backend logs
    window.runtime.EventsOn('backend-log', (log) => {
        appendLog(log);
    });
    
    // Connection status events
    window.runtime.EventsOn('connection-success', (message) => {
        updateConnectionStatus('connected');
        console.log('WebSocket connected:', message);
    });
    
    window.runtime.EventsOn('connection-error', (error) => {
        updateConnectionStatus('error');
        console.error('WebSocket connection error:', error);
        appendChatMessage('system', `Connection error: ${error}`);
    });
}

// Load providers
async function loadProviders() {
    try {
        providers = await window.go.ui.App.GetProviders();
        
        providerSelect.innerHTML = '<option value="">Select a provider</option>';
        providers.forEach(provider => {
            if (provider.available) {
                const option = document.createElement('option');
                option.value = provider.name;
                option.textContent = provider.name;
                providerSelect.appendChild(option);
            }
        });
        
        updateConnectionStatus('connected');
        updateUIState(); // Set initial button state
    } catch (error) {
        console.error('Failed to load providers:', error);
        updateConnectionStatus('error');
        updateUIState(); // Set initial button state even on error
    }
}

// Load sessions
async function loadSessions() {
    try {
        sessions = await window.go.ui.App.GetSessions();
        
        const sessionSelect = document.getElementById('session-list');
        sessionSelect.innerHTML = '<option value="">Select a session</option>';
        
        sessions.forEach(session => {
            const option = document.createElement('option');
            option.value = session.name;
            option.textContent = `${session.name} (${session.message_count} messages)`;
            sessionSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load sessions:', error);
    }
}

// Save current session
async function saveCurrentSession() {
    const sessionName = prompt('Enter session name:');
    if (!sessionName) return;
    
    try {
        const session = {
            name: sessionName,
            timestamp: new Date().toISOString(),
            message_count: conversationHistory.length,
            success_count: 0, // Could be tracked
            failure_count: 0, // Could be tracked
            conversation_history: conversationHistory
        };
        
        await window.go.ui.App.SaveSession(session);
        await loadSessions();
        
        appendChatMessage('system', `Session "${sessionName}" saved successfully`);
    } catch (error) {
        console.error('Failed to save session:', error);
        appendChatMessage('system', `Failed to save session: ${error.message}`);
    }
}

// Load selected session
async function loadSelectedSession() {
    const sessionSelect = document.getElementById('session-list');
    const sessionName = sessionSelect.value;
    
    if (!sessionName) {
        alert('Please select a session to load');
        return;
    }
    
    try {
        const session = await window.go.ui.App.LoadSession(sessionName);
        
        // Clear current chat
        chatMessages.innerHTML = '';
        conversationHistory = [];
        
        // Load conversation history
        if (session.conversation_history) {
            conversationHistory = session.conversation_history;
            session.conversation_history.forEach(msg => {
                appendChatMessage(msg.role, msg.content);
            });
        }
        
        currentSession = session;
        appendChatMessage('system', `Session "${sessionName}" loaded successfully`);
    } catch (error) {
        console.error('Failed to load session:', error);
        appendChatMessage('system', `Failed to load session: ${error.message}`);
    }
}

// Session select change handler
function onSessionSelectChange() {
    const sessionSelect = document.getElementById('session-list');
    const loadSessionBtn = document.getElementById('load-session');
    
    loadSessionBtn.disabled = !sessionSelect.value;
}

// Load automations
async function loadAutomations() {
    try {
        automations = await window.go.ui.App.GetAutomations();
        
        const automationSelect = document.getElementById('automation-list');
        automationSelect.innerHTML = '<option value="">Select an automation</option>';
        
        automations.forEach(automation => {
            const option = document.createElement('option');
            option.value = automation.id;
            option.textContent = `${automation.name} - ${automation.description}`;
            automationSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load automations:', error);
    }
}

// Save current automation
async function saveCurrentAutomation() {
    if (conversationHistory.length === 0) {
        alert('No conversation to save as automation');
        return;
    }
    
    const automationName = prompt('Enter automation name:');
    if (!automationName) return;
    
    const description = prompt('Enter automation description:') || '';
    
    try {
        const automation = {
            name: automationName,
            description: description,
            task: conversationHistory.length > 0 ? conversationHistory[0].content : '',
            category: 'General',
            tags: ['manual'],
            llm_provider: selectedProvider,
            llm_model: selectedModel,
            conversation_history: conversationHistory,
            created_at: new Date().toISOString(),
            execution_count: 0,
            success_count: 0,
            failure_count: 0
        };
        
        await window.go.ui.App.SaveAutomation(automation);
        await loadAutomations();
        
        appendChatMessage('system', `Automation "${automationName}" saved successfully`);
    } catch (error) {
        console.error('Failed to save automation:', error);
        appendChatMessage('system', `Failed to save automation: ${error.message}`);
    }
}

// Run selected automation
async function runSelectedAutomation() {
    const automationSelect = document.getElementById('automation-list');
    const automationId = automationSelect.value;
    
    if (!automationId) {
        alert('Please select an automation to run');
        return;
    }
    
    try {
        setExecuting(true);
        await window.go.ui.App.ExecuteAutomation(automationId, {});
        appendChatMessage('system', `Running automation...`);
    } catch (error) {
        console.error('Failed to run automation:', error);
        appendChatMessage('system', `Failed to run automation: ${error.message}`);
        setExecuting(false);
    }
}

// Automation select change handler
function onAutomationSelectChange() {
    const automationSelect = document.getElementById('automation-list');
    const runAutomationBtn = document.getElementById('run-automation');
    
    runAutomationBtn.disabled = !automationSelect.value;
}

// Provider change handler
function onProviderChange() {
    const providerName = providerSelect.value;
    selectedProvider = providerName;
    selectedModel = null; // Reset model selection
    
    modelSelect.innerHTML = '<option value="">Select a model</option>';
    
    if (providerName) {
        const provider = providers.find(p => p.name === providerName);
        if (provider) {
            provider.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
        }
    }
    
    updateUIState();
}

// Model change handler
function onModelChange() {
    selectedModel = modelSelect.value;
    updateUIState();
}

// Update UI state based on selection
function updateUIState() {
    const hasSelection = selectedProvider && selectedModel;
    
    // Enable/disable send buttons based on selection
    sendBtn.disabled = !hasSelection;
    executeBtn.disabled = !hasSelection;
    
    // Update button text to provide feedback
    if (!hasSelection) {
        sendBtn.textContent = 'Select Provider & Model';
        executeBtn.textContent = 'Select Provider & Model';
    } else {
        sendBtn.textContent = 'Send';
        executeBtn.textContent = 'Execute';
    }
}

// Switch mode
function switchMode(mode) {
    currentMode = mode;
    
    // Update buttons
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    
    // Update views
    document.getElementById('chat-view').classList.toggle('active', mode === 'chat');
    document.getElementById('agent-view').classList.toggle('active', mode === 'agent');
}

// Send chat message
async function sendChatMessage() {
    const message = chatInput.value.trim();
    
    if (!message) {
        appendChatMessage('system', 'Please enter a message');
        return;
    }
    
    if (!selectedProvider) {
        appendChatMessage('system', 'Please select a provider first');
        return;
    }
    
    if (!selectedModel) {
        appendChatMessage('system', 'Please select a model first');
        return;
    }
    
    // Add user message to chat and conversation history
    appendChatMessage('user', message);
    conversationHistory.push({ role: 'user', content: message });
    chatInput.value = '';
    
    // Update UI state
    setExecuting(true);
    
    try {
        await window.go.ui.App.SendTask({
            type: 'chat',
            message: message,
            provider: selectedProvider,
            model: selectedModel,
            custom_system_message: ''
        });
    } catch (error) {
        appendChatMessage('system', `Error: ${error.message || error}`);
        setExecuting(false);
    }
}

// Execute agent task
async function executeAgent() {
    const task = agentInput.value.trim();
    
    if (!task) {
        appendTerminalLine('Please enter a task');
        return;
    }
    
    if (!selectedProvider) {
        appendTerminalLine('Please select a provider first');
        return;
    }
    
    if (!selectedModel) {
        appendTerminalLine('Please select a model first');
        return;
    }
    
    // Clear terminal and add task
    terminalOutput.innerHTML = '';
    appendTerminalLine(`$ ${task}`);
    agentInput.value = '';
    
    // Update UI state
    setExecuting(true);
    
    try {
        await window.go.ui.App.SendTask({
            type: 'agent',
            message: task,
            provider: selectedProvider,
            model: selectedModel,
            custom_system_message: ''
        });
    } catch (error) {
        appendTerminalLine(`Error: ${error.message || error}`);
        setExecuting(false);
    }
}

// Stop execution
async function stopExecution() {
    try {
        await window.go.ui.App.StopTask();
        setExecuting(false);
        
        if (currentMode === 'chat') {
            appendChatMessage('system', 'Task stopped by user');
        } else {
            appendTerminalLine('Task stopped by user');
        }
    } catch (error) {
        console.error('Failed to stop task:', error);
    }
}

// Handle backend messages
function handleBackendMessage(data) {
    // Handle messages according to Python backend protocol
    if (data.type === 'chat_response') {
        if (data.data.content) {
            if (data.data.streaming) {
                // Update the last message with streaming content
                updateLastMessage(data.data.content);
            } else {
                // Add complete response
                appendChatMessage('assistant', data.data.content);
                conversationHistory.push({ role: 'assistant', content: data.data.content });
            }
        }
    } else if (data.type === 'chat_stream_update') {
        // Show progress updates
        if (data.data.message) {
            appendChatMessage('system', `Step ${data.data.step || 1}: ${data.data.message}`);
        }
    } else if (data.type === 'chat_complete') {
        setExecuting(false);
        if (data.data.final_result) {
            appendChatMessage('assistant', data.data.final_result);
            conversationHistory.push({ role: 'assistant', content: data.data.final_result });
        }
        if (data.data.message) {
            appendChatMessage('system', `Completed: ${data.data.message}`);
        }
    } else if (data.type === 'stream_update') {
        // Agent mode updates
        if (data.data.message) {
            appendTerminalLine(`Step ${data.data.step || 1}: ${data.data.message}`);
        }
        if (data.data.status === 'completed' || data.data.status === 'failed') {
            setExecuting(false);
            if (data.data.final_result) {
                appendTerminalLine(`Result: ${data.data.final_result}`);
            }
        }
    } else if (data.type === 'chat_error') {
        setExecuting(false);
        if (currentMode === 'chat') {
            appendChatMessage('system', `Error: ${data.data.message}`);
        } else {
            appendTerminalLine(`Error: ${data.data.message}`);
        }
    } else if (data.type === 'automation_save_result') {
        if (data.data.success) {
            appendChatMessage('system', `Automation saved: ${data.data.message}`);
            loadAutomations(); // Refresh automation list
        } else {
            appendChatMessage('system', `Failed to save automation: ${data.data.message}`);
        }
    } else if (data.type === 'automation_execute_result') {
        setExecuting(false);
        if (data.data.success) {
            appendChatMessage('system', `Automation completed: ${data.data.message}`);
        } else {
            appendChatMessage('system', `Automation failed: ${data.data.message}`);
        }
    } else if (data.type === 'pong') {
        // Heartbeat response - connection is alive
        console.log('Received pong from backend');
    }
}

// UI Helper functions
function appendChatMessage(role, content) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.textContent = content;
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function updateLastMessage(content) {
    const messages = chatMessages.querySelectorAll('.message');
    if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        const contentDiv = lastMessage.querySelector('.message-content');
        if (contentDiv && lastMessage.classList.contains('assistant')) {
            contentDiv.textContent = content;
        }
    }
}

function appendTerminalLine(line) {
    const lineDiv = document.createElement('div');
    lineDiv.className = 'terminal-line';
    lineDiv.textContent = line;
    terminalOutput.appendChild(lineDiv);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

function appendLog(log) {
    const logLine = document.createElement('div');
    logLine.textContent = log;
    logContent.appendChild(logLine);
    logContent.scrollTop = logContent.scrollHeight;
}

function setExecuting(executing) {
    isExecuting = executing;
    
    if (currentMode === 'chat') {
        sendBtn.style.display = executing ? 'none' : 'block';
        stopBtn.style.display = executing ? 'block' : 'none';
        chatInput.disabled = executing;
    } else {
        executeBtn.style.display = executing ? 'none' : 'block';
        stopAgentBtn.style.display = executing ? 'block' : 'none';
        agentInput.disabled = executing;
    }
}

function updateConnectionStatus(status) {
    connectionStatus.className = 'status-dot ' + status;
    
    const statusMessages = {
        'connected': 'Connected',
        'connecting': 'Connecting...',
        'error': 'Connection Error'
    };
    
    statusText.textContent = statusMessages[status] || 'Unknown';
}