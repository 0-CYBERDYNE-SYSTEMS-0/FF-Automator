# Parity Plan: Web Interface → Go Desktop UI

## Goal
Bring the Go desktop application (`go-ui/assets`) to feature, layout, and behavioural parity with the modern web interface (`web_interface/static`).

## Current State Summary
- **Source of truth (web)**: Rich tabbed layout with top navigation, animated loading screen, dark/light theming, chat sidebar containing saved automations, context bucket, configurable settings, full agent console, sessions/automations/providers management views, toast notifications, and responsive/mobile navigation. See `web_interface/static/index.html` and `web_interface/static/js/app.js`.
- **Go desktop UI**: Sidebar-based layout (`go-ui/assets/index.html`) with limited controls—basic provider/model dropdowns, chat/agent/templates/scheduler views, session & automation dropdowns, log panel. Missing context bucket, theming controls, tabbed navigation, toast UX, and most rich management surfaces. Backed by Wails bindings in `go-ui/internal/ui/app.go`.

## High-Level Gap Highlights
1. **Layout/Theming**: Web uses header tabs + mobile nav + theme/background toggles; Go UI uses fixed sidebar with a single theme.
2. **Chat Sidebar Features**: Web provides quick automation categories, context bucket management, granular settings; Go UI lacks these sections entirely.
3. **Chat Controls**: Web supports stop/interrupt/redirect buttons with clear state handling, typing indicators, toasts, saved chat sessions, background image upload; Go UI offers minimal controls and no status feedback.
4. **Agent Console**: Web exposes full task form (max steps/actions, provider/model/API key, custom instructions, context integration, progress UI); Go UI has a basic text field feeding terminal output.
5. **Sessions/Automations/Providers Tabs**: Web delivers dedicated tab views with cards, filters, schedules, and provider cards; Go UI collapses everything into dropdowns and a separate scheduler view.
6. **Context Bucket & Persistence**: Web integrates add/import/export/clear, token usage, and agent access; Go UI has no corresponding functionality nor backend bindings.
7. **Feedback & Responsiveness**: Web uses toast notifications, loading placeholders, mobile navigation; Go UI relies on console/log output and is partially responsive.

## Implementation Plan

### 1. Shared Infrastructure & Data Access
- Expose the Python backend base URL to the webview (add `GetBackendURL()` binding in `go-ui/internal/ui/app.go`).
- Audit existing Wails bindings to decide reuse vs. direct `fetch` calls; prefer mirroring web behaviour by calling REST/WebSocket endpoints directly via the exposed base URL, while keeping bindings for operations that require Go mediation (e.g., launching Python, websocket client lifecycle).
- Centralise API helper utilities in a new JS module (e.g., `assets/js/api.js`) mirroring `FFTerminalApp.apiBase` usage for consistency.

### 2. Global Layout & Theming Parity
- Replace the current sidebar layout in `go-ui/assets/index.html` with the web interface skeleton (header, nav buttons, main content containers, mobile nav) adapted for Wails (remove browser-only scripts, adjust asset paths).
- Port the loading screen and connection status components; hook them into Go app startup events.
- Implement theme toggling & persistence: replicate `theme-toggle` logic from web JS, toggling `theme-dark` class on `<body>` and storing preference locally.
- Add background image upload/clear support (`bg-image-input` flow), ensuring files are stored in `localStorage`/`IndexedDB` only (no disk writes needed).

### 3. Toast Notifications & UX Feedback
- Port the toast container and `showToast` helper used in `web_interface/static/js/app.js` to the Go UI JS bundle, ensuring consistent styling and timeouts.
- Replace current `alert`/`appendChatMessage('system', …)` usages for status/errors with toasts where appropriate.

### 4. Chat Experience Parity
- Recreate the chat tab structure (sidebar + main pane) inside the Go UI, matching HTML structure and class names from the web interface for CSS reuse.
- Implement Saved Automations quick actions: fetch automation templates, render category tabs, support `executeAutomation` & context menu placeholders.
- Integrate typing indicator, streaming updates, stop/interrupt/redirect/redirect buttons, clear/save chat modals, chat hint text, and conversation history tracking.
- Add chat settings panel: provider/model selection (reuse provider API), API key inputs per provider, GPT-5 reasoning/verbosity controls (conditional display), custom instructions textarea, background image uploader.
- Support chat session saving/loading using the same endpoints used on the web, including save modal; ensure conversation history is persisted for automation creation.

