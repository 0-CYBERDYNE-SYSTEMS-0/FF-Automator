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
let categories = [];
let tags = [];
let scheduledAutomations = [];
let customSystemMessage = '';

// DOM elements - with deferred initialization
let providerSelect = null;
let modelSelect = null;
let chatMessages = null;
let chatInput = null;
let sendBtn = null;
let stopBtn = null;
let terminalOutput = null;
let agentInput = null;
let executeBtn = null;
let stopAgentBtn = null;
let connectionStatus = null;
let statusText = null;
let logContent = null;
let logPanel = null;
let toggleLogsBtn = null;

// Wait for Wails runtime to be available
async function waitForWailsRuntime() {
    const maxWait = 15000; // 15 seconds max wait
    const checkInterval = 200; // Check every 200ms
    let waited = 0;
    
    console.log('Starting Wails runtime detection...');
    
    while (waited < maxWait) {
        // Check for runtime
        const hasRuntime = !!window.runtime;
        const hasGo = !!window.go;
        const hasApp = !!(window.go && window.go.ui && window.go.ui.App);
        
        console.log(`Runtime check (${waited}ms):`, {
            runtime: hasRuntime,
            go: hasGo,
            app: hasApp
        });
        
        if (hasRuntime && hasGo && hasApp) {
            console.log('✅ Wails runtime fully available');
            return;
        }
        
        await new Promise(resolve => setTimeout(resolve, checkInterval));
        waited += checkInterval;
    }
    
    // Final diagnostic
    console.error('❌ Wails runtime not fully available after 15 seconds');
    console.error('Final state:', {
        runtime: !!window.runtime,
        go: !!window.go,
        goUi: !!(window.go && window.go.ui),
        app: !!(window.go && window.go.ui && window.go.ui.App),
        availableMethods: window.go?.ui?.App ? Object.keys(window.go.ui.App) : []
    });
    
    throw new Error('Wails runtime not available after 15 seconds - check console for details');
}

// Initialize DOM elements after DOM is ready
function initializeDOMElements() {
    providerSelect = document.getElementById('provider');
    modelSelect = document.getElementById('model');
    chatMessages = document.getElementById('chat-messages');
    chatInput = document.getElementById('chat-input');
    sendBtn = document.getElementById('send-btn');
    stopBtn = document.getElementById('stop-btn');
    terminalOutput = document.getElementById('terminal-output');
    agentInput = document.getElementById('agent-input');
    executeBtn = document.getElementById('execute-btn');
    stopAgentBtn = document.getElementById('stop-agent-btn');
    connectionStatus = document.getElementById('connection-status');
    statusText = document.getElementById('status-text');
    logContent = document.getElementById('log-content');
    logPanel = document.getElementById('log-panel');
    toggleLogsBtn = document.getElementById('toggle-logs');
    
    console.log('DOM elements initialized:', {
        providerSelect: !!providerSelect,
        modelSelect: !!modelSelect,
        chatMessages: !!chatMessages,
        chatInput: !!chatInput,
        sendBtn: !!sendBtn,
        stopBtn: !!stopBtn,
        terminalOutput: !!terminalOutput,
        agentInput: !!agentInput,
        executeBtn: !!executeBtn,
        stopAgentBtn: !!stopAgentBtn,
        connectionStatus: !!connectionStatus,
        statusText: !!statusText,
        logContent: !!logContent,
        logPanel: !!logPanel,
        toggleLogsBtn: !!toggleLogsBtn
    });
}

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    // Wait for Wails runtime to be available
    await waitForWailsRuntime();
    
    // Initialize DOM elements first
    initializeDOMElements();
    
    // Setup UI first - critical for responsiveness
    setupEventListeners();
    setupWailsEvents();
    
    // Show loading state
    updateConnectionStatus('connecting');
    
    try {
        // Load critical data first (providers needed for UI state)
        updateConnectionStatus('loading-providers');
        await loadProviders();
        
        // Load remaining data in parallel for better performance
        updateConnectionStatus('loading-data');
        const results = await Promise.allSettled([
            loadSessions(),
            loadAutomations(), 
            loadAutomationTemplates(),
            loadCategories(),
            loadTags(),
            loadScheduledAutomations()
        ]);
        
        // Log any failures
        results.forEach((result, index) => {
            const functionNames = ['loadSessions', 'loadAutomations', 'loadAutomationTemplates', 'loadCategories', 'loadTags', 'loadScheduledAutomations'];
            if (result.status === 'rejected') {
                console.warn(`${functionNames[index]} failed:`, result.reason);
            }
        });
        
        updateConnectionStatus('connected');
        console.log('Application initialization complete');
    } catch (error) {
        console.error('Initialization failed:', error);
        updateConnectionStatus('error');
    }
});

