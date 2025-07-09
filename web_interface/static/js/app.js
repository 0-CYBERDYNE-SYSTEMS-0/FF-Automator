/**
 * FF-Terminal:Desktop_ver - Elegant Interface JavaScript Application
 * Modern vanilla JavaScript implementation with component architecture
 */

class FFTerminalApp {
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
		this.savedAutomations = [];
		this.scheduledAutomations = [];
		this.currentAgentExecution = null; // Track current agent execution for saving
		
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
			await this.loadSavedAutomations();
			await this.setupAutomationEventListeners();
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
		
		// Mobile Navigation
		document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
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
		
		// Context bucket functionality
		this.setupContextBucket();
	}

	setupChatListeners() {
		const chatInput = document.getElementById('chat-input');
		const sendBtn = document.getElementById('send-chat-btn');
		const stopBtn = document.getElementById('stop-chat-btn');
		const interruptBtn = document.getElementById('interrupt-chat-btn');
		const redirectBtn = document.getElementById('redirect-chat-btn');
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

		// Interrupt button
		interruptBtn.addEventListener('click', () => this.interruptChat());

		// Redirect button
		redirectBtn.addEventListener('click', () => this.redirectChat());

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
		const saveAgentBtn = document.getElementById('save-agent-automation-btn');

		runBtn.addEventListener('click', () => this.runAgent());
		stopBtn.addEventListener('click', () => this.stopAgent());
		refineBtn.addEventListener('click', () => this.refineTask());
		clearTerminalBtn.addEventListener('click', () => this.clearTerminal());
		saveAgentBtn.addEventListener('click', () => this.saveAgentAsAutomation());

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
			case 'chat_stream_update':
				this.handleChatStreamUpdate(message.data);
				break;
			case 'chat_complete':
				this.handleChatComplete(message.data);
				break;
			case 'chat_error':
				this.handleChatError(message.data);
				break;
			case 'automation_save_result':
				this.handleAutomationSaveResult(message.data);
				break;
			case 'automation_execute_result':
				this.handleAutomationExecuteResult(message.data);
				break;
			case 'automation_status':
				this.handleAutomationStatus(message.data);
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
		// Update navigation - handle both desktop and mobile nav buttons
		document.querySelectorAll('.nav-btn').forEach(btn => {
			btn.classList.remove('active');
		});
		document.querySelectorAll('.mobile-nav-btn').forEach(btn => {
			btn.classList.remove('active');
		});
		
		// Add active class to all matching tab buttons (desktop and mobile)
		document.querySelectorAll(`[data-tab="${tabName}"]`).forEach(btn => {
			btn.classList.add('active');
		});

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

		// Get custom system message
		const customSystemMessage = document.getElementById('chat-custom-system').value.trim();

		// Send via WebSocket
		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({
				type: 'chat_message',
				data: {
					message,
					llm_provider: provider,
					llm_model: model,
					api_key: apiKey,
					custom_system_message: customSystemMessage
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
					<h3>Welcome to FF-Terminal:Desktop_ver!</h3>
					<p>I'm your AI assistant for automating desktop tasks. You can:</p>
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

	interruptChat() {
		if (!this.isChatRunning) return;

		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({ type: 'interrupt_chat', data: {} }));
		}

		this.showToast('Chat interrupted', 'info');
	}

	redirectChat() {
		if (!this.isChatRunning) return;

		const newTask = prompt('Enter the new task to redirect to:');
		if (!newTask || !newTask.trim()) return;

		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({ 
				type: 'redirect_chat', 
				data: { task: newTask.trim() } 
			}));
		}

		this.showToast(`Redirecting to: ${newTask}`, 'info');
	}

	updateChatUI(running) {
		const sendBtn = document.getElementById('send-chat-btn');
		const stopBtn = document.getElementById('stop-chat-btn');
		const interruptBtn = document.getElementById('interrupt-chat-btn');
		const redirectBtn = document.getElementById('redirect-chat-btn');
		const chatInput = document.getElementById('chat-input');

		sendBtn.disabled = running;
		stopBtn.disabled = !running;
		interruptBtn.disabled = !running;
		redirectBtn.disabled = !running;
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

	handleChatStreamUpdate(data) {
		// Handle multi-step chat execution updates
		const { status, message, step, max_steps, queue_status, current_task } = data;

		// Update or create typing indicator based on status
		if (status === 'starting') {
			this.currentChatTypingId = this.addTypingIndicator();
		}

		// Update typing indicator with current status
		if (this.currentChatTypingId) {
			const typingEl = document.getElementById(this.currentChatTypingId);
			if (typingEl) {
				const bubble = typingEl.querySelector('.message-bubble');
				if (bubble) {
					let displayMessage = message;
					
					// Add step information if available
					if (step && max_steps) {
						displayMessage += ` (Step ${step}/${max_steps})`;
					}
					
					// Add task queue information if available
					if (queue_status && queue_status.pending_tasks > 0) {
						displayMessage += ` [${queue_status.pending_tasks} tasks queued]`;
					}
					
					// Add status indicator
					const statusIcon = this.getStatusIcon(status);
					bubble.innerHTML = `${statusIcon} ${this.formatMessageContent(displayMessage)}`;
				}
			}
		}

		// Add progress message for certain statuses
		if (status === 'step_completed' || status === 'next_task' || status === 'task_added') {
			this.addChatMessage(message, 'assistant', true);
		}

		// Handle special statuses
		if (status === 'interrupted' || status === 'redirected') {
			this.addChatMessage(message, 'assistant', true);
			this.showToast(message, 'info');
		}
	}

	getStatusIcon(status) {
		const icons = {
			'starting': '<i class="fas fa-play fa-pulse"></i>',
			'running': '<i class="fas fa-cog fa-spin"></i>',
			'step_completed': '<i class="fas fa-check"></i>',
			'completed': '<i class="fas fa-check-circle"></i>',
			'next_task': '<i class="fas fa-arrow-right"></i>',
			'interrupted': '<i class="fas fa-pause"></i>',
			'redirected': '<i class="fas fa-route"></i>',
			'task_added': '<i class="fas fa-plus"></i>',
			'error': '<i class="fas fa-exclamation-triangle"></i>'
		};
		return icons[status] || '<i class="fas fa-robot"></i>';
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

		// Reset execution tracking for new run
		this.currentAgentExecution = null;
		const saveBtn = document.getElementById('save-agent-automation-btn');
		saveBtn.disabled = true;

		this.isAgentRunning = true;
		this.updateAgentUI(true);

		// Get custom system message
		const customSystemMessage = document.getElementById('agent-custom-system').value.trim();

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
					api_key: apiKey,
					custom_system_message: customSystemMessage
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

		// Track execution data for saving
		if (!this.currentAgentExecution) {
			this.currentAgentExecution = {
				task: document.getElementById('agent-task').value,
				status: status,
				steps: [],
				provider: document.getElementById('agent-provider').value,
				model: document.getElementById('agent-model').value,
				custom_system: document.getElementById('agent-custom-system').value,
				started_at: new Date().toISOString()
			};
		}

		// Update execution tracking
		this.currentAgentExecution.status = status;
		if (message) {
			this.currentAgentExecution.steps.push({
				step: step,
				message: message,
				status: status,
				timestamp: new Date().toISOString()
			});
		}

		// Handle completion
		if (status === 'completed' || status === 'failed' || status === 'error' || status === 'stopped') {
			this.isAgentRunning = false;
			this.updateAgentUI(false);

			if (final_result) {
				this.showAgentResult(final_result);
				this.currentAgentExecution.final_result = final_result;
			}

			this.currentAgentExecution.completed_at = new Date().toISOString();

			// Enable save button only on successful completion
			const saveBtn = document.getElementById('save-agent-automation-btn');
			saveBtn.disabled = status !== 'completed';

			const toastType = status === 'completed' ? 'success' : (status === 'stopped' ? 'warning' : 'error');
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
			const systemMessage = `You are a helpful assistant that refines user prompts for a FF-Terminal:Desktop_ver agent.
The user has provided a prompt: "${originalTask}"

Your task is to refine this prompt to make it more specific, clearer, and more likely to succeed when executed on macOS.
For this purpose the agent can preform the following actions:
- Open an app
- Click on an element
- Type text into a field
- Create an AppleScript
          
GENERAL PRINCIPLES:
1. Include useful details that make the task clear and executable (e.g Open [app name], click on the [element name])
2. Don't change the intent of the original prompt!
3. If the task involves multiple steps, break it down into smaller steps
4. When prompting for opening an app, ALWAYS prompt with "open 'app name'"
5. When prompting for opening a browser, prompt with "open a new window"
6. Dont take the user sequence as granted, decide for yourself what is the best way to accomplish the task

Only return the refined prompt text, nothing else.`;

			const response = await fetch(`${this.apiBase}/api/refine-prompt`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					message: originalTask,
					system_message: systemMessage,
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

	// Automation Management Methods
	async loadSavedAutomations() {
		try {
			const response = await fetch(`${this.apiBase}/api/automations`);
			this.savedAutomations = await response.json();
			this.renderSavedAutomations();
		} catch (error) {
			console.error('Failed to load saved automations:', error);
		}
	}

	async saveAgentAsAutomation() {
		if (!this.currentAgentExecution || this.currentAgentExecution.status !== 'completed') {
			this.showToast('No successful agent execution to save as automation', 'warning');
			return;
		}

		const modal = document.createElement('div');
		modal.className = 'modal-overlay';
		modal.innerHTML = `
			<div class="modal-content">
				<h3>Save Agent as Automation</h3>
				<form id="save-agent-automation-form">
					<div class="form-group">
						<label for="agent-automation-name">Automation Name</label>
						<input type="text" id="agent-automation-name" required placeholder="Enter automation name" value="${this.currentAgentExecution.task.substring(0, 50)}">
					</div>
					<div class="form-group">
						<label for="agent-automation-description">Description (optional)</label>
						<textarea id="agent-automation-description" placeholder="Describe what this automation does">${this.currentAgentExecution.task}</textarea>
					</div>
					<div class="form-group">
						<label for="agent-automation-category">Category</label>
						<input type="text" id="agent-automation-category" placeholder="e.g. Productivity, Communication" value="Agent Tasks">
					</div>
					<div class="form-group">
						<label for="agent-automation-tags">Tags (comma-separated)</label>
						<input type="text" id="agent-automation-tags" placeholder="e.g. automation, agent, task">
					</div>
					<div class="modal-buttons">
						<button type="button" class="secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
						<button type="submit" class="primary">Save Automation</button>
					</div>
				</form>
			</div>
		`;

		document.body.appendChild(modal);

		const form = modal.querySelector('#save-agent-automation-form');
		form.addEventListener('submit', async (e) => {
			e.preventDefault();

			const name = document.getElementById('agent-automation-name').value;
			const description = document.getElementById('agent-automation-description').value;
			const category = document.getElementById('agent-automation-category').value;
			const tags = document.getElementById('agent-automation-tags').value;

			if (this.socket && this.socket.readyState === WebSocket.OPEN) {
				this.socket.send(JSON.stringify({
					type: 'save_automation',
					data: {
						name,
						description,
						task: this.currentAgentExecution.task,
						category,
						tags,
						custom_system_message: this.currentAgentExecution.custom_system,
						llm_provider: this.currentAgentExecution.provider,
						llm_model: this.currentAgentExecution.model,
						execution_data: this.currentAgentExecution
					}
				}));

				modal.remove();
				this.showToast('Saving automation...', 'info');
			} else {
				this.showToast('WebSocket not connected', 'error');
			}
		});
	}

	async saveCurrentChatAsAutomation() {
		if (this.conversationHistory.length === 0) {
			this.showToast('No conversation to save as automation', 'warning');
			return;
		}

		const modal = document.createElement('div');
		modal.className = 'modal-overlay';
		modal.innerHTML = `
			<div class="modal-content">
				<h3>Save as Automation</h3>
				<form id="save-automation-form">
					<div class="form-group">
						<label for="automation-name">Automation Name</label>
						<input type="text" id="automation-name" required placeholder="Enter automation name">
					</div>
					<div class="form-group">
						<label for="automation-description">Description (optional)</label>
						<textarea id="automation-description" placeholder="Describe what this automation does"></textarea>
					</div>
					<div class="form-group">
						<label for="automation-category">Category</label>
						<input type="text" id="automation-category" placeholder="e.g. Productivity, Communication">
					</div>
					<div class="form-group">
						<label for="automation-tags">Tags (comma-separated)</label>
						<input type="text" id="automation-tags" placeholder="e.g. email, calendar, quick">
					</div>
					<div class="modal-buttons">
						<button type="button" class="secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
						<button type="submit" class="primary">Save Automation</button>
					</div>
				</form>
			</div>
		`;

		document.body.appendChild(modal);

		const form = document.getElementById('save-automation-form');
		form.addEventListener('submit', async (e) => {
			e.preventDefault();
			
			const name = document.getElementById('automation-name').value;
			const description = document.getElementById('automation-description').value;
			const category = document.getElementById('automation-category').value;
			const tags = document.getElementById('automation-tags').value.split(',').map(t => t.trim()).filter(t => t);
			
			if (!name) {
				this.showToast('Automation name is required', 'error');
				return;
			}

			// Send save automation message via WebSocket
			if (this.socket && this.socket.readyState === WebSocket.OPEN) {
				this.socket.send(JSON.stringify({
					type: 'save_automation',
					data: {
						name,
						description,
						task: this.conversationHistory[0]?.content || name,
						category,
						tags,
						custom_system_message: this.getCustomSystemMessage(),
						llm_provider: this.getCurrentProvider(),
						llm_model: this.getCurrentModel()
					}
				}));
			}

			modal.remove();
		});
	}

	async executeAutomation(automationId, parameters = {}) {
		if (this.socket && this.socket.readyState === WebSocket.OPEN) {
			this.socket.send(JSON.stringify({
				type: 'execute_automation',
				data: {
					automation_id: automationId,
					runtime_parameters: parameters
				}
			}));
		}
	}

	async deleteAutomation(automationId) {
		if (!confirm('Are you sure you want to delete this automation?')) {
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/automations/${automationId}`, {
				method: 'DELETE'
			});

			const data = await response.json();

			if (data.success) {
				this.showToast('Automation deleted successfully', 'success');
				this.loadSavedAutomations();
			} else {
				this.showToast('Failed to delete automation', 'error');
			}
		} catch (error) {
			console.error('Failed to delete automation:', error);
			this.showToast('Failed to delete automation', 'error');
		}
	}

	async scheduleAutomation(automationId) {
		const modal = document.createElement('div');
		modal.className = 'modal-overlay';
		modal.innerHTML = `
			<div class="modal-content">
				<h3>Schedule Automation</h3>
				<form id="schedule-automation-form">
					<div class="form-group">
						<label for="schedule-type">Schedule Type</label>
						<select id="schedule-type" required>
							<option value="">Select schedule type</option>
							<option value="daily">Daily</option>
							<option value="weekly">Weekly</option>
							<option value="hourly">Hourly</option>
							<option value="custom">Custom (Cron)</option>
						</select>
					</div>
					<div class="form-group" id="time-group" style="display: none;">
						<label for="schedule-time">Time</label>
						<input type="time" id="schedule-time">
					</div>
					<div class="form-group" id="weekday-group" style="display: none;">
						<label for="schedule-weekday">Day of Week</label>
						<select id="schedule-weekday">
							<option value="1">Monday</option>
							<option value="2">Tuesday</option>
							<option value="3">Wednesday</option>
							<option value="4">Thursday</option>
							<option value="5">Friday</option>
							<option value="6">Saturday</option>
							<option value="0">Sunday</option>
						</select>
					</div>
					<div class="form-group" id="cron-group" style="display: none;">
						<label for="schedule-cron">Cron Expression</label>
						<input type="text" id="schedule-cron" placeholder="0 9 * * 1-5 (9 AM weekdays)">
						<small>Format: minute hour day month weekday</small>
					</div>
					<div class="modal-buttons">
						<button type="button" class="secondary" onclick="this.closest('.modal-overlay').remove()">Cancel</button>
						<button type="submit" class="primary">Schedule</button>
					</div>
				</form>
			</div>
		`;

		document.body.appendChild(modal);

		// Handle schedule type changes
		const scheduleType = document.getElementById('schedule-type');
		const timeGroup = document.getElementById('time-group');
		const weekdayGroup = document.getElementById('weekday-group');
		const cronGroup = document.getElementById('cron-group');

		scheduleType.addEventListener('change', () => {
			timeGroup.style.display = 'none';
			weekdayGroup.style.display = 'none';
			cronGroup.style.display = 'none';

			switch (scheduleType.value) {
				case 'daily':
				case 'weekly':
					timeGroup.style.display = 'block';
					if (scheduleType.value === 'weekly') {
						weekdayGroup.style.display = 'block';
					}
					break;
				case 'custom':
					cronGroup.style.display = 'block';
					break;
			}
		});

		const form = document.getElementById('schedule-automation-form');
		form.addEventListener('submit', async (e) => {
			e.preventDefault();
			
			let cronExpression = '';
			const type = scheduleType.value;
			const time = document.getElementById('schedule-time').value;
			const weekday = document.getElementById('schedule-weekday').value;
			const customCron = document.getElementById('schedule-cron').value;

			switch (type) {
				case 'daily':
					if (!time) {
						this.showToast('Time is required for daily schedule', 'error');
						return;
					}
					const [hour, minute] = time.split(':');
					cronExpression = `${minute} ${hour} * * *`;
					break;
				case 'weekly':
					if (!time) {
						this.showToast('Time is required for weekly schedule', 'error');
						return;
					}
					const [wHour, wMinute] = time.split(':');
					cronExpression = `${wMinute} ${wHour} * * ${weekday}`;
					break;
				case 'hourly':
					cronExpression = '0 * * * *';
					break;
				case 'custom':
					if (!customCron) {
						this.showToast('Cron expression is required', 'error');
						return;
					}
					cronExpression = customCron;
					break;
				default:
					this.showToast('Please select a schedule type', 'error');
					return;
			}

			try {
				const response = await fetch(`${this.apiBase}/api/automations/${automationId}/schedule`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({
						automation_id: automationId,
						cron_expression: cronExpression
					})
				});

				const data = await response.json();

				if (data.success) {
					this.showToast('Automation scheduled successfully', 'success');
					modal.remove();
				} else {
					this.showToast('Failed to schedule automation', 'error');
				}
			} catch (error) {
				console.error('Failed to schedule automation:', error);
				this.showToast('Failed to schedule automation', 'error');
			}
		});
	}

	renderSavedAutomations() {
		const container = document.getElementById('saved-automations-list');
		if (!container) return;

		if (this.savedAutomations.length === 0) {
			container.innerHTML = `
				<div class="empty-state">
					<p>No saved automations yet</p>
					<small>Successful chat interactions can be saved as reusable automations</small>
				</div>
			`;
			return;
		}

		container.innerHTML = this.savedAutomations.map(automation => `
			<div class="automation-item">
				<div class="automation-header">
					<h4>${automation.name}</h4>
					<div class="automation-stats">
						<span class="success-count">${automation.success_count} successes</span>
						<span class="failure-count">${automation.failure_count} failures</span>
					</div>
				</div>
				<p class="automation-description">${automation.description || 'No description'}</p>
				<div class="automation-meta">
					<span class="category">${automation.category || 'Uncategorized'}</span>
					<span class="steps">${automation.steps_count} steps</span>
					<span class="updated">${new Date(automation.updated_at).toLocaleDateString()}</span>
				</div>
				<div class="automation-actions">
					<button class="run-button" onclick="app.executeAutomation('${automation.id}')">Run</button>
					<button class="schedule-button" onclick="app.scheduleAutomation('${automation.id}')">Schedule</button>
					<button class="delete-button" onclick="app.deleteAutomation('${automation.id}')">Delete</button>
				</div>
			</div>
		`).join('');
	}

	getCurrentProvider() {
		const providerSelect = document.getElementById('llm-provider');
		return providerSelect ? providerSelect.value : 'OpenAI';
	}

	getCurrentModel() {
		const modelSelect = document.getElementById('llm-model');
		return modelSelect ? modelSelect.value : 'gpt-4';
	}

	getCustomSystemMessage() {
		const textarea = document.getElementById('custom-system-message');
		return textarea ? textarea.value : '';
	}

	setupAutomationEventListeners() {
		// Automation tab switching
		const automationTabBtns = document.querySelectorAll('.automation-tab-btn');
		automationTabBtns.forEach(btn => {
			btn.addEventListener('click', (e) => {
				// Remove active class from all tabs and sections
				automationTabBtns.forEach(b => b.classList.remove('active'));
				document.querySelectorAll('.automation-section').forEach(s => s.classList.remove('active'));
				
				// Add active class to clicked tab
				btn.classList.add('active');
				
				// Show corresponding section
				const section = btn.getAttribute('data-section');
				const sectionElement = document.getElementById(`${section}-automations-section`);
				if (sectionElement) {
					sectionElement.classList.add('active');
				}
				
				// Load data for the section
				if (section === 'scheduled') {
					this.loadScheduledAutomations();
				} else if (section === 'history') {
					this.loadExecutionHistory();
				}
			});
		});

		// Search and filter functionality
		const searchInput = document.getElementById('automation-search');
		const categoryFilter = document.getElementById('automation-category-filter');
		
		if (searchInput) {
			searchInput.addEventListener('input', () => {
				this.filterAutomations();
			});
		}
		
		if (categoryFilter) {
			categoryFilter.addEventListener('change', () => {
				this.filterAutomations();
			});
		}
	}

	async loadScheduledAutomations() {
		try {
			const response = await fetch(`${this.apiBase}/api/scheduled-automations`);
			this.scheduledAutomations = await response.json();
			this.renderScheduledAutomations();
		} catch (error) {
			console.error('Failed to load scheduled automations:', error);
		}
	}

	async loadExecutionHistory() {
		// For now, just show empty state
		const container = document.getElementById('execution-history-list');
		if (container) {
			container.innerHTML = `
				<div class="empty-state">
					<p>No execution history</p>
					<small>History of automation executions will appear here</small>
				</div>
			`;
		}
	}

	renderScheduledAutomations() {
		const container = document.getElementById('scheduled-automations-list');
		if (!container) return;

		if (this.scheduledAutomations.length === 0) {
			container.innerHTML = `
				<div class="empty-state">
					<p>No scheduled automations</p>
					<small>Schedule automations to run automatically at specified times</small>
				</div>
			`;
			return;
		}

		container.innerHTML = this.scheduledAutomations.map(automation => `
			<div class="automation-item">
				<div class="automation-header">
					<h4>${automation.name}</h4>
					<div class="automation-stats">
						<span class="next-run">Next: ${automation.next_run ? new Date(automation.next_run).toLocaleString() : 'Not scheduled'}</span>
					</div>
				</div>
				<p class="automation-description">${automation.description || 'No description'}</p>
				<div class="automation-meta">
					<span class="schedules">${automation.schedules} schedule(s)</span>
					<span class="success-count">${automation.success_count} successes</span>
					<span class="failure-count">${automation.failure_count} failures</span>
				</div>
				<div class="automation-actions">
					<button class="run-button" onclick="app.executeAutomation('${automation.automation_id}')">Run Now</button>
					<button class="delete-button" onclick="app.unscheduleAutomation('${automation.automation_id}')">Unschedule</button>
				</div>
			</div>
		`).join('');
	}

	async unscheduleAutomation(automationId) {
		if (!confirm('Are you sure you want to unschedule this automation?')) {
			return;
		}

		try {
			// For now, just remove the first schedule (index 0)
			const response = await fetch(`${this.apiBase}/api/automations/${automationId}/schedule/0`, {
				method: 'DELETE'
			});

			const data = await response.json();

			if (data.success) {
				this.showToast('Automation unscheduled successfully', 'success');
				this.loadScheduledAutomations();
			} else {
				this.showToast('Failed to unschedule automation', 'error');
			}
		} catch (error) {
			console.error('Failed to unschedule automation:', error);
			this.showToast('Failed to unschedule automation', 'error');
		}
	}

	filterAutomations() {
		const searchTerm = document.getElementById('automation-search')?.value.toLowerCase() || '';
		const selectedCategory = document.getElementById('automation-category-filter')?.value || '';
		
		const automationItems = document.querySelectorAll('.automation-item');
		
		automationItems.forEach(item => {
			const title = item.querySelector('h4')?.textContent.toLowerCase() || '';
			const description = item.querySelector('.automation-description')?.textContent.toLowerCase() || '';
			const category = item.querySelector('.category')?.textContent || '';
			
			const matchesSearch = title.includes(searchTerm) || description.includes(searchTerm);
			const matchesCategory = !selectedCategory || category === selectedCategory;
			
			if (matchesSearch && matchesCategory) {
				item.style.display = 'block';
			} else {
				item.style.display = 'none';
			}
		});
	}

	// Automation WebSocket Message Handlers
	handleAutomationSaveResult(data) {
		if (data.success) {
			this.showToast(data.message, 'success');
			// Refresh the automations list
			this.loadSavedAutomations();
		} else {
			this.showToast(data.message, 'error');
		}
	}

	handleAutomationExecuteResult(data) {
		if (data.success) {
			this.showToast(`Automation completed successfully in ${data.duration}s`, 'success');
		} else {
			this.showToast(data.message, 'error');
		}
		
		// Update any running automation indicators
		this.isAutomationRunning = false;
		
		// Refresh lists to show updated stats
		this.loadSavedAutomations();
		if (this.currentTab === 'automations') {
			this.loadScheduledAutomations();
		}
	}

	handleAutomationStatus(data) {
		// Show status updates for automation execution
		switch (data.status) {
			case 'starting':
				this.showToast(data.message, 'info');
				this.isAutomationRunning = true;
				break;
			case 'running':
				// Could show progress if needed
				break;
			case 'step_completed':
				// Could show step completion status
				break;
			case 'completed':
				this.showToast(data.message, 'success');
				this.isAutomationRunning = false;
				break;
			case 'failed':
			case 'error':
				this.showToast(data.message, 'error');
				this.isAutomationRunning = false;
				break;
		}
	}

	// Context Bucket Methods
	setupContextBucket() {
		// Toggle button
		const toggleBtn = document.getElementById('toggle-context-bucket');
		if (toggleBtn) {
			toggleBtn.addEventListener('click', () => this.toggleContextBucket());
		}

		// Action buttons
		document.getElementById('add-context-btn')?.addEventListener('click', () => this.showAddContextModal());
		document.getElementById('clear-context-btn')?.addEventListener('click', () => this.clearContextBucket());
		document.getElementById('export-context-btn')?.addEventListener('click', () => this.exportContextBucket());
		document.getElementById('import-context-btn')?.addEventListener('click', () => this.showImportContextModal());

		// Load initial context items
		this.loadContextItems();
	}

	toggleContextBucket() {
		const content = document.getElementById('context-bucket-content');
		const toggleBtn = document.getElementById('toggle-context-bucket');
		const icon = toggleBtn.querySelector('i');

		if (content.classList.contains('collapsed')) {
			content.classList.remove('collapsed');
			icon.classList.remove('fa-chevron-right');
			icon.classList.add('fa-chevron-down');
		} else {
			content.classList.add('collapsed');
			icon.classList.remove('fa-chevron-down');
			icon.classList.add('fa-chevron-right');
		}
	}

	async loadContextItems() {
		try {
			const response = await fetch(`${this.apiBase}/api/context-bucket/items`);
			const data = await response.json();
			
			this.renderContextItems(data.items || []);
			this.updateContextStats(data.stats || {});
		} catch (error) {
			console.error('Failed to load context items:', error);
		}
	}

	renderContextItems(items) {
		const container = document.getElementById('context-bucket-items');
		
		if (items.length === 0) {
			container.innerHTML = `
				<div class="empty-context">
					<i class="fas fa-folder-open"></i>
					<p>No context items yet. Add documents, instructions, or references.</p>
				</div>
			`;
			return;
		}

		container.innerHTML = items.map(item => `
			<div class="context-item" data-item-id="${item.id}">
				<div class="context-item-header">
					<div>
						<span class="context-item-type">${item.type}</span>
						<span class="context-item-title">${this.escapeHtml(item.title)}</span>
					</div>
					<div class="context-item-actions">
						<span class="context-item-priority priority-${item.priority}">${item.priority}</span>
						<button class="btn-icon-small" onclick="app.editContextItem('${item.id}')" title="Edit">
							<i class="fas fa-edit"></i>
						</button>
						<button class="btn-icon-small" onclick="app.deleteContextItem('${item.id}')" title="Delete">
							<i class="fas fa-trash"></i>
						</button>
					</div>
				</div>
				<div class="context-item-content">
					${this.escapeHtml(item.content).substring(0, 150)}${item.content.length > 150 ? '...' : ''}
				</div>
				${item.tags && item.tags.length > 0 ? `
					<div class="context-item-tags">
						${item.tags.map(tag => `<span class="context-tag">${this.escapeHtml(tag)}</span>`).join('')}
					</div>
				` : ''}
			</div>
		`).join('');
	}

	updateContextStats(stats) {
		const usedTokens = stats.total_tokens || 0;
		const maxTokens = stats.max_tokens || 8000;
		const percentage = (usedTokens / maxTokens) * 100;

		document.getElementById('context-tokens-used').textContent = usedTokens;
		document.getElementById('context-tokens-max').textContent = maxTokens;
		
		const progressBar = document.getElementById('token-progress-bar');
		progressBar.style.width = `${percentage}%`;
		
		// Update color based on usage
		progressBar.classList.remove('warning', 'danger');
		if (percentage > 90) {
			progressBar.classList.add('danger');
		} else if (percentage > 70) {
			progressBar.classList.add('warning');
		}
	}

	showAddContextModal() {
		const modal = document.getElementById('context-add-modal');
		modal.classList.remove('hidden');
		
		// Clear form
		document.getElementById('context-type').value = 'document';
		document.getElementById('context-title').value = '';
		document.getElementById('context-content').value = '';
		document.getElementById('context-priority').value = 'medium';
		document.getElementById('context-tags').value = '';
		document.getElementById('context-source').value = '';
	}

	async saveContextItem() {
		const type = document.getElementById('context-type').value;
		const title = document.getElementById('context-title').value.trim();
		const content = document.getElementById('context-content').value.trim();
		const priority = document.getElementById('context-priority').value;
		const tags = document.getElementById('context-tags').value
			.split(',')
			.map(tag => tag.trim())
			.filter(tag => tag.length > 0);
		const source = document.getElementById('context-source').value.trim();

		if (!title || !content) {
			this.showToast('Title and content are required', 'error');
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/context-bucket/add`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					type,
					title,
					content,
					priority,
					tags,
					source: source || undefined
				})
			});

			const result = await response.json();
			
			if (result.success) {
				this.showToast('Context item added successfully', 'success');
				this.closeContextModal();
				this.loadContextItems();
			} else {
				this.showToast(result.message || 'Failed to add context item', 'error');
			}
		} catch (error) {
			console.error('Failed to save context item:', error);
			this.showToast('Failed to save context item', 'error');
		}
	}

	closeContextModal() {
		document.getElementById('context-add-modal').classList.add('hidden');
	}

	async deleteContextItem(itemId) {
		if (!confirm('Are you sure you want to delete this context item?')) {
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/context-bucket/items/${itemId}`, {
				method: 'DELETE'
			});

			const result = await response.json();
			
			if (result.success) {
				this.showToast('Context item deleted', 'success');
				this.loadContextItems();
			} else {
				this.showToast('Failed to delete context item', 'error');
			}
		} catch (error) {
			console.error('Failed to delete context item:', error);
			this.showToast('Failed to delete context item', 'error');
		}
	}

	async clearContextBucket() {
		if (!confirm('Are you sure you want to clear all context items?')) {
			return;
		}

		try {
			const response = await fetch(`${this.apiBase}/api/context-bucket/clear`, {
				method: 'POST'
			});

			const result = await response.json();
			
			if (result.success) {
				this.showToast('Context bucket cleared', 'success');
				this.loadContextItems();
			} else {
				this.showToast('Failed to clear context bucket', 'error');
			}
		} catch (error) {
			console.error('Failed to clear context bucket:', error);
			this.showToast('Failed to clear context bucket', 'error');
		}
	}

	async exportContextBucket() {
		try {
			const response = await fetch(`${this.apiBase}/api/context-bucket/export`);
			const data = await response.json();
			
			// Create and download JSON file
			const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `context-bucket-${new Date().toISOString().split('T')[0]}.json`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
			
			this.showToast('Context bucket exported', 'success');
		} catch (error) {
			console.error('Failed to export context bucket:', error);
			this.showToast('Failed to export context bucket', 'error');
		}
	}

	showImportContextModal() {
		const input = document.createElement('input');
		input.type = 'file';
		input.accept = '.json';
		
		input.onchange = async (e) => {
			const file = e.target.files[0];
			if (!file) return;
			
			try {
				const text = await file.text();
				const data = JSON.parse(text);
				
				const response = await fetch(`${this.apiBase}/api/context-bucket/import`, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(data)
				});
				
				const result = await response.json();
				
				if (result.success) {
					this.showToast('Context bucket imported successfully', 'success');
					this.loadContextItems();
				} else {
					this.showToast('Failed to import context bucket', 'error');
				}
			} catch (error) {
				console.error('Failed to import context bucket:', error);
				this.showToast('Invalid context bucket file', 'error');
			}
		};
		
		input.click();
	}

	// Helper method for editing context items (placeholder for future implementation)
	editContextItem(itemId) {
		// TODO: Implement edit functionality
		this.showToast('Edit functionality coming soon', 'info');
	}
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
	window.app = new FFTerminalApp();
});

// Global functions for context modal
window.closeContextModal = function() {
	window.app.closeContextModal();
};

window.saveContextItem = function() {
	window.app.saveContextItem();
};