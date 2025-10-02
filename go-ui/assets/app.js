/**
 * FF-Terminal:Desktop_ver - Elegant Interface JavaScript Application
 * Modern vanilla JavaScript implementation with component architecture
 * Ported from web interface with Wails integration adaptations
 */

class FFTerminalApp {
	constructor() {
		// Remove hardcoded URLs - will be set by Wails backend
		this.apiBase = ''; // Will be set by Go backend
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
			console.log('Starting app initialization...');
			await this.showLoadingScreen();
			console.log('Loading screen shown');

			await this.initializeApp();
			console.log('App initialized');

			await this.setupEventListeners();
			console.log('Event listeners setup');

			await this.connectWailsBackend();
			console.log('Backend connected');

			// Try to load data, but don't fail if backend has issues
			try {
				await Promise.all([
					this.loadProviders(),
					this.loadSessions(),
					this.loadAutomationTemplates(),
					this.loadSavedAutomations()
				]);
				console.log('Data loaded successfully');
			} catch (error) {
				console.warn('Some data loading failed, continuing anyway:', error);
				// Set up mock data if backend is having issues
				this.setupMockData();
			}

			await this.setupAutomationEventListeners();
			console.log('Automation listeners setup');

			await this.hideLoadingScreen();
			console.log('Loading screen hidden - App ready!');
		} catch (error) {
			console.error('Failed to initialize app:', error);
			this.showToast('Failed to initialize application: ' + error.message, 'error');
			// Still hide loading screen even if there's an error
			await this.hideLoadingScreen();
		}
	}

	// Setup mock data for demonstration if backend is not available
	setupMockData() {
		console.log('Setting up mock data for demonstration...');

		// Mock providers
		this.providers = {
			"OpenAI": {
				available: true,
				models: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
				api_key_required: true
			},
			"Anthropic": {
				available: true,
				models: ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
				api_key_required: true
			},
			"OpenRouter": {
				available: true,
				models: ["meta-llama/llama-3.2-3b-instruct:free"],
				api_key_required: true
			}
		};

		// Mock sessions
		this.sessions = [];

		// Mock automation templates
		this.automationTemplates = {
			"Quick Tasks": [],
			"Multi-Step Workflows": [],
			"Productivity Automations": []
		};

		// Mock saved automations
		this.savedAutomations = [];

		console.log('Mock data setup complete');
	}

	async showLoadingScreen() {
		return new Promise(resolve => {
			setTimeout(resolve, 200); // Short loading time for demo
		});
	}

	async hideLoadingScreen() {
		const loadingScreen = document.getElementById('loading-screen');
		const mainApp = document.getElementById('main-app');

		if (loadingScreen && mainApp) {
			loadingScreen.style.opacity = '0';
			setTimeout(() => {
				loadingScreen.classList.add('hidden');
				mainApp.classList.remove('hidden');
			}, 500);
		}
	}

	async initializeApp() {
		// Set up initial UI state
		this.updateConnectionStatus(false);
		this.switchTab('chat');
	}

	// Connect to Wails backend instead of direct WebSocket
	async connectWailsBackend() {
		try {
			// Test backend connection
			if (window.go && window.go.ui && window.go.ui.App) {
				// Get backend URL from Go
				this.apiBase = await window.go.ui.App.GetBackendURL();
				console.log('Connected to Wails backend:', this.apiBase);

				// Set up WebSocket event handlers through Wails
				this.setupWailsWebSocket();
				this.updateConnectionStatus(true);
			} else {
				console.warn('Wails backend not available, using offline mode');
				// Set up offline mode
				this.apiBase = 'http://localhost:8080';
				this.updateConnectionStatus(false);
				this.showToast('Backend unavailable - running in offline mode', 'warning');
			}
		} catch (error) {
			console.error('Failed to connect to Wails backend:', error);
			// Continue in offline mode
			this.apiBase = 'http://localhost:8080';
			this.updateConnectionStatus(false);
			this.showToast('Backend connection failed - running in offline mode', 'warning');
		}
	}

	// Setup WebSocket event handlers through Wails backend
	setupWailsWebSocket() {
		try {
			// Register WebSocket event handlers through Wails
			if (window.runtime && window.runtime.EventsOn) {
				window.runtime.EventsOn('backend-message', (message) => {
					try {
						const data = JSON.parse(message);
						this.handleWebSocketMessage(data);
					} catch (e) {
						console.error('Failed to parse WebSocket message:', e);
					}
				});

				window.runtime.EventsOn('connection-success', (message) => {
					console.log('WebSocket connected via Wails:', message);
					this.updateConnectionStatus(true);
				});

				window.runtime.EventsOn('connection-error', (error) => {
					console.error('WebSocket connection error:', error);
					this.updateConnectionStatus(false);
				});

				console.log('WebSocket event handlers registered');
			}
		} catch (error) {
			console.error('Failed to setup Wails WebSocket:', error);
			throw error;
		}
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
		if (chatInput) {
			chatInput.addEventListener('keypress', (e) => {
				if (e.key === 'Enter' && !e.shiftKey) {
					e.preventDefault();
					this.sendChatMessage();
				}
			});
		}

		// Send button
		if (sendBtn) {
			sendBtn.addEventListener('click', () => this.sendChatMessage());
		}

		// Stop button
		if (stopBtn) {
			stopBtn.addEventListener('click', () => this.stopChat());
		}

		// Interrupt button
		if (interruptBtn) {
			interruptBtn.addEventListener('click', () => this.interruptChat());
		}

		// Redirect button
		if (redirectBtn) {
			redirectBtn.addEventListener('click', () => this.redirectChat());
		}

		// Clear chat
		if (clearBtn) {
			clearBtn.addEventListener('click', () => this.clearChat());
		}

		// Save chat
		if (saveBtn) {
			saveBtn.addEventListener('click', () => this.showSaveChatModal());
		}

		// Provider/model changes
		const chatProvider = document.getElementById('chat-provider');
		if (chatProvider) {
			chatProvider.addEventListener('change', (e) => {
				this.updateChatModels(e.target.value);
			});
		}
	}

	setupAgentListeners() {
		const runBtn = document.getElementById('run-agent-btn');
		const stopBtn = document.getElementById('stop-agent-btn');
		const refineBtn = document.getElementById('refine-task-btn');
		const clearTerminalBtn = document.getElementById('clear-terminal-btn');
		const saveAgentBtn = document.getElementById('save-agent-automation-btn');
		const manageContextBtn = document.getElementById('manage-agent-context-btn');

		if (runBtn) runBtn.addEventListener('click', () => this.runAgent());
		if (stopBtn) stopBtn.addEventListener('click', () => this.stopAgent());
		if (refineBtn) refineBtn.addEventListener('click', () => this.refineTask());
		if (clearTerminalBtn) clearTerminalBtn.addEventListener('click', () => this.clearTerminal());
		if (saveAgentBtn) saveAgentBtn.addEventListener('click', () => this.saveAgentAsAutomation());
		if (manageContextBtn) manageContextBtn.addEventListener('click', () => this.openAgentContextModal());

		// Provider changes
		const agentProvider = document.getElementById('agent-provider');
		if (agentProvider) {
			agentProvider.addEventListener('change', (e) => {
				this.updateAgentModels(e.target.value);
			});
		}

		// Context session changes
		const agentContextSession = document.getElementById('agent-context-session');
		if (agentContextSession) {
			agentContextSession.addEventListener('input', () => {
				this.updateAgentContextSummary();
			});
		}
	}

	setupSessionsListeners() {
		const refreshBtn = document.getElementById('refresh-sessions-btn');
		const saveSessionBtn = document.getElementById('save-session-btn');

		if (refreshBtn) {
			refreshBtn.addEventListener('click', () => this.loadSessions());
		}
		if (saveSessionBtn) {
			saveSessionBtn.addEventListener('click', () => this.saveCurrentSession());
		}
	}

	setupProvidersListeners() {
		const refreshBtn = document.getElementById('refresh-providers-btn');
		if (refreshBtn) {
			refreshBtn.addEventListener('click', () => this.loadProviders());
		}
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

	updateConnectionStatus(connected) {
		const statusEl = document.getElementById('connection-status');
		if (!statusEl) return;

		const iconEl = statusEl.querySelector('i');
		const textEl = statusEl.querySelector('span');

		if (connected) {
			statusEl.classList.remove('disconnected');
			if (textEl) textEl.textContent = 'Connected';
		} else {
			statusEl.classList.add('disconnected');
			if (textEl) textEl.textContent = 'Disconnected';
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
		const tabContent = document.getElementById(`${tabName}-tab`);
		if (tabContent) {
			tabContent.classList.add('active');
		}

		this.currentTab = tabName;

		// Load tab-specific data
		if (tabName === 'sessions') {
			this.loadSessions();
		} else if (tabName === 'providers') {
			this.loadProviders();
		}
	}

	// Chat Functionality - adapted for Wails
	async sendChatMessage() {
		if (this.isChatRunning) return;

		const input = document.getElementById('chat-input');
		if (!input) return;

		const message = input.value.trim();

		if (!message) return;

		const provider = document.getElementById('chat-provider')?.value;
		const model = document.getElementById('chat-model')?.value;
		const apiKey = document.getElementById('chat-api-key')?.value;

		// Add user message to chat
		this.addChatMessage(message, 'user');
		input.value = '';

		// Update UI state
		this.isChatRunning = true;
		this.updateChatUI(true);

		// Show typing indicator
		this.currentChatTypingId = this.addTypingIndicator();

		// Get custom system message
		const customSystemMessage = document.getElementById('chat-custom-system')?.value.trim() || '';

		// Send via Wails backend instead of direct WebSocket
		try {
			if (window.go && window.go.ui && window.go.ui.App) {
				await window.go.ui.App.SendTask({
					type: 'chat',
					message: message,
					provider: provider,
					model: model,
					api_key: apiKey,
					custom_system_message: customSystemMessage
				});

				// Update conversation history with user message
				this.conversationHistory.push({
					type: 'user',
					content: message,
					timestamp: new Date().toISOString(),
					success: true
				});
			} else {
				throw new Error('Wails backend not available');
			}
		} catch (error) {
			console.error('Failed to send chat message:', error);
			this.showToast('Failed to send message', 'error');
			this.removeTypingIndicator(this.currentChatTypingId);
			this.isChatRunning = false;
			this.updateChatUI(false);
		}
	}

	addChatMessage(content, sender, success = true) {
		const messagesContainer = document.getElementById('chat-messages');
		if (!messagesContainer) return;

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
		if (!messagesContainer) return null;

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
		if (!messagesContainer) return;

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

		// Send stop command via Wails backend
		if (window.go && window.go.ui && window.go.ui.App) {
			window.go.ui.App.StopTask().catch(error => {
				console.error('Failed to stop chat:', error);
			});
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

		// Send interrupt command via Wails backend
		if (window.go && window.go.ui && window.go.ui.App) {
			window.go.ui.App.InterruptChat().catch(error => {
				console.error('Failed to interrupt chat:', error);
			});
		}

		this.showToast('Chat interrupted', 'info');
	}

	redirectChat() {
		if (!this.isChatRunning) return;

		const newTask = prompt('Enter the new task to redirect to:');
		if (!newTask || !newTask.trim()) return;

		// Send redirect command via Wails backend
		if (window.go && window.go.ui && window.go.ui.App) {
			window.go.ui.App.RedirectChat(newTask.trim()).catch(error => {
				console.error('Failed to redirect chat:', error);
			});
		}

		this.showToast(`Redirecting to: ${newTask}`, 'info');
	}

	updateChatUI(running) {
		const sendBtn = document.getElementById('send-chat-btn');
		const stopBtn = document.getElementById('stop-chat-btn');
		const interruptBtn = document.getElementById('interrupt-chat-btn');
		const redirectBtn = document.getElementById('redirect-chat-btn');
		const chatInput = document.getElementById('chat-input');

		if (sendBtn) {
			sendBtn.disabled = running;
			sendBtn.innerHTML = running ? '<i class="fas fa-spinner fa-spin"></i> Processing...' : '<i class="fas fa-paper-plane"></i> Send';
		}
		if (stopBtn) stopBtn.disabled = !running;
		if (interruptBtn) interruptBtn.disabled = !running;
		if (redirectBtn) redirectBtn.disabled = !running;
		if (chatInput) chatInput.disabled = running;
	}

	// WebSocket message handling - adapted for Wails events
	handleWebSocketMessage(message) {
		switch (message.type) {
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
			case 'stream_update':
				this.handleAgentStreamUpdate(message.data);
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
			case 'pong':
				// Heartbeat response
				break;
			default:
				console.log('Unknown message type:', message);
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

	// Automation Templates - adapted for Wails
	async loadAutomationTemplates() {
		try {
			if (window.go && window.go.ui && window.go.ui.App) {
				this.automationTemplates = await window.go.ui.App.GetAutomationTemplates();
				this.renderAutomationTemplates();
			}
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
		const activeTab = document.querySelector(`[data-category="${category}"]`);
		if (activeTab) {
			activeTab.classList.add('active');
		}

		// Update current category and render
		this.currentAutomationCategory = category;
		this.renderAutomationTemplates();
	}

	renderAutomationTemplates() {
		const container = document.getElementById('automation-list');
		if (!container) return;

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
		const chatInput = document.getElementById('chat-input');
		if (chatInput) {
			chatInput.value = prompt;
			this.sendChatMessage();
		}
	}

	showAutomationContextMenu(event, template) {
		// For now, just show a toast about saving (can be enhanced later)
		this.showToast(`"${template.name}" automation available for quick access`, 'info');
	}

	// Agent Functionality - adapted for Wails
	async runAgent() {
		if (this.isAgentRunning) return;

		const task = document.getElementById('agent-task')?.value.trim();
		if (!task) {
			this.showToast('Please enter a task description', 'warning');
			return;
		}

		const maxSteps = parseInt(document.getElementById('max-steps')?.value || 10);
		const maxActions = parseInt(document.getElementById('max-actions')?.value || 20);
		const provider = document.getElementById('agent-provider')?.value;
		const model = document.getElementById('agent-model')?.value;
		const apiKey = document.getElementById('agent-api-key')?.value;

		// Reset execution tracking for new run
		this.currentAgentExecution = null;
		const saveBtn = document.getElementById('save-agent-automation-btn');
		if (saveBtn) saveBtn.disabled = true;

		this.isAgentRunning = true;
		this.updateAgentUI(true);

		// Get custom system message and context session
		const customSystemMessage = document.getElementById('agent-custom-system')?.value.trim() || '';
		const contextSessionId = document.getElementById('agent-context-session')?.value.trim() || 'agent_session';

		// Send task via Wails backend
		try {
			if (window.go && window.go.ui && window.go.ui.App) {
				await window.go.ui.App.SendTask({
					type: 'agent',
					message: task,
					max_steps: maxSteps,
					max_actions: maxActions,
					llm_provider: provider,
					llm_model: model,
					api_key: apiKey,
					custom_system_message: customSystemMessage,
					context_session_id: contextSessionId
				});
			} else {
				throw new Error('Wails backend not available');
			}
		} catch (error) {
			console.error('Failed to run agent:', error);
			this.showToast('Failed to start agent', 'error');
			this.isAgentRunning = false;
			this.updateAgentUI(false);
		}
	}

	stopAgent() {
		if (!this.isAgentRunning) return;

		// Send stop command via Wails backend
		if (window.go && window.go.ui && window.go.ui.App) {
			window.go.ui.App.StopTask().catch(error => {
				console.error('Failed to stop agent:', error);
			});
		}

		this.isAgentRunning = false;
		this.updateAgentUI(false);
	}

	handleAgentStreamUpdate(data) {
		const { status, message, step, max_steps, final_result } = data;

		// Update execution status
		const statusEl = document.getElementById('execution-status');
		if (statusEl) {
			const statusText = statusEl.querySelector('.status-text');
			if (statusText) {
				statusEl.className = `execution-status ${status}`;
				statusText.textContent = this.capitalizeFirst(status);
			}
		}

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
				task: document.getElementById('agent-task')?.value || '',
				status: status,
				steps: [],
				provider: document.getElementById('agent-provider')?.value || '',
				model: document.getElementById('agent-model')?.value || '',
				custom_system: document.getElementById('agent-custom-system')?.value || '',
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
			if (saveBtn) saveBtn.disabled = status !== 'completed';

			const toastType = status === 'completed' ? 'success' : (status === 'stopped' ? 'warning' : 'error');
			this.showToast(message || `Agent ${status}`, toastType);
		}
	}

	updateAgentUI(running) {
		const runBtn = document.getElementById('run-agent-btn');
		const stopBtn = document.getElementById('stop-agent-btn');
		const progressSection = document.getElementById('agent-progress');

		if (runBtn) runBtn.disabled = running;
		if (stopBtn) stopBtn.disabled = !running;

		if (progressSection) {
			if (running) {
				progressSection.classList.remove('hidden');
			} else {
				progressSection.classList.add('hidden');
			}
		}
	}

	updateAgentProgress(step, maxSteps, message) {
		const progressText = document.getElementById('progress-text');
		const progressStep = document.getElementById('progress-step');
		const progressFill = document.getElementById('progress-fill');

		if (progressText) progressText.textContent = message || `Processing step ${step}...`;
		if (progressStep) progressStep.textContent = `Step ${step} / ${maxSteps}`;

		if (progressFill) {
			const percentage = (step / maxSteps) * 100;
			progressFill.style.width = `${percentage}%`;
		}
	}

	addTerminalLine(text, type = 'info') {
		const terminalContent = document.getElementById('terminal-content');
		if (!terminalContent) return;

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
		if (terminalContent) {
			terminalContent.innerHTML = '<p class="terminal-ready">Ready to execute agent tasks...</p>';
		}
	}

	showAgentResult(result) {
		const resultSection = document.getElementById('agent-result');
		const resultContent = document.getElementById('result-content');

		if (resultSection && resultContent) {
			resultContent.textContent = result;
			resultSection.classList.remove('hidden');
		}
	}

	async refineTask() {
		const taskInput = document.getElementById('agent-task');
		if (!taskInput) return;

		const originalTask = taskInput.value.trim();

		if (!originalTask) {
			this.showToast('Please enter a task first', 'warning');
			return;
		}

		const provider = document.getElementById('agent-provider')?.value;
		const model = document.getElementById('agent-model')?.value;
		const apiKey = document.getElementById('agent-api-key')?.value;

		const refineBtn = document.getElementById('refine-task-btn');
		if (!refineBtn) return;

		const originalText = refineBtn.innerHTML;
		refineBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refining...';
		refineBtn.disabled = true;

		try {
			// Use Wails backend for prompt refinement
			if (window.go && window.go.ui && window.go.ui.App) {
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

				const refinedPrompt = await window.go.ui.App.RefinePrompt(originalTask, provider, model, systemMessage);

				if (refinedPrompt) {
					taskInput.value = refinedPrompt;
					this.showToast('Task refined successfully', 'success');
				} else {
					this.showToast('Failed to refine task', 'error');
				}
			} else {
				throw new Error('Wails backend not available');
			}

		} catch (error) {
			console.error('Refine task error:', error);
			this.showToast('Failed to refine task', 'error');
		} finally {
			refineBtn.innerHTML = originalText;
			refineBtn.disabled = false;
		}
	}

	// Provider Management - adapted for Wails
	async loadProviders() {
		try {
			console.log('Loading providers...');
			if (window.go && window.go.ui && window.go.ui.App) {
				console.log('Calling GetProviders()...');
				const providersData = await window.go.ui.App.GetProviders();
				console.log('Received providers data:', providersData);

				// Convert array to object for easier lookup
				this.providers = {};
				if (Array.isArray(providersData)) {
					providersData.forEach(provider => {
						this.providers[provider.Name] = {
							available: provider.Available,
							models: provider.Models || [],
							api_key_required: true
						};
					});
				}

				console.log('Processed providers:', this.providers);
				this.renderProviders();
				this.updateProviderSelects();
				console.log('Providers loaded successfully');
			} else {
				console.log('Wails bindings not available, using mock providers');
				// Use mock providers if bindings not available
				this.providers = {
					"OpenAI": {
						available: true,
						models: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-4-turbo"],
						api_key_required: true
					},
					"Anthropic": {
						available: true,
						models: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
						api_key_required: true
					},
					"Google": {
						available: true,
						models: ["gemini-1.5-pro", "gemini-1.5-flash"],
						api_key_required: true
					},
					"DeepSeek": {
						available: true,
						models: ["deepseek-chat", "deepseek-reasoner"],
						api_key_required: true
					}
				};
				this.renderProviders();
				this.updateProviderSelects();
				console.log('Mock providers loaded successfully');
			}
		} catch (error) {
			console.error('Failed to load providers:', error);
			console.error('Error details:', error.message, error.stack);
			console.log('Wails bindings available:', !!window.go, !!window.go.ui, !!window.go.ui.App);
			console.log('App Go bindings:', Object.keys(window.go?.ui?.App || {}));

			// Use mock providers as fallback
			this.providers = {
				"OpenAI": {
					available: true,
					models: ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
					api_key_required: true
				},
				"Anthropic": {
					available: false,
					models: ["claude-3-5-sonnet-20241022"],
					api_key_required: true
				},
				"Google": {
					available: false,
					models: ["gemini-1.5-pro", "gemini-1.5-flash"],
					api_key_required: true
				}
			};
			this.renderProviders();
			this.updateProviderSelects();
			console.log('Fallback providers loaded');
			this.showToast('Using demo providers - configure API keys in settings', 'info');
		}
	}

	renderProviders() {
		const container = document.getElementById('providers-grid');
		if (!container) return;

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
			// Use Wails backend for provider testing
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.TestProvider(providerName, model, apiKey);
				const toastType = result.status === 'success' ? 'success' : 'error';
				this.showToast(result.message || result.error, toastType);
			} else {
				throw new Error('Wails backend not available');
			}

		} catch (error) {
			console.error('Provider test error:', error);
			this.showToast('Failed to test provider', 'error');
		}
	}

	updateProviderSelects() {
		const chatProvider = document.getElementById('chat-provider');
		const agentProvider = document.getElementById('agent-provider');

		if (!chatProvider || !agentProvider) return;

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
		if (modelSelect) {
			this.updateModelSelect(modelSelect, provider);
		}
	}

	updateAgentModels(provider) {
		const modelSelect = document.getElementById('agent-model');
		if (modelSelect) {
			this.updateModelSelect(modelSelect, provider);
		}
	}

	updateModelSelect(selectElement, provider) {
		if (!selectElement) return;

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

	// Session Management - adapted for Wails
	async loadSessions() {
		try {
			if (window.go && window.go.ui && window.go.ui.App) {
				this.sessions = await window.go.ui.App.GetSessions();
				this.renderSessions();
			}
		} catch (error) {
			console.error('Failed to load sessions:', error);
			this.showToast('Failed to load sessions', 'error');
		}
	}

	renderSessions() {
		const container = document.getElementById('sessions-container');
		if (!container) return;

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
			// Use Wails backend to load session
			if (window.go && window.go.ui && window.go.ui.App) {
				const sessionData = await window.go.ui.App.LoadSession(sessionName);

				// Clear current chat
				this.clearChat();

				// Load messages
				this.conversationHistory = sessionData.conversation_history || [];
				if (sessionData.conversation_history) {
					sessionData.conversation_history.forEach(msg => {
						this.addChatMessage(msg.content, msg.role, true);
					});
				}

				// Switch to chat tab
				this.switchTab('chat');
				this.showToast(`Loaded session: ${sessionName}`, 'success');
			} else {
				throw new Error('Wails backend not available');
			}

		} catch (error) {
			console.error('Failed to load session:', error);
			this.showToast('Failed to load session', 'error');
		}
	}

	async deleteSession(sessionName) {
		if (!confirm(`Are you sure you want to delete session "${sessionName}"?`)) {
			return;
		}

		// This would need to be implemented in the Go backend
		this.showToast('Session deletion not yet implemented', 'info');
	}

	async saveCurrentSession() {
		const sessionNameInput = document.getElementById('session-name-input');
		if (!sessionNameInput) return;

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
			// Use Wails backend to save session
			if (window.go && window.go.ui && window.go.ui.App) {
				const session = {
					name: sessionName,
					timestamp: new Date().toISOString(),
					message_count: this.conversationHistory.length,
					success_count: this.conversationHistory.filter(m => m.success !== false).length,
					failure_count: this.conversationHistory.filter(m => m.success === false).length,
					conversation_history: this.conversationHistory
				};

				await window.go.ui.App.SaveSession(session);

				sessionNameInput.value = '';
				this.showToast('Session saved successfully', 'success');
				this.loadSessions(); // Refresh list
			} else {
				throw new Error('Wails backend not available');
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
			if (input) {
				input.focus();
				input.value = `Chat ${new Date().toLocaleDateString()}`;
			}
		}, 300);
	}

	// Utility Functions
	showToast(message, type = 'info') {
		const container = document.getElementById('toast-container');
		if (!container) return;

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

	// Automation Management Methods - adapted for Wails
	async loadSavedAutomations() {
		try {
			if (window.go && window.go.ui && window.go.ui.App) {
				this.savedAutomations = await window.go.ui.App.GetAutomations();
				this.renderSavedAutomations();
			}
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

			// Send save automation message via Wails backend
			try {
				if (window.go && window.go.ui && window.go.ui.App) {
					const contextSessionId = document.getElementById('agent-context-session')?.value || 'agent_session';

					const automation = {
						name,
						description,
						task: this.currentAgentExecution.task,
						category,
						tags: tags.split(',').map(t => t.trim()).filter(t => t),
						custom_system_message: this.currentAgentExecution.custom_system,
						llm_provider: this.currentAgentExecution.provider,
						llm_model: this.currentAgentExecution.model,
						context_session_id: contextSessionId,
						execution_data: this.currentAgentExecution
					};

					await window.go.ui.App.SaveAutomation(automation);

					modal.remove();
					this.showToast('Saving automation...', 'info');
					this.loadSavedAutomations(); // Refresh list
				} else {
					throw new Error('Wails backend not available');
				}
			} catch (error) {
				console.error('Failed to save automation:', error);
				this.showToast('Failed to save automation', 'error');
			}
		});
	}

	async executeAutomation(automationId, parameters = {}) {
		// Execute automation via Wails backend
		try {
			if (window.go && window.go.ui && window.go.ui.App) {
				await window.go.ui.App.ExecuteAutomation(automationId, parameters);
			} else {
				throw new Error('Wails backend not available');
			}
		} catch (error) {
			console.error('Failed to execute automation:', error);
			this.showToast('Failed to execute automation', 'error');
		}
	}

	async deleteAutomation(automationId) {
		if (!confirm('Are you sure you want to delete this automation?')) {
			return;
		}

		try {
			// This would need to be implemented in the Go backend
			this.showToast('Automation deletion not yet implemented', 'info');
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
				// Use Wails backend for scheduling
				if (window.go && window.go.ui && window.go.ui.App) {
					await window.go.ui.App.ScheduleAutomation(automationId, cronExpression, true);

					this.showToast('Automation scheduled successfully', 'success');
					modal.remove();
					this.loadScheduledAutomations(); // Refresh list
				} else {
					throw new Error('Wails backend not available');
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
						<span class="success-count">${automation.success_count || 0} successes</span>
						<span class="failure-count">${automation.failure_count || 0} failures</span>
					</div>
				</div>
				<p class="automation-description">${automation.description || 'No description'}</p>
				<div class="automation-meta">
					<span class="category">${automation.category || 'Uncategorized'}</span>
					<span class="steps">${automation.steps_count || 0} steps</span>
					<span class="updated">${new Date(automation.updated_at || automation.created_at).toLocaleDateString()}</span>
				</div>
				<div class="automation-actions">
					<button class="run-button" onclick="app.executeAutomation('${automation.id}')">Run</button>
					<button class="schedule-button" onclick="app.scheduleAutomation('${automation.id}')">Schedule</button>
					<button class="delete-button" onclick="app.deleteAutomation('${automation.id}')">Delete</button>
				</div>
			</div>
		`).join('');
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
			if (window.go && window.go.ui && window.go.ui.App) {
				this.scheduledAutomations = await window.go.ui.App.GetScheduledAutomations();
				this.renderScheduledAutomations();
			}
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
						<span class="next-run">Next: ${automation.next_execution ? new Date(automation.next_execution).toLocaleString() : 'Not scheduled'}</span>
					</div>
				</div>
				<p class="automation-description">${automation.description || 'No description'}</p>
				<div class="automation-meta">
					<span class="schedules">${automation.schedules?.length || 0} schedule(s)</span>
					<span class="success-count">${automation.success_count || 0} successes</span>
					<span class="failure-count">${automation.failure_count || 0} failures</span>
				</div>
				<div class="automation-actions">
					<button class="run-button" onclick="app.executeAutomation('${automation.automation_id || automation.id}')">Run Now</button>
					<button class="delete-button" onclick="app.unscheduleAutomation('${automation.automation_id || automation.id}')">Unschedule</button>
				</div>
			</div>
		`).join('');
	}

	async unscheduleAutomation(automationId) {
		if (!confirm('Are you sure you want to unschedule this automation?')) {
			return;
		}

		try {
			// This would need to be implemented in the Go backend
			this.showToast('Automation unscheduling not yet implemented', 'info');
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
			this.showToast(`Automation completed successfully in ${data.duration || 0}s`, 'success');
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

	// Context Bucket Methods - adapted for Wails
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
		if (!content || !toggleBtn) return;

		const icon = toggleBtn.querySelector('i');
		if (!icon) return;

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
			// Use Wails backend to load context items
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.GetContextBucketItems();
				this.renderContextItems(result.items || []);
				this.updateContextStats(result.stats || {});
			}
		} catch (error) {
			console.error('Failed to load context items:', error);
		}
	}

	renderContextItems(items) {
		const container = document.getElementById('context-bucket-items');
		if (!container) return;

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

		const tokensUsedEl = document.getElementById('context-tokens-used');
		const tokensMaxEl = document.getElementById('context-tokens-max');
		const progressBar = document.getElementById('token-progress-bar');

		if (tokensUsedEl) tokensUsedEl.textContent = usedTokens;
		if (tokensMaxEl) tokensMaxEl.textContent = maxTokens;

		if (progressBar) {
			progressBar.style.width = `${percentage}%`;

			// Update color based on usage
			progressBar.classList.remove('warning', 'danger');
			if (percentage > 90) {
				progressBar.classList.add('danger');
			} else if (percentage > 70) {
				progressBar.classList.add('warning');
			}
		}
	}

	openAgentContextModal() {
		// Set the current session ID for agent context
		const sessionId = document.getElementById('agent-context-session')?.value || 'agent_session';
		this.currentContextSession = sessionId;

		// Load context items for this session
		this.loadContextItems();

		// Show the context bucket sidebar
		const contextBucket = document.getElementById('context-bucket');
		if (contextBucket) {
			contextBucket.classList.remove('hidden');
		}

		// Update session ID display in sidebar
		const sessionDisplay = document.getElementById('context-session-id');
		if (sessionDisplay) {
			sessionDisplay.textContent = sessionId;
		}

		this.showToast(`Managing context for session: ${sessionId}`, 'info');

		// Update context summary
		this.updateAgentContextSummary();
	}

	async updateAgentContextSummary() {
		const sessionId = document.getElementById('agent-context-session')?.value || 'agent_session';

		try {
			// Use Wails backend to get context summary
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.GetContextBucketSummary();

				if (result.success) {
					const summary = result.summary;
					const countElement = document.querySelector('#agent-context-summary .context-count');
					const tokensElement = document.querySelector('#agent-context-summary .context-tokens');

					if (countElement) {
						countElement.textContent = `${summary.total_items} context items`;
					}
					if (tokensElement) {
						tokensElement.textContent = `${summary.total_tokens} tokens`;
					}
				}
			}
		} catch (error) {
			console.error('Failed to update agent context summary:', error);
		}
	}

	showAddContextModal() {
		const modal = document.getElementById('context-add-modal');
		if (modal) {
			modal.classList.remove('hidden');

			// Clear form
			const contextType = document.getElementById('context-type');
			const contextTitle = document.getElementById('context-title');
			const contextContent = document.getElementById('context-content');
			const contextPriority = document.getElementById('context-priority');
			const contextTags = document.getElementById('context-tags');
			const contextSource = document.getElementById('context-source');

			if (contextType) contextType.value = 'document';
			if (contextTitle) contextTitle.value = '';
			if (contextContent) contextContent.value = '';
			if (contextPriority) contextPriority.value = 'medium';
			if (contextTags) contextTags.value = '';
			if (contextSource) contextSource.value = '';
		}
	}

	async saveContextItem() {
		const type = document.getElementById('context-type')?.value || 'document';
		const title = document.getElementById('context-title')?.value.trim();
		const content = document.getElementById('context-content')?.value.trim();
		const priority = document.getElementById('context-priority')?.value || 'medium';
		const tags = document.getElementById('context-tags')?.value
			.split(',')
			.map(tag => tag.trim())
			.filter(tag => tag.length > 0);
		const source = document.getElementById('context-source')?.value.trim();

		if (!title || !content) {
			this.showToast('Title and content are required', 'error');
			return;
		}

		try {
			// Use Wails backend to save context item
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.AddContextBucketItem({
					type,
					title,
					content,
					priority,
					tags,
					source: source || undefined
				});

				if (result.success) {
					this.showToast('Context item added successfully', 'success');
					this.closeContextModal();
					this.loadContextItems();
				} else {
					this.showToast(result.message || 'Failed to add context item', 'error');
				}
			} else {
				throw new Error('Wails backend not available');
			}
		} catch (error) {
			console.error('Failed to save context item:', error);
			this.showToast('Failed to save context item', 'error');
		}
	}

	closeContextModal() {
		const modal = document.getElementById('context-add-modal');
		if (modal) {
			modal.classList.add('hidden');
		}
	}

	async deleteContextItem(itemId) {
		if (!confirm('Are you sure you want to delete this context item?')) {
			return;
		}

		try {
			// Use Wails backend to delete context item
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.DeleteContextBucketItem(itemId);

				if (result.success) {
					this.showToast('Context item deleted', 'success');
					this.loadContextItems();
				} else {
					this.showToast('Failed to delete context item', 'error');
				}
			} else {
				throw new Error('Wails backend not available');
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
			// Use Wails backend to clear context bucket
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.ClearContextBucket();

				if (result.success) {
					this.showToast('Context bucket cleared', 'success');
					this.loadContextItems();
				} else {
					this.showToast('Failed to clear context bucket', 'error');
				}
			} else {
				throw new Error('Wails backend not available');
			}
		} catch (error) {
			console.error('Failed to clear context bucket:', error);
			this.showToast('Failed to clear context bucket', 'error');
		}
	}

	async exportContextBucket() {
		try {
			// Use Wails backend to export context bucket
			if (window.go && window.go.ui && window.go.ui.App) {
				const result = await window.go.ui.App.ExportContextBucket();

				if (result.success) {
					// Create and download JSON file
					const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
					const url = URL.createObjectURL(blob);
					const a = document.createElement('a');
					a.href = url;
					a.download = `context-bucket-${new Date().toISOString().split('T')[0]}.json`;
					document.body.appendChild(a);
					a.click();
					document.body.removeChild(a);
					URL.revokeObjectURL(url);

					this.showToast('Context bucket exported', 'success');
				} else {
					this.showToast('Failed to export context bucket', 'error');
				}
			} else {
				throw new Error('Wails backend not available');
			}
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

				// Use Wails backend to import context bucket
				if (window.go && window.go.ui && window.go.ui.App) {
					const result = await window.go.ui.App.ImportContextBucket(data);

					if (result.success) {
						this.showToast('Context bucket imported successfully', 'success');
						this.loadContextItems();
					} else {
						this.showToast('Failed to import context bucket', 'error');
					}
				} else {
					throw new Error('Wails backend not available');
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

	// Helper method to escape HTML
	escapeHtml(text) {
		const div = document.createElement('div');
		div.textContent = text;
		return div.innerHTML;
	}
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
	window.app = new FFTerminalApp();
});

// Global functions for context modal
window.closeContextModal = function() {
	if (window.app) {
		window.app.closeContextModal();
	}
};

window.saveContextItem = function() {
	if (window.app) {
		window.app.saveContextItem();
	}
};