### 5. Context Bucket Integration
- Port UI (collapsible card, token usage meter, add/import/export/clear buttons, items list) into the chat sidebar and agent tab.
- Add modals (`context-add-modal`) and handlers for add/import/export/clear actions identical to web implementation.
- Extend `go-ui/internal/ui/app.go` with bindings for context-bucket endpoints (list, summary, add, delete, clear, export, import) or call endpoints directly from JS using the backend base URL.
- Ensure agent context summary updates after modifications and context session IDs sync between agent & chat views.

### 6. Agent Console Parity
- Port agent tab HTML & CSS, including task textarea, refine button, numeric inputs for steps/actions, provider/model/API key selectors, GPT-5 parameters, custom instructions, context bucket controls.
- Implement `Refine with AI` flow (POST `/api/refine-prompt`) and ensure UI handles loading/disabled state.
- Add progress UI (progress bar, step counts), streaming terminal output, final result panel, save-as-automation enablement once execution finishes.
- Wire stop button to websocket stop message (`stop_agent`/`stop_chat` depending on backend protocol) with state cleanup matching web behaviour.

### 7. Sessions Tab Parity
- Rebuild sessions tab using card layout from `web_interface/static/index.html`, displaying metadata (timestamp, counts) and action buttons (load/delete).
- Hook refresh and save controls to backend endpoints, reusing the modal/inputs already defined in web JS.
- Ensure switching tabs triggers data refresh aligning with web logic (`switchTab` behaviour).

### 8. Automations Tab Parity
- Implement tabbed sections for Saved, Scheduled, Execution History with the same filters/search inputs and empty states as the web UI.
- Reuse automation cards markup and actions (run/edit/duplicate/delete) while aligning with existing Go bindings for scheduling/history operations.
- Integrate scheduled automations list and history views currently present in Go UI scheduler/history modals into the new tab structure; retire the separate Templates/Scheduler “modes” once parity tabs exist.
- Provide `Save Current Chat`, `Refresh`, `Run Now`, and history modals consistent with web behaviour.

### 9. Providers Tab Parity
- Port provider cards grid (availability indicator, model badges, API key input, test buttons) and hook into `loadProviders()` and `testProvider()` logic.
- Ensure API keys entered in the provider cards propagate to chat/agent settings (store locally, apply when sending requests).
- Include refresh control and loading placeholders.

### 10. WebSocket & State Management Enhancements
- Align websocket handling with web app: reconnection logic, heartbeat ping/pong, unified message router handling `chat_stream_update`, `automation_*`, etc.
- Ensure UI state flags (`isChatRunning`, `isAgentRunning`, etc.) exist and control button disabled states matching web behaviour.
- Support typing indicators and streaming message updates inside chat UI.

### 11. Styling & Responsiveness
- Port `web_interface/static/styles.css` (or merge key sections) into the Go asset pipeline, adjusting variables to work with Wails (e.g., font imports, icon CDN usage).
- Verify responsive behaviours including mobile nav toggles; implement JS to handle mobile tab switching if necessary.
- Ensure theme variants (`body.theme-dark`, background overlays) render correctly in desktop webview.

### 12. Backend/Wails Binding Updates
- Extend `go-ui/internal/ui/app.go` with helper methods for any REST endpoints not already covered (context bucket, automation tabs, provider API key submission if needed, etc.).
- Ensure JSON contracts match those expected by the web front-end scripts (e.g., provider objects as map vs array—convert as needed for parity).
- Update `cmd/macos-use-ui/main.go` startup to preload new assets if directory structure changes.

### 13. QA & Validation
- Manual parity walkthrough comparing each tab against the running web interface (same backend dataset).
- Exercise websocket flows: chat streaming, agent runs, automation execution, stop/interrupt controls.
- Validate context bucket CRUD, import/export round-trips, session save/load, automation scheduling/history, provider testing.
- Test theme/background persistence across app restarts.
- Verify responsive layout at multiple window sizes within the desktop app.
- Capture follow-up issues (e.g., unimplemented context edit) as backlog tasks.

### 14. Delivery Milestones
1. **Scaffolding & Theming**: Layout swap, navigation, theme/background toggle, toasts.
2. **Chat + Context Bucket**: Sidebar parity, chat controls, provider/model settings.
3. **Agent Console**: Full agent tab parity with context integration.
4. **Management Tabs**: Sessions, Automations, Providers replicate web experience; deprecate redundant sidebar controls.
5. **Backend Binding Completion**: All new API calls wired, websocket parity confirmed.
6. **Styling & QA**: Responsive polish, accessibility checks, final walkthrough vs. web UI.

