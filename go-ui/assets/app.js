// App state
let currentMode = 'chat';
let isExecuting = false;
let providers = [];
let selectedProvider = null;
let selectedModel = null;

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
    } catch (error) {
        console.error('Failed to load providers:', error);
        updateConnectionStatus('error');
    }
}

// Provider change handler
function onProviderChange() {
    const providerName = providerSelect.value;
    selectedProvider = providerName;
    
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
}

// Model change handler
function onModelChange() {
    selectedModel = modelSelect.value;
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
    if (!message || !selectedProvider || !selectedModel) return;
    
    // Add user message to chat
    appendChatMessage('user', message);
    chatInput.value = '';
    
    // Update UI state
    setExecuting(true);
    
    try {
        await window.go.ui.App.SendTask({
            type: 'chat',
            message: message,
            provider: selectedProvider,
            model: selectedModel
        });
    } catch (error) {
        appendChatMessage('system', `Error: ${error.message}`);
        setExecuting(false);
    }
}

// Execute agent task
async function executeAgent() {
    const task = agentInput.value.trim();
    if (!task || !selectedProvider || !selectedModel) return;
    
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
            model: selectedModel
        });
    } catch (error) {
        appendTerminalLine(`Error: ${error.message}`);
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
    if (data.type === 'chat_response') {
        appendChatMessage('assistant', data.content);
    } else if (data.type === 'chat_progress') {
        // Show progress in chat
        updateLastMessage(data.content);
    } else if (data.type === 'agent_output') {
        appendTerminalLine(data.content);
    } else if (data.type === 'task_complete') {
        setExecuting(false);
    } else if (data.type === 'error') {
        if (currentMode === 'chat') {
            appendChatMessage('system', `Error: ${data.content}`);
        } else {
            appendTerminalLine(`Error: ${data.content}`);
        }
        setExecuting(false);
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