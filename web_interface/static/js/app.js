/**
 * macOS Automation - Elegant Interface JavaScript Application
 * Modern vanilla JavaScript implementation with component architecture
 */

class MacOSAutomationApp {
	constructor() {
		this.apiBase = 'http://localhost:8080';
		this.wsUrl = 'ws://localhost:8080';
		this.socket = null;
		this.currentTab = 'chat';
		this.conversationHistory = [];
		this.providers = {};
		this.sessions = [];
		this.automationTemplates = {};
		this.currentAutomationCategory = 'Quick Tasks';
		this.isAgentRunning = false;
		this.isChatRunning = false;
		
		this.init();
	}

	async init() {
		try {
			await this.showLoadingScreen();
			await this.initializeApp();
			await this.setupEventListeners();
			await this.connectWebSocket();
			await this.loadProviders();
			await this.loadSessions();
			await this.loadAutomationTemplates();
			await this.hideLoadingScreen();
		} catch (error) {
			console.error('Failed to initialize app:', error);
			this.showToast('Failed to initialize application', 'error');
		}
	}

	async showLoadingScreen() {
		return new Promise(resolve => {
			setTimeout(resolve, 1500); // Simulated loading time
		});
	}

	async hideLoadingScreen() {
		const loadingScreen = document.getElementById('loading-screen');
		const mainApp = document.getElementById('main-app');
		
		loadingScreen.style.opacity = '0';
		setTimeout(() => {
			loadingScreen.classList.add('hidden');
			mainApp.classList.remove('hidden');
		}, 500);
	}

	async initializeApp() {
		// Set up initial UI state
		this.updateConnectionStatus(false);
		this.switchTab('chat');
	}

	setupEventListeners() {
		// Navigation
		document.querySelectorAll('.nav-btn').forEach(btn => {
			btn.addEventListener('click', (e) => {
				const tab = e.currentTarget.dataset.tab;
				this.switchTab(tab);
			});
		});

		// Chat functionality
		this.setupChatListeners();
		
		// Agent functionality
		this.setupAgentListeners();
		
		// Sessions functionality
		this.setupSessionsListeners();
		
		// Providers functionality
		this.setupProvidersListeners();

		// Automation templates
		this.setupAutomationTemplates();

		// Help icons
		this.setupHelpIcons();
	}

	setupChatListeners() {
		const chatInput = document.getElementById('chat-input');
		const sendBtn = document.getElementById('send-chat-btn');
		const stopBtn = document.getElementById('stop-chat-btn');
		const clearBtn = document.getElementById('clear-chat-btn');
		const saveBtn = document.getElementById('save-chat-btn');

		// Send message on Enter
		chatInput.addEventListener('keypress', (e) => {
			if (e.key === 'Enter' && !e.shiftKey) {
				e.preventDefault();
				this.sendChatMessage();
			}
		});

		// Send button
		sendBtn.addEventListener('click', () => this.sendChatMessage());

		// Stop button
		stopBtn.addEventListener('click', () => this.stopChat());

		// Clear chat
		clearBtn.addEventListener('click', () => this.clearChat());

		// Save chat
		saveBtn.addEventListener('click', () => this.showSaveChatModal());

		// Provider/model changes
		document.getElementById('chat-provider').addEventListener('change', (e) => {
			this.updateChatModels(e.target.value);
		});
	}

	setupAgentListeners() {
		const runBtn = document.getElementById('run-agent-btn');
		const stopBtn = document.getElementById('stop-agent-btn');
		const refineBtn = document.getElementById('refine-task-btn');
		const clearTerminalBtn = document.getElementById('clear-terminal-btn');

		runBtn.addEventListener('click', () => this.runAgent());
		stopBtn.addEventListener('click', () => this.stopAgent());
		refineBtn.addEventListener('click', () => this.refineTask());
		clearTerminalBtn.addEventListener('click', () => this.clearTerminal());

		// Provider changes
		document.getElementById('agent-provider').addEventListener('change', (e) => {
			this.updateAgentModels(e.target.value);
		});
	}

