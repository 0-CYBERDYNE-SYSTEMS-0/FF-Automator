.PHONY: install dev build clean run setup

# Install dependencies
install:
	go mod download
	go mod tidy

# Setup development environment
setup:
	@echo "Installing Wails CLI..."
	go install github.com/wailsapp/wails/v2/cmd/wails@latest
	@echo "Installing dependencies..."
	$(MAKE) install
	@echo "Setup complete!"

# Run in development mode with hot reload
dev:
	wails dev

# Build for development
build:
	wails build

# Build for production (optimized, no debug)
build-prod:
	wails build -production -clean

# Clean build artifacts
clean:
	rm -rf build/
	go clean

# Run the built application
run: build
	./build/bin/macOS-use.app/Contents/MacOS/macOS-use

# Create DMG installer (requires production build)
dmg: build-prod
	@echo "Creating DMG installer..."
	@if ! command -v create-dmg &> /dev/null; then \
		echo "Installing create-dmg..."; \
		brew install create-dmg; \
	fi
	@rm -f macOS-use.dmg
	create-dmg \
		--volname "macOS-use" \
		--window-pos 200 120 \
		--window-size 600 400 \
		--icon-size 100 \
		--icon "macOS-use.app" 175 120 \
		--hide-extension "macOS-use.app" \
		--app-drop-link 425 120 \
		"macOS-use.dmg" \
		"build/bin/"
	@echo "DMG created: macOS-use.dmg"

# Check Python backend
check-backend:
	@if [ ! -d "../.venv" ]; then \
		echo "Python virtual environment not found!"; \
		echo "Please run 'uv venv && uv pip install --editable .' in parent directory"; \
		exit 1; \
	fi
	@if [ ! -f "../.env" ]; then \
		echo "Environment file not found!"; \
		echo "Please copy .env.example to .env and add your API keys"; \
		exit 1; \
	fi
	@echo "Python backend check passed ✓"

# Full setup from scratch
setup-all: setup check-backend
	@echo "Full setup complete! Run 'make dev' to start development"