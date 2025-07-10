package main

import (
	"context"
	"fmt"
	"log"
	"os"

	"github.com/macOS-use/go-ui/internal/backend"
	"github.com/macOS-use/go-ui/internal/ui"
	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"
	"github.com/wailsapp/wails/v2/pkg/options/mac"
)

func main() {
	// Create application instance
	app := ui.NewApp()

	// Start Python backend
	pythonManager := backend.NewPythonManager()
	if err := pythonManager.Start(); err != nil {
		log.Fatalf("Failed to start Python backend: %v", err)
	}
	defer pythonManager.Stop()

	// Wait for backend to be ready
	if err := pythonManager.WaitForReady(context.Background()); err != nil {
		log.Fatalf("Python backend failed to start: %v", err)
	}

	// Create application with options
	err := wails.Run(&options.App{
		Title:  "macOS-use",
		Width:  1200,
		Height: 800,
		AssetServer: &assetserver.Options{
			Assets: os.DirFS("assets"),
		},
		BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},
		OnStartup: func(ctx context.Context) {
			app.OnStartup(ctx, pythonManager)
		},
		OnShutdown: func(ctx context.Context) {
			app.OnShutdown(ctx)
		},
		Bind: []interface{}{
			app,
		},
		Mac: &mac.Options{
			TitleBar: &mac.TitleBar{
				TitlebarAppearsTransparent: true,
				HideTitle:                  false,
				FullSizeContent:           true,
			},
			About: &mac.AboutInfo{
				Title:   "macOS-use",
				Message: "Natural language control for macOS",
			},
		},
	})

	if err != nil {
		fmt.Printf("Error: %v\n", err)
	}
}