	setupSessionsListeners() {
		const refreshBtn = document.getElementById('refresh-sessions-btn');
		const saveSessionBtn = document.getElementById('save-session-btn');

		refreshBtn.addEventListener('click', () => this.loadSessions());
		saveSessionBtn.addEventListener('click', () => this.saveCurrentSession());
	}

	setupProvidersListeners() {
		const refreshBtn = document.getElementById('refresh-providers-btn');
		refreshBtn.addEventListener('click', () => this.loadProviders());
	}

	setupAutomationTemplates() {
		// Category tab switching
		document.querySelectorAll('.category-tab').forEach(tab => {
			tab.addEventListener('click', (e) => {
				const category = e.currentTarget.dataset.category;
				this.switchAutomationCategory(category);
			});
		});
	}

	setupHelpIcons() {
		document.querySelectorAll('.help-icon').forEach(icon => {
			icon.addEventListener('click', (e) => {
				const title = e.target.getAttribute('title');
				if (title) {
					this.showToast(title, 'info');
				}
			});
		});
	}

	// WebSocket Connection
	async connectWebSocket() {
		try {
			this.socket = new WebSocket(`${this.wsUrl}/ws/${this.generateClientId()}`);
			
			this.socket.onopen = () => {
				console.log('WebSocket connected');
				this.updateConnectionStatus(true);
				this.startHeartbeat();
			};

			this.socket.onmessage = (event) => {
				const message = JSON.parse(event.data);
				this.handleWebSocketMessage(message);
			};

			this.socket.onclose = () => {
				console.log('WebSocket disconnected');
				this.updateConnectionStatus(false);
				this.stopHeartbeat();
				// Attempt to reconnect after 3 seconds
				setTimeout(() => this.connectWebSocket(), 3000);
			};

			this.socket.onerror = (error) => {
				console.error('WebSocket error:', error);
				this.updateConnectionStatus(false);
			};
		} catch (error) {
			console.error('Failed to connect WebSocket:', error);
			this.updateConnectionStatus(false);
		}
	}

	generateClientId() {
		return 'client_' + Math.random().toString(36).substr(2, 9);
	}

	startHeartbeat() {
		this.heartbeatInterval = setInterval(() => {
			if (this.socket && this.socket.readyState === WebSocket.OPEN) {
				this.socket.send(JSON.stringify({ type: 'ping' }));
			}
		}, 30000);
	}

	stopHeartbeat() {
		if (this.heartbeatInterval) {
			clearInterval(this.heartbeatInterval);
		}
	}

	handleWebSocketMessage(message) {
		switch (message.type) {
			case 'pong':
				// Heartbeat response
				break;
			case 'stream_update':
				this.handleAgentStreamUpdate(message.data);
				break;
			case 'chat_response':
				this.handleChatResponse(message.data);
				break;
			case 'chat_complete':
				this.handleChatComplete(message.data);
				break;
			case 'chat_error':
				this.handleChatError(message.data);
				break;
			default:
				console.log('Unknown message type:', message);
		}
	}

	updateConnectionStatus(connected) {
		const statusEl = document.getElementById('connection-status');
		const iconEl = statusEl.querySelector('i');
		const textEl = statusEl.querySelector('span');

		if (connected) {
			statusEl.classList.remove('disconnected');
			textEl.textContent = 'Connected';
		} else {
			statusEl.classList.add('disconnected');
			textEl.textContent = 'Disconnected';
		}
	}

	// Tab Management
	switchTab(tabName) {
		// Update navigation
		document.querySelectorAll('.nav-btn').forEach(btn => {
			btn.classList.remove('active');
		});
		document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

		// Update content
		document.querySelectorAll('.tab-content').forEach(content => {
			content.classList.remove('active');
		});
		document.getElementById(`${tabName}-tab`).classList.add('active');

		this.currentTab = tabName;

		// Load tab-specific data
		if (tabName === 'sessions') {
			this.loadSessions();
		} else if (tabName === 'providers') {
			this.loadProviders();
		}
	}

