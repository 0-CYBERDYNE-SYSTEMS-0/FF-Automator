#!/bin/bash

# Z.AI Setup Script for macOS-use
# This script helps configure Z.AI integration

echo "🤖 Z.AI Setup for macOS-use"
echo "=============================="
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

echo
echo "🔑 Next Steps:"
echo "1. Get your Z.AI API key from: https://z.ai/manage-apikey/apikey-list"
echo "2. Edit the .env file and add your API key:"
echo "   ANTHROPIC_AUTH_TOKEN=your_zai_api_key_here"
echo "   Z_AI_API_KEY=your_zai_api_key_here"
echo

# Check for Node.js/npm
if command -v node &> /dev/null && command -v npm &> /dev/null; then
    echo "✅ Node.js and npm are installed (required for Vision capabilities)"
else
    echo "⚠️  Node.js/npm not found - Vision capabilities will not work"
    echo "   Install Node.js from: https://nodejs.org/"
fi

echo
echo "🧪 Testing Z.AI Integration:"
echo "   Run: python test_zai_integration.py"
echo

echo "🚀 Starting Web Interface:"
echo "   Run: python web_interface_app.py"
echo "   Then open http://localhost:8080 and go to Providers tab"
echo

echo "📚 For complete documentation, see: docs/Z_AI_INTEGRATION.md"