// Setup event listeners
function setupEventListeners() {
    // Mode switching
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });
    
    // Provider/model selection - with null checks
    if (providerSelect) {
        providerSelect.addEventListener('change', onProviderChange);
        console.log('Provider select event listener attached');
    } else {
        console.error('Provider select element not found');
    }
    
    if (modelSelect) {
        modelSelect.addEventListener('change', onModelChange);
        console.log('Model select event listener attached');
    } else {
        console.error('Model select element not found');
    }
    
    // Provider testing
    const testProviderBtn = document.getElementById('test-provider');
    if (testProviderBtn) {
        testProviderBtn.addEventListener('click', testSelectedProvider);
        console.log('Test provider button event listener attached');
    } else {
        console.error('Test provider button not found');
    }
    
    // Chat controls
    sendBtn.addEventListener('click', sendChatMessage);
    stopBtn.addEventListener('click', stopExecution);
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendChatMessage();
        }
    });
    
    // Advanced chat controls
    const interruptBtn = document.getElementById('interrupt-chat');
    const redirectBtn = document.getElementById('redirect-chat');
    const addTaskBtn = document.getElementById('add-task');
    const refinePromptBtn = document.getElementById('refine-prompt');
    const customSystemBtn = document.getElementById('custom-system');
    
    interruptBtn.addEventListener('click', interruptChat);
    redirectBtn.addEventListener('click', redirectChat);
    addTaskBtn.addEventListener('click', addTaskToQueue);
    refinePromptBtn.addEventListener('click', refinePrompt);
    customSystemBtn.addEventListener('click', openSystemMessageModal);
    
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
    const duplicateAutomationBtn = document.getElementById('duplicate-automation');
    const viewHistoryBtn = document.getElementById('view-history');
    const automationSelect = document.getElementById('automation-list');
    const automationSearch = document.getElementById('automation-search');
    const categoryFilter = document.getElementById('category-filter');
    
    saveAutomationBtn.addEventListener('click', saveCurrentAutomation);
    runAutomationBtn.addEventListener('click', runSelectedAutomation);
    duplicateAutomationBtn.addEventListener('click', duplicateSelectedAutomation);
    viewHistoryBtn.addEventListener('click', viewAutomationHistory);
    automationSelect.addEventListener('change', onAutomationSelectChange);
    automationSearch.addEventListener('input', searchAutomations);
    categoryFilter.addEventListener('change', filterAutomations);
    
    // Template management
    const refreshScheduledBtn = document.getElementById('refresh-scheduled');
    const addScheduleBtn = document.getElementById('add-schedule');
    
    refreshScheduledBtn.addEventListener('click', loadScheduledAutomations);
    addScheduleBtn.addEventListener('click', openScheduleModal);
    
    // Modal event listeners
    setupModalEventListeners();
}