	// Chat Functionality
	async sendChatMessage() {
		if (this.isChatRunning) return;
		
		const input = document.getElementById('chat-input');
		const message = input.value.trim();
		
		if (!message) return;

		const provider = document.getElementById('chat-provider').value;
		const model = document.getElementById('chat-model').value;
		const apiKey = document.getElementById('chat-api-key').value;

		// Add user message to chat
		this.addChatMessage(message, 'user');
		input.value = '';

		// Update UI state
		this.isChatRunning = true;
		this.updateChatUI(true);

		// Show typing indicator
		this.currentChatTypingId = this.addTypingIndicator();

		// Send via WebSocket
		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({
				type: 'chat_message',
				data: {
					message,
					llm_provider: provider,
					llm_model: model,
					api_key: apiKey
				}
			}));

			// Update conversation history with user message
			this.conversationHistory.push({
				type: 'user',
				content: message,
				timestamp: new Date().toISOString(),
				success: true
			});
		} else {
			this.showToast('WebSocket not connected', 'error');
			this.removeTypingIndicator(this.currentChatTypingId);
			this.isChatRunning = false;
			this.updateChatUI(false);
		}
	}

	addChatMessage(content, sender, success = true) {
		const messagesContainer = document.getElementById('chat-messages');
		
		// Remove welcome message if it exists
		const welcomeMessage = messagesContainer.querySelector('.welcome-message');
		if (welcomeMessage) {
			welcomeMessage.remove();
		}

		const messageEl = document.createElement('div');
		messageEl.className = `message ${sender}`;
		
		const timestamp = new Date().toLocaleTimeString();
		const icon = sender === 'user' ? 'fa-user' : 'fa-robot';
		const statusClass = success === false ? 'error' : '';

		messageEl.innerHTML = `
			<div class="message-avatar">
				<i class="fas ${icon}"></i>
			</div>
			<div class="message-content">
				<div class="message-bubble ${statusClass}">
					${this.formatMessageContent(content)}
				</div>
				<div class="message-time">${timestamp}</div>
			</div>
		`;

		messagesContainer.appendChild(messageEl);
		messagesContainer.scrollTop = messagesContainer.scrollHeight;
	}

	addTypingIndicator() {
		const messagesContainer = document.getElementById('chat-messages');
		const typingId = 'typing_' + Date.now();
		
		const typingEl = document.createElement('div');
		typingEl.id = typingId;
		typingEl.className = 'message assistant';
		typingEl.innerHTML = `
			<div class="message-avatar">
				<i class="fas fa-robot"></i>
			</div>
			<div class="message-content">
				<div class="message-bubble">
					<i class="fas fa-ellipsis-h fa-pulse"></i> Thinking...
				</div>
			</div>
		`;

		messagesContainer.appendChild(typingEl);
		messagesContainer.scrollTop = messagesContainer.scrollHeight;
		
		return typingId;
	}

	removeTypingIndicator(typingId) {
		const typingEl = document.getElementById(typingId);
		if (typingEl) {
			typingEl.remove();
		}
	}

	formatMessageContent(content) {
		// Basic markdown-like formatting
		return content
			.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
			.replace(/\*(.*?)\*/g, '<em>$1</em>')
			.replace(/`(.*?)`/g, '<code>$1</code>')
			.replace(/\n/g, '<br>');
	}

	clearChat() {
		const messagesContainer = document.getElementById('chat-messages');
		messagesContainer.innerHTML = `
			<div class="welcome-message">
				<div class="welcome-content">
					<i class="fas fa-robot"></i>
					<h3>Welcome to macOS Automation!</h3>
					<p>I'm your AI assistant for automating macOS tasks. You can:</p>
					<ul>
						<li>Ask me to control applications and perform tasks</li>
						<li>Use natural language to describe what you want to do</li>
						<li>Try quick actions from the sidebar</li>
						<li>Save and load conversation sessions</li>
					</ul>
					<p>How can I help you today?</p>
				</div>
			</div>
		`;
		this.conversationHistory = [];
		this.showToast('Chat cleared', 'info');
	}

	stopChat() {
		if (!this.isChatRunning) return;

		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({ type: 'stop_chat' }));
		}

		// Remove typing indicator
		if (this.currentChatTypingId) {
			this.removeTypingIndicator(this.currentChatTypingId);
			this.currentChatTypingId = null;
		}

		this.isChatRunning = false;
		this.updateChatUI(false);
		this.showToast('Chat stopped', 'info');
	}

	updateChatUI(running) {
		const sendBtn = document.getElementById('send-chat-btn');
		const stopBtn = document.getElementById('stop-chat-btn');
		const chatInput = document.getElementById('chat-input');

		sendBtn.disabled = running;
		stopBtn.disabled = !running;
		chatInput.disabled = running;

		if (running) {
			sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
		} else {
			sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
		}
	}

	handleChatResponse(data) {
		// Stream update - add partial content or update existing message
		if (data.streaming && this.currentChatTypingId) {
			// Update the typing indicator with partial content
			const typingEl = document.getElementById(this.currentChatTypingId);
			if (typingEl) {
				const bubble = typingEl.querySelector('.message-bubble');
				if (bubble) {
					bubble.innerHTML = this.formatMessageContent(data.content || 'Thinking...');
				}
			}
		}
	}

	handleChatComplete(data) {
		// Remove typing indicator
		if (this.currentChatTypingId) {
			this.removeTypingIndicator(this.currentChatTypingId);
			this.currentChatTypingId = null;
		}

		// Add final assistant response
		this.addChatMessage(data.response, 'assistant', data.success);

		// Update conversation history
		this.conversationHistory.push({
			type: 'assistant',
			content: data.response,
			timestamp: new Date().toISOString(),
			success: data.success
		});

		// Update UI state
		this.isChatRunning = false;
		this.updateChatUI(false);
	}

	handleChatError(data) {
		// Remove typing indicator
		if (this.currentChatTypingId) {
			this.removeTypingIndicator(this.currentChatTypingId);
			this.currentChatTypingId = null;
		}

		// Add error message
		this.addChatMessage('Sorry, I encountered an error processing your message.', 'assistant', false);
		this.showToast(data.error || 'Chat error occurred', 'error');

		// Update UI state
		this.isChatRunning = false;
		this.updateChatUI(false);
	}

	// Automation Templates
	async loadAutomationTemplates() {
		try {
			const response = await fetch(`${this.apiBase}/api/automation-templates`);
			this.automationTemplates = await response.json();
			this.renderAutomationTemplates();
		} catch (error) {
			console.error('Failed to load automation templates:', error);
			this.showToast('Failed to load automation templates', 'error');
		}
	}

	switchAutomationCategory(category) {
		// Update active tab
		document.querySelectorAll('.category-tab').forEach(tab => {
			tab.classList.remove('active');
		});
		document.querySelector(`[data-category="${category}"]`).classList.add('active');

		// Update current category and render
		this.currentAutomationCategory = category;
		this.renderAutomationTemplates();
	}

	renderAutomationTemplates() {
		const container = document.getElementById('automation-list');
		
		if (!this.automationTemplates[this.currentAutomationCategory]) {
			container.innerHTML = '<div class="loading-automations"><i class="fas fa-spinner fa-spin"></i> Loading automations...</div>';
			return;
		}

		const templates = this.automationTemplates[this.currentAutomationCategory];
		
		if (templates.length === 0) {
			container.innerHTML = '<div class="text-center" style="padding: 1rem; color: var(--gray-500);">No automations in this category</div>';
			return;
		}

		container.innerHTML = '';

		templates.forEach((template, index) => {
			const btn = document.createElement('button');
			btn.className = 'automation-btn';
			btn.onclick = () => this.executeAutomation(template.prompt);
			
			// Add right-click context menu for saving
			btn.oncontextmenu = (e) => {
				e.preventDefault();
				this.showAutomationContextMenu(e, template);
			};

			btn.innerHTML = `
				<div class="automation-content">
					<div class="automation-name">${template.name}</div>
					<div class="automation-preview">${template.prompt}</div>
				</div>
				<i class="fas fa-play"></i>
			`;

			container.appendChild(btn);
		});
	}

	executeAutomation(prompt) {
		if (this.isChatRunning) {
			this.showToast('Chat is currently running, please wait...', 'warning');
			return;
		}
		document.getElementById('chat-input').value = prompt;
		this.sendChatMessage();
	}

	showAutomationContextMenu(event, template) {
		// For now, just show a toast about saving (can be enhanced later)
		this.showToast(`"${template.name}" automation available for quick access`, 'info');
	}

	// Agent Functionality
	async runAgent() {
		if (this.isAgentRunning) return;

		const task = document.getElementById('agent-task').value.trim();
		if (!task) {
			this.showToast('Please enter a task description', 'warning');
			return;
		}

		const maxSteps = parseInt(document.getElementById('max-steps').value);
		const maxActions = parseInt(document.getElementById('max-actions').value);
		const provider = document.getElementById('agent-provider').value;
		const model = document.getElementById('agent-model').value;
		const apiKey = document.getElementById('agent-api-key').value;

		this.isAgentRunning = true;
		this.updateAgentUI(true);

		// Send task via WebSocket
		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({
				type: 'agent_task',
				data: {
					task,
					max_steps: maxSteps,
					max_actions: maxActions,
					llm_provider: provider,
					llm_model: model,
					api_key: apiKey
				}
			}));
		} else {
			this.showToast('WebSocket not connected', 'error');
			this.isAgentRunning = false;
			this.updateAgentUI(false);
		}
	}

	stopAgent() {
		if (!this.isAgentRunning) return;

		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({ type: 'stop_agent' }));
		}

		this.isAgentRunning = false;
		this.updateAgentUI(false);
	}

	handleAgentStreamUpdate(data) {
		const { status, message, step, max_steps, final_result } = data;

		// Update execution status
		const statusEl = document.getElementById('execution-status');
		const statusText = statusEl.querySelector('.status-text');
		
		statusEl.className = `execution-status ${status}`;
		statusText.textContent = this.capitalizeFirst(status);

		// Update progress
		if (step !== undefined && max_steps !== undefined) {
			this.updateAgentProgress(step, max_steps, message);
		}

		// Add terminal output
		if (message) {
			this.addTerminalLine(message, status);
		}

		// Handle completion
		if (status === 'completed' || status === 'failed' || status === 'error') {
			this.isAgentRunning = false;
			this.updateAgentUI(false);

			if (final_result) {
				this.showAgentResult(final_result);
			}

			const toastType = status === 'completed' ? 'success' : 'error';
			this.showToast(message || `Agent ${status}`, toastType);
		}
	}

	updateAgentUI(running) {
		const runBtn = document.getElementById('run-agent-btn');
		const stopBtn = document.getElementById('stop-agent-btn');
		const progressSection = document.getElementById('agent-progress');

		runBtn.disabled = running;
		stopBtn.disabled = !running;

		if (running) {
			progressSection.classList.remove('hidden');
		} else {
			progressSection.classList.add('hidden');
		}
	}

	updateAgentProgress(step, maxSteps, message) {
		const progressText = document.getElementById('progress-text');
		const progressStep = document.getElementById('progress-step');
		const progressFill = document.getElementById('progress-fill');

		progressText.textContent = message || `Processing step ${step}...`;
		progressStep.textContent = `Step ${step} / ${maxSteps}`;

		const percentage = (step / maxSteps) * 100;
		progressFill.style.width = `${percentage}%`;
	}

	addTerminalLine(text, type = 'info') {
		const terminalContent = document.getElementById('terminal-content');
		
		// Remove ready message if it exists
		const readyMsg = terminalContent.querySelector('.terminal-ready');
		if (readyMsg) {
			readyMsg.remove();
		}

		const line = document.createElement('div');
		line.className = `terminal-line terminal-${type}`;
		line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;

		terminalContent.appendChild(line);
		terminalContent.scrollTop = terminalContent.scrollHeight;
	}

	clearTerminal() {
		const terminalContent = document.getElementById('terminal-content');
		terminalContent.innerHTML = '<p class="terminal-ready">Ready to execute agent tasks...</p>';
	}

	showAgentResult(result) {
		const resultSection = document.getElementById('agent-result');
		const resultContent = document.getElementById('result-content');

		resultContent.textContent = result;
		resultSection.classList.remove('hidden');
	}

	async refineTask() {
		const taskInput = document.getElementById('agent-task');
		const originalTask = taskInput.value.trim();
		
		if (!originalTask) {
			this.showToast('Please enter a task first', 'warning');
			return;
		}

		const provider = document.getElementById('agent-provider').value;
		const model = document.getElementById('agent-model').value;
		const apiKey = document.getElementById('agent-api-key').value;

		const refineBtn = document.getElementById('refine-task-btn');
		const originalText = refineBtn.innerHTML;
		refineBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refining...';
		refineBtn.disabled = true;

		try {
			const response = await fetch(`${this.apiBase}/api/chat/send`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					message: `Please refine this task to be more specific and actionable for macOS automation: "${originalTask}"`,
					llm_provider: provider,
					llm_model: model,
					api_key: apiKey
				})
			});

			const data = await response.json();
			
			if (data.success) {
				taskInput.value = data.response;
				this.showToast('Task refined successfully', 'success');
			} else {
				this.showToast('Failed to refine task', 'error');
			}

		} catch (error) {
			console.error('Refine task error:', error);
			this.showToast('Failed to refine task', 'error');
		} finally {
			refineBtn.innerHTML = originalText;
			refineBtn.disabled = false;
		}
	}

	// Provider Management
	async loadProviders() {
		try {
			const response = await fetch(`${this.apiBase}/api/providers`);
			this.providers = await response.json();
			this.renderProviders();
			this.updateProviderSelects();
		} catch (error) {
			console.error('Failed to load providers:', error);
			this.showToast('Failed to load providers', 'error');
		}
	}

	renderProviders() {
		const container = document.getElementById('providers-grid');
		
		if (Object.keys(this.providers).length === 0) {
			container.innerHTML = '<div class="loading-providers"><i class="fas fa-spinner fa-spin"></i> Loading providers...</div>';
			return;
		}

		container.innerHTML = '';

		Object.entries(this.providers).forEach(([name, info]) => {
			const card = document.createElement('div');
			card.className = 'provider-card';
			
			const statusClass = info.available ? 'available' : 'unavailable';
			const statusText = info.available ? 'Available' : 'Unavailable';
			const statusIcon = info.available ? 'fa-check-circle' : 'fa-times-circle';

			card.innerHTML = `
				<div class="provider-header">
					<h3 class="provider-name">${name}</h3>
					<div class="provider-status ${statusClass}">
						<i class="fas ${statusIcon}"></i>
						${statusText}
					</div>
				</div>
				<div class="provider-info">
					${info.api_key_required ? 'API key required' : 'No API key needed'}
				</div>
				<div class="provider-models">
					<h4>Available Models:</h4>
					<div class="models-list">
						${info.models.slice(0, 5).map(model => 
							`<span class="model-tag">${model}</span>`
						).join('')}
						${info.models.length > 5 ? `<span class="model-tag">+${info.models.length - 5} more</span>` : ''}
					</div>
				</div>
				${info.api_key_required ? `
					<div class="provider-actions">
						<input type="password" class="api-key-input" placeholder="Enter API key..." 
							   id="api-key-${name}" data-provider="${name}">
						<button class="btn btn-primary btn-sm" onclick="app.testProvider('${name}')">
							<i class="fas fa-check"></i> Test
						</button>
					</div>
				` : `
					<div class="provider-actions">
						<button class="btn btn-primary btn-sm" onclick="app.testProvider('${name}')" 
								${!info.available ? 'disabled' : ''}>
							<i class="fas fa-check"></i> Test Connection
						</button>
					</div>
				`}
			`;

			container.appendChild(card);
		});
	}

	async testProvider(providerName) {
		const apiKeyInput = document.getElementById(`api-key-${providerName}`);
		const apiKey = apiKeyInput ? apiKeyInput.value : null;
		const provider = this.providers[providerName];
		
		if (!provider) return;

		const model = provider.models[0];
		if (!model) {
			this.showToast('No models available for this provider', 'warning');
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/providers/test`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					provider: providerName,
					model: model,
					api_key: apiKey
				})
			});

			const data = await response.json();
			const toastType = data.success ? 'success' : 'error';
			this.showToast(data.message, toastType);

		} catch (error) {
			console.error('Provider test error:', error);
			this.showToast('Failed to test provider', 'error');
		}
	}

	updateProviderSelects() {
		const chatProvider = document.getElementById('chat-provider');
		const agentProvider = document.getElementById('agent-provider');

		// Clear existing options
		chatProvider.innerHTML = '';
		agentProvider.innerHTML = '';

		// Add provider options
		Object.entries(this.providers).forEach(([name, info]) => {
			if (info.available) {
				const option = document.createElement('option');
				option.value = name;
				option.textContent = name;
				
				chatProvider.appendChild(option.cloneNode(true));
				agentProvider.appendChild(option);
			}
		});

		// Set default to OpenAI if available, otherwise first available
		let defaultProvider = "OpenAI";
		if (!this.providers["OpenAI"] || !this.providers["OpenAI"].available) {
			defaultProvider = Object.keys(this.providers).find(p => this.providers[p].available) || "OpenAI";
		}
		
		chatProvider.value = defaultProvider;
		agentProvider.value = defaultProvider;
		
		// Update models for default provider
		this.updateChatModels(defaultProvider);
		this.updateAgentModels(defaultProvider);
	}

	updateChatModels(provider) {
		const modelSelect = document.getElementById('chat-model');
		this.updateModelSelect(modelSelect, provider);
	}

	updateAgentModels(provider) {
		const modelSelect = document.getElementById('agent-model');
		this.updateModelSelect(modelSelect, provider);
	}

	updateModelSelect(selectElement, provider) {
		selectElement.innerHTML = '';
		
		if (this.providers[provider] && this.providers[provider].models) {
			this.providers[provider].models.forEach(model => {
				const option = document.createElement('option');
				option.value = model;
				
				// Add helpful indicators for tool-capable models
				let displayText = model;
				if (provider === "OpenRouter") {
					if (model.includes("openai/") || model.includes("anthropic/") || model.includes("google/")) {
						displayText += " ✓"; // Indicates tool support
					} else if (model.includes("gpt") || model.includes("claude") || model.includes("gemini")) {
						displayText += " ✓"; // Likely tool support
					}
					if (model.includes(":free")) {
						displayText += " (Free)";
					}
				}
				
				option.textContent = displayText;
				selectElement.appendChild(option);
			});
		}
	}

	// Session Management
	async loadSessions() {
		try {
			const response = await fetch(`${this.apiBase}/api/sessions`);
			this.sessions = await response.json();
			this.renderSessions();
		} catch (error) {
			console.error('Failed to load sessions:', error);
			this.showToast('Failed to load sessions', 'error');
		}
	}

	renderSessions() {
		const container = document.getElementById('sessions-container');
		
		if (this.sessions.length === 0) {
			container.innerHTML = `
				<div class="text-center" style="grid-column: 1 / -1; padding: 2rem;">
					<i class="fas fa-history" style="font-size: 3rem; color: var(--gray-400); margin-bottom: 1rem;"></i>
					<h3>No Sessions Found</h3>
					<p class="text-muted">Start a conversation to create your first session.</p>
				</div>
			`;
			return;
		}

		container.innerHTML = '';

		this.sessions.forEach(session => {
			const card = document.createElement('div');
			card.className = 'session-card';
			card.onclick = () => this.loadSession(session.name);

			const date = new Date(session.timestamp).toLocaleDateString();
			const time = new Date(session.timestamp).toLocaleTimeString();

			card.innerHTML = `
				<div class="session-card-header">
					<h3 class="session-name">${session.name}</h3>
					<div class="session-actions">
						<button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); app.deleteSession('${session.name}')">
							<i class="fas fa-trash"></i>
						</button>
					</div>
				</div>
				<div class="session-meta">${date} at ${time}</div>
				<div class="session-stats">
					<div class="session-stat">
						<i class="fas fa-comments"></i>
						${session.message_count} messages
					</div>
					<div class="session-stat success">
						<i class="fas fa-check"></i>
						${session.success_count}
					</div>
					<div class="session-stat failure">
						<i class="fas fa-times"></i>
						${session.failure_count}
					</div>
				</div>
			`;

			container.appendChild(card);
		});
	}

	async loadSession(sessionName) {
		try {
			const response = await fetch(`${this.apiBase}/api/sessions/${sessionName}`);
			const sessionData = await response.json();

			// Clear current chat
			this.clearChat();

			// Load messages
			this.conversationHistory = sessionData.messages;
			sessionData.messages.forEach(msg => {
				this.addChatMessage(msg.content, msg.type, msg.success);
			});

			// Switch to chat tab
			this.switchTab('chat');
			this.showToast(`Loaded session: ${sessionName}`, 'success');

		} catch (error) {
			console.error('Failed to load session:', error);
			this.showToast('Failed to load session', 'error');
		}
	}

	async deleteSession(sessionName) {
		if (!confirm(`Are you sure you want to delete session "${sessionName}"?`)) {
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/sessions/${sessionName}`, {
				method: 'DELETE'
			});

			if (response.ok) {
				this.showToast('Session deleted', 'success');
				this.loadSessions(); // Refresh list
			} else {
				this.showToast('Failed to delete session', 'error');
			}
		} catch (error) {
			console.error('Failed to delete session:', error);
			this.showToast('Failed to delete session', 'error');
		}
	}

	async saveCurrentSession() {
		const sessionNameInput = document.getElementById('session-name-input');
		const sessionName = sessionNameInput.value.trim();

		if (!sessionName) {
			this.showToast('Please enter a session name', 'warning');
			return;
		}

		if (this.conversationHistory.length === 0) {
			this.showToast('No conversation to save', 'warning');
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/sessions`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					session_name: sessionName,
					conversation_history: this.conversationHistory
				})
			});

			const data = await response.json();

			if (data.success) {
				sessionNameInput.value = '';
				this.showToast('Session saved successfully', 'success');
				this.loadSessions(); // Refresh list
			} else {
				this.showToast('Failed to save session', 'error');
			}

		} catch (error) {
			console.error('Failed to save session:', error);
			this.showToast('Failed to save session', 'error');
		}
	}

	showSaveChatModal() {
		// For now, just focus the session name input and switch to sessions tab
		this.switchTab('sessions');
		setTimeout(() => {
			const input = document.getElementById('session-name-input');
			input.focus();
			input.value = `Chat ${new Date().toLocaleDateString()}`;
		}, 300);
	}

	// Utility Functions
	showToast(message, type = 'info') {
		const container = document.getElementById('toast-container');
		const toast = document.createElement('div');
		toast.className = `toast ${type}`;
		toast.textContent = message;

		container.appendChild(toast);

		// Auto remove after 5 seconds
		setTimeout(() => {
			toast.style.opacity = '0';
			setTimeout(() => {
				if (toast.parentNode) {
					toast.parentNode.removeChild(toast);
				}
			}, 300);
		}, 5000);
	}

	capitalizeFirst(str) {
		return str.charAt(0).toUpperCase() + str.slice(1);
	}
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
	window.app = new MacOSAutomationApp();
});