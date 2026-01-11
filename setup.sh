#!/bin/bash

set -e

echo "🎮 LED Runner - Installation"
echo "================================"

# Create config.json from example if it doesn't exist
if [ ! -f config.json ]; then
    echo ""
    echo "📄 Creating config.json from config.example.json..."
    cp config.example.json config.json
    echo "   Edit config.json to customize your settings"
else
    echo ""
    echo "📄 config.json already exists, keeping your settings"
fi

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt update
sudo apt install -y python3-dev python3-venv python3-pip build-essential

# Create virtual environment
echo ""
echo "🐍 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python packages
echo ""
echo "📚 Installing Python packages..."
pip install -r requirements.txt

echo ""
echo "🔧 Installing systemd service..."

# Determine current user and directory
CURRENT_USER=$(whoami)
INSTALL_DIR=$(pwd)
HOME_DIR=$(eval echo ~$CURRENT_USER)

echo "   Installing for user: $CURRENT_USER"
echo "   Installation directory: $INSTALL_DIR"

# Generate service file from template
sed -e "s|{{USER}}|$CURRENT_USER|g" \
    -e "s|{{INSTALL_DIR}}|$INSTALL_DIR|g" \
    -e "s|{{HOME_DIR}}|$HOME_DIR|g" \
    led-runner.service.template > led-runner.service

# Copy service file to systemd directory
sudo cp led-runner.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start at boot)
sudo systemctl enable led-runner.service

echo ""
echo "🚀 Starting service..."
sudo systemctl start led-runner.service

# Wait and check status
sleep 2
echo ""
if sudo systemctl is-active --quiet led-runner.service; then
    echo "✅ Service is running!"
    echo ""
    echo "View live logs with:"
    echo "  journalctl -u led-runner -f"
else
    echo "⚠️  Service could not start. Check the status:"
    echo "  sudo systemctl status led-runner"
    echo "  journalctl -u led-runner -n 50"
fi

echo ""
echo "✅ Installation complete!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Service commands:"
echo "  sudo systemctl start led-runner    # Start the service"
echo "  sudo systemctl stop led-runner     # Stop the service"
echo "  sudo systemctl restart led-runner  # Restart the service"
echo "  sudo systemctl status led-runner   # View status"
echo "  journalctl -u led-runner -f        # View logs (live)"
echo ""
echo "The service will start automatically on reboot."
echo ""
echo "Or start manually with: ./start.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