// Setup modal event listeners
function setupModalEventListeners() {
    // System message modal
    const systemModal = document.getElementById('system-message-modal');
    const closeSystemModal = document.getElementById('close-system-modal');
    const saveSystemMessage = document.getElementById('save-system-message');
    const cancelSystemMessage = document.getElementById('cancel-system-message');
    
    closeSystemModal.addEventListener('click', () => systemModal.style.display = 'none');
    cancelSystemMessage.addEventListener('click', () => systemModal.style.display = 'none');
    saveSystemMessage.addEventListener('click', saveCustomSystemMessage);
    
    // Template modal
    const templateModal = document.getElementById('template-modal');
    const closeTemplateModal = document.getElementById('close-template-modal');
    const createFromTemplate = document.getElementById('create-from-template');
    const cancelTemplate = document.getElementById('cancel-template');
    
    closeTemplateModal.addEventListener('click', () => templateModal.style.display = 'none');
    cancelTemplate.addEventListener('click', () => templateModal.style.display = 'none');
    createFromTemplate.addEventListener('click', createAutomationFromTemplate);
    
    // Schedule modal
    const scheduleModal = document.getElementById('schedule-modal');
    const closeScheduleModal = document.getElementById('close-schedule-modal');
    const saveSchedule = document.getElementById('save-schedule');
    const cancelSchedule = document.getElementById('cancel-schedule');
    
    closeScheduleModal.addEventListener('click', () => scheduleModal.style.display = 'none');
    cancelSchedule.addEventListener('click', () => scheduleModal.style.display = 'none');
    saveSchedule.addEventListener('click', saveAutomationSchedule);
    
    // History modal
    const historyModal = document.getElementById('history-modal');
    const closeHistoryModal = document.getElementById('close-history-modal');
    const closeHistory = document.getElementById('close-history');
    
    closeHistoryModal.addEventListener('click', () => historyModal.style.display = 'none');
    closeHistory.addEventListener('click', () => historyModal.style.display = 'none');
    
    // Refine modal
    const refineModal = document.getElementById('refine-modal');
    const closeRefineModal = document.getElementById('close-refine-modal');
    const useRefinedPrompt = document.getElementById('use-refined-prompt');
    const cancelRefine = document.getElementById('cancel-refine');
    
    closeRefineModal.addEventListener('click', () => refineModal.style.display = 'none');
    cancelRefine.addEventListener('click', () => refineModal.style.display = 'none');
    useRefinedPrompt.addEventListener('click', useRefinedPromptInChat);
    
    // Close modals when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

// Setup Wails event listeners
function setupWailsEvents() {
    // Check if runtime is available
    if (!window.runtime || !window.runtime.EventsOn) {
        console.warn('Wails runtime not available, skipping event setup');
        return;
    }
    
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
    
    console.log('Wails events setup complete');
}

// Load providers
async function loadProviders() {
    try {
        console.log('Loading providers...');
        
        if (!providerSelect) {
            throw new Error('Provider select element not available');
        }
        
        // Validate Wails runtime is available
        if (!window.go || !window.go.ui || !window.go.ui.App || !window.go.ui.App.GetProviders) {
            throw new Error('Wails runtime not available - cannot call GetProviders');
        }
        
        console.log('Calling GetProviders...');
        providers = await window.go.ui.App.GetProviders();
        console.log('Providers loaded:', providers);
        
        if (!Array.isArray(providers)) {
            throw new Error('Invalid providers data received');
        }
        
        // Clear and populate provider dropdown
        providerSelect.innerHTML = '<option value="">Select a provider</option>';
        
        let availableCount = 0;
        providers.forEach(provider => {
            if (provider && provider.available && provider.name) {
                const option = document.createElement('option');
                option.value = provider.name;
                option.textContent = provider.name;
                providerSelect.appendChild(option);
                availableCount++;
                console.log(`Added provider: ${provider.name} (${provider.models?.length || 0} models)`);
            } else {
                console.warn('Skipping invalid or unavailable provider:', provider);
            }
        });
        
        console.log(`Provider UI updated: ${availableCount} available providers`);
        updateUIState();
        
    } catch (error) {
        console.error('Failed to load providers:', error);
        updateConnectionStatus('error');
        
        // Provide fallback UI state
        if (providerSelect) {
            providerSelect.innerHTML = '<option value="">Error loading providers</option>';
        }
        
        updateUIState();
        throw error; // Re-throw to be caught by initialization handler
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

// Load automations
async function loadAutomations() {
    try {
        automations = await window.go.ui.App.GetAutomations();
        populateAutomationList();
    } catch (error) {
        console.error('Failed to load automations:', error);
    }
}

// Load automation templates
async function loadAutomationTemplates() {
    try {
        automationTemplates = await window.go.ui.App.GetAutomationTemplates();
        renderTemplateGrid();
    } catch (error) {
        console.error('Failed to load automation templates:', error);
    }
}

// Load categories
async function loadCategories() {
    try {
        categories = await window.go.ui.App.GetAutomationCategories();
        populateCategoryFilter();
    } catch (error) {
        console.error('Failed to load categories:', error);
    }
}

// Load tags
async function loadTags() {
    try {
        tags = await window.go.ui.App.GetAutomationTags();
    } catch (error) {
        console.error('Failed to load tags:', error);
    }
}

// Load scheduled automations
async function loadScheduledAutomations() {
    try {
        scheduledAutomations = await window.go.ui.App.GetScheduledAutomations();
        renderScheduledList();
    } catch (error) {
        console.error('Failed to load scheduled automations:', error);
    }
}

// Test selected provider
async function testSelectedProvider() {
    if (!selectedProvider) {
        alert('Please select a provider first');
        return;
    }
    
    try {
        const result = await window.go.ui.App.TestProvider(selectedProvider);
        const message = result.status === 'success' ? 
            `✅ ${selectedProvider} connection successful (${result.latency}ms)` :
            `❌ ${selectedProvider} connection failed: ${result.message}`;
        
        appendChatMessage('system', message);
    } catch (error) {
        appendChatMessage('system', `❌ Provider test failed: ${error.message}`);
    }
}

// Provider change handler
function onProviderChange() {
    console.log('Provider change event triggered');
    
    if (!providerSelect) {
        console.error('Provider select element not available');
        return;
    }
    
    const providerName = providerSelect.value;
    console.log('Selected provider:', providerName);
    
    selectedProvider = providerName;
    selectedModel = null; // Reset model selection
    
    if (!modelSelect) {
        console.error('Model select element not available');
        return;
    }
    
    // Clear model dropdown
    modelSelect.innerHTML = '<option value="">Select a model</option>';
    
    if (providerName) {
        const provider = providers.find(p => p.name === providerName);
        if (provider && provider.models) {
            console.log(`Loading ${provider.models.length} models for ${providerName}`);
            provider.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                modelSelect.appendChild(option);
            });
        } else {
            console.warn(`No provider found or no models available for: ${providerName}`);
        }
    }
    
    updateUIState();
}

// Model change handler
function onModelChange() {
    console.log('Model change event triggered');
    
    if (!modelSelect) {
        console.error('Model select element not available');
        return;
    }
    
    selectedModel = modelSelect.value;
    console.log('Selected model:', selectedModel);
    
    updateUIState();
}

// Update UI state based on selection
function updateUIState() {
    const hasSelection = selectedProvider && selectedModel;
    
    console.log('UI State Update:', {
        selectedProvider,
        selectedModel,
        hasSelection
    });
    
    // Get button elements dynamically (in case of timing issues)
    const sendButton = document.getElementById('send-btn');
    const executeButton = document.getElementById('execute-btn');
    
    if (sendButton) {
        sendButton.disabled = !hasSelection;
        sendButton.textContent = hasSelection ? 'Send' : 'Select Provider & Model';
    }
    
    if (executeButton) {
        executeButton.disabled = !hasSelection;
        executeButton.textContent = hasSelection ? 'Execute' : 'Select Provider & Model';
    }
    
    console.log('UI buttons updated:', {
        sendDisabled: sendButton?.disabled,
        executeDisabled: executeButton?.disabled
    });
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
    document.getElementById('templates-view').classList.toggle('active', mode === 'templates');
    document.getElementById('scheduler-view').classList.toggle('active', mode === 'scheduler');
    
    // Show/hide chat controls
    const chatControls = document.querySelector('.chat-controls');
    if (chatControls) {
        chatControls.style.display = mode === 'chat' && isExecuting ? 'block' : 'none';
    }
}

// Advanced chat functions
async function interruptChat() {
    try {
        await window.go.ui.App.InterruptChat();
        appendChatMessage('system', 'Chat interrupted');
    } catch (error) {
        appendChatMessage('system', `Failed to interrupt chat: ${error.message}`);
    }
}

async function redirectChat() {
    const newTask = prompt('Enter new task:');
    if (!newTask) return;
    
    try {
        await window.go.ui.App.RedirectChat(newTask);
        appendChatMessage('system', `Redirected to: ${newTask}`);
    } catch (error) {
        appendChatMessage('system', `Failed to redirect chat: ${error.message}`);
    }
}

async function addTaskToQueue() {
    const task = prompt('Enter task to add to queue:');
    if (!task) return;
    
    try {
        await window.go.ui.App.AddTask(task);
        appendChatMessage('system', `Added to queue: ${task}`);
    } catch (error) {
        appendChatMessage('system', `Failed to add task: ${error.message}`);
    }
}

function openSystemMessageModal() {
    const modal = document.getElementById('system-message-modal');
    const input = document.getElementById('system-message-input');
    input.value = customSystemMessage;
    modal.style.display = 'block';
}

function saveCustomSystemMessage() {
    const input = document.getElementById('system-message-input');
    customSystemMessage = input.value;
    document.getElementById('system-message-modal').style.display = 'none';
    appendChatMessage('system', 'Custom system message saved');
}

async function refinePrompt() {
    const prompt = chatInput.value.trim();
    if (!prompt) {
        alert('Please enter a prompt to refine');
        return;
    }
    
    if (!selectedProvider || !selectedModel) {
        alert('Please select provider and model first');
        return;
    }
    
    try {
        const refinedPrompt = await window.go.ui.App.RefinePrompt(prompt, selectedProvider, selectedModel);
        
        document.getElementById('original-prompt').value = prompt;
        document.getElementById('refined-prompt').value = refinedPrompt;
        document.getElementById('refine-modal').style.display = 'block';
    } catch (error) {
        appendChatMessage('system', `Failed to refine prompt: ${error.message}`);
    }
}

function useRefinedPromptInChat() {
    const refinedPrompt = document.getElementById('refined-prompt').value;
    chatInput.value = refinedPrompt;
    document.getElementById('refine-modal').style.display = 'none';
}

// Send chat message
async function sendChatMessage() {
    const message = chatInput.value.trim();
    
    if (!message) {
        appendChatMessage('system', 'Please enter a message');
        return;
    }
    
    if (!selectedProvider || !selectedModel) {
        appendChatMessage('system', 'Please select provider and model first');
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
            custom_system_message: customSystemMessage
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
    
    if (!selectedProvider || !selectedModel) {
        appendTerminalLine('Please select provider and model first');
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
            custom_system_message: customSystemMessage
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

// Template functions
function renderTemplateGrid() {
    const grid = document.getElementById('template-grid');
    grid.innerHTML = '';
    
    automationTemplates.forEach(template => {
        const card = document.createElement('div');
        card.className = 'template-card';
        card.innerHTML = `
            <h3>${template.name}</h3>
            <p>${template.description}</p>
            <div class="template-meta">
                <span class="category">${template.category}</span>
                <div class="tags">
                    ${template.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            </div>
            <button class="btn-primary" onclick="openTemplateModal('${template.name}')">Use Template</button>
        `;
        grid.appendChild(card);
    });
}

function openTemplateModal(templateName) {
    const template = automationTemplates.find(t => t.name === templateName);
    if (!template) return;
    
    const form = document.getElementById('template-form');
    form.innerHTML = `
        <h4>${template.name}</h4>
        <p>${template.description}</p>
        <div class="form-group">
            <label for="template-automation-name">Automation Name:</label>
            <input type="text" id="template-automation-name" value="${template.name}" required>
        </div>
        <div class="form-group">
            <label for="template-automation-description">Description:</label>
            <textarea id="template-automation-description" rows="3">${template.description}</textarea>
        </div>
    `;
    
    // Add parameter fields if template has parameters
    if (template.parameters) {
        Object.entries(template.parameters).forEach(([key, value]) => {
            const paramDiv = document.createElement('div');
            paramDiv.className = 'form-group';
            paramDiv.innerHTML = `
                <label for="param-${key}">${key}:</label>
                <input type="text" id="param-${key}" value="${value}" placeholder="Enter ${key}">
            `;
            form.appendChild(paramDiv);
        });
    }
    
    document.getElementById('template-modal').style.display = 'block';
    document.getElementById('template-modal').dataset.templateName = templateName;
}

async function createAutomationFromTemplate() {
    const templateName = document.getElementById('template-modal').dataset.templateName;
    const automationName = document.getElementById('template-automation-name').value;
    const description = document.getElementById('template-automation-description').value;
    
    if (!automationName) {
        alert('Please enter an automation name');
        return;
    }
    
    // Collect parameters
    const parameters = { name: automationName, description: description };
    const template = automationTemplates.find(t => t.name === templateName);
    
    if (template && template.parameters) {
        Object.keys(template.parameters).forEach(key => {
            const input = document.getElementById(`param-${key}`);
            if (input) {
                parameters[key] = input.value;
            }
        });
    }
    
    try {
        await window.go.ui.App.CreateAutomationFromTemplate(templateName, parameters);
        document.getElementById('template-modal').style.display = 'none';
        await loadAutomations();
        appendChatMessage('system', `Automation "${automationName}" created from template`);
    } catch (error) {
        alert(`Failed to create automation: ${error.message}`);
    }
}

// Scheduler functions
function renderScheduledList() {
    const list = document.getElementById('scheduled-list');
    list.innerHTML = '';
    
    if (scheduledAutomations.length === 0) {
        list.innerHTML = '<p>No scheduled automations</p>';
        return;
    }
    
    scheduledAutomations.forEach(scheduled => {
        const card = document.createElement('div');
        card.className = 'scheduled-card';
        card.innerHTML = `
            <h4>${scheduled.name}</h4>
            <p>Next: ${scheduled.next_execution || 'Not scheduled'}</p>
            <p>Last: ${scheduled.last_execution || 'Never'}</p>
            <div class="scheduled-actions">
                <button class="btn-small" onclick="editSchedule('${scheduled.automation_id}')">Edit</button>
                <button class="btn-small btn-danger" onclick="deleteSchedule('${scheduled.automation_id}')">Delete</button>
            </div>
        `;
        list.appendChild(card);
    });
}

function openScheduleModal() {
    const modal = document.getElementById('schedule-modal');
    const select = document.getElementById('schedule-automation');
    
    // Populate automation dropdown
    select.innerHTML = '<option value="">Select automation...</option>';
    automations.forEach(automation => {
        const option = document.createElement('option');
        option.value = automation.id;
        option.textContent = automation.name;
        select.appendChild(option);
    });
    
    modal.style.display = 'block';
}

async function saveAutomationSchedule() {
    const automationId = document.getElementById('schedule-automation').value;
    const cronExpression = document.getElementById('cron-expression').value;
    const enabled = document.getElementById('schedule-enabled').checked;
    
    if (!automationId || !cronExpression) {
        alert('Please select automation and enter cron expression');
        return;
    }
    
    try {
        await window.go.ui.App.ScheduleAutomation(automationId, cronExpression, enabled);
        document.getElementById('schedule-modal').style.display = 'none';
        await loadScheduledAutomations();
        appendChatMessage('system', 'Automation scheduled successfully');
    } catch (error) {
        alert(`Failed to schedule automation: ${error.message}`);
    }
}

// Automation functions
function populateAutomationList() {
    const automationSelect = document.getElementById('automation-list');
    automationSelect.innerHTML = '<option value="">Select an automation</option>';
    
    automations.forEach(automation => {
        const option = document.createElement('option');
        option.value = automation.id;
        option.textContent = `${automation.name} - ${automation.description}`;
        automationSelect.appendChild(option);
    });
}

function populateCategoryFilter() {
    const filter = document.getElementById('category-filter');
    filter.innerHTML = '<option value="">All Categories</option>';
    
    categories.forEach(category => {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        filter.appendChild(option);
    });
}

async function searchAutomations() {
    const query = document.getElementById('automation-search').value;
    const category = document.getElementById('category-filter').value;
    
    try {
        const result = await window.go.ui.App.SearchAutomations(query, category, []);
        automations = result.automations;
        populateAutomationList();
    } catch (error) {
        console.error('Failed to search automations:', error);
    }
}

async function filterAutomations() {
    await searchAutomations();
}

async function duplicateSelectedAutomation() {
    const automationId = document.getElementById('automation-list').value;
    if (!automationId) {
        alert('Please select an automation to duplicate');
        return;
    }
    
    const newName = prompt('Enter new automation name:');
    if (!newName) return;
    
    try {
        await window.go.ui.App.DuplicateAutomation(automationId, newName);
        await loadAutomations();
        appendChatMessage('system', `Automation duplicated as "${newName}"`);
    } catch (error) {
        alert(`Failed to duplicate automation: ${error.message}`);
    }
}

async function viewAutomationHistory() {
    const automationId = document.getElementById('automation-list').value;
    if (!automationId) {
        alert('Please select an automation to view history');
        return;
    }
    
    try {
        const history = await window.go.ui.App.GetAutomationHistory(automationId);
        const content = document.getElementById('history-content');
        
        if (history.length === 0) {
            content.innerHTML = '<p>No execution history</p>';
        } else {
            content.innerHTML = history.map(entry => `
                <div class="history-entry">
                    <div class="history-date">${new Date(entry.executed_at).toLocaleString()}</div>
                    <div class="history-status status-${entry.status}">${entry.status}</div>
                    <div class="history-duration">${entry.duration}ms</div>
                    ${entry.error_message ? `<div class="history-error">${entry.error_message}</div>` : ''}
                </div>
            `).join('');
        }
        
        document.getElementById('history-modal').style.display = 'block';
    } catch (error) {
        alert(`Failed to load history: ${error.message}`);
    }
}

// Session functions
async function saveCurrentSession() {
    const sessionName = prompt('Enter session name:');
    if (!sessionName) return;
    
    try {
        const session = {
            name: sessionName,
            timestamp: new Date().toISOString(),
            message_count: conversationHistory.length,
            success_count: 0,
            failure_count: 0,
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

async function loadSelectedSession() {
    const sessionSelect = document.getElementById('session-list');
    const sessionName = sessionSelect.value;
    
    if (!sessionName) {
        alert('Please select a session to load');
        return;
    }
    
    try {
        const session = await window.go.ui.App.LoadSession(sessionName);
        
        chatMessages.innerHTML = '';
        conversationHistory = [];
        
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

function onSessionSelectChange() {
    const sessionSelect = document.getElementById('session-list');
    const loadSessionBtn = document.getElementById('load-session');
    
    loadSessionBtn.disabled = !sessionSelect.value;
}

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
        appendChatMessage('system', 'Running automation...');
    } catch (error) {
        console.error('Failed to run automation:', error);
        appendChatMessage('system', `Failed to run automation: ${error.message}`);
        setExecuting(false);
    }
}

function onAutomationSelectChange() {
    const automationSelect = document.getElementById('automation-list');
    const runAutomationBtn = document.getElementById('run-automation');
    const duplicateBtn = document.getElementById('duplicate-automation');
    const historyBtn = document.getElementById('view-history');
    
    const hasSelection = !!automationSelect.value;
    runAutomationBtn.disabled = !hasSelection;
    duplicateBtn.disabled = !hasSelection;
    historyBtn.disabled = !hasSelection;
}

// Handle backend messages
function handleBackendMessage(data) {
    if (data.type === 'chat_response') {
        if (data.data.content) {
            if (data.data.streaming) {
                updateLastMessage(data.data.content);
            } else {
                appendChatMessage('assistant', data.data.content);
                conversationHistory.push({ role: 'assistant', content: data.data.content });
            }
        }
    } else if (data.type === 'chat_stream_update') {
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
            loadAutomations();
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
        
        // Show/hide advanced controls
        const chatControls = document.querySelector('.chat-controls');
        if (chatControls) {
            chatControls.style.display = executing ? 'block' : 'none';
        }
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
        'connecting': 'Loading...',
        'error': 'Connection Error',
        'loading-providers': 'Loading providers...',
        'loading-data': 'Loading data...'
    };
    
    statusText.textContent = statusMessages[status] || 'Unknown';
}