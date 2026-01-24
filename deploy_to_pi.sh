#!/bin/bash
# Deployment script for DC Motor Control System to Raspberry Pi
# Usage: ./deploy_to_pi.sh

PI_USER="wajeru"
PI_IP="192.168.100.106"
PI_DIR="DC-Control_v1.0"  # Using underscore for compatibility

echo "🚀 Deploying DC Motor Control System to Raspberry Pi"
echo "=================================================="
echo "Target: $PI_USER@$PI_IP"
echo "Directory: ~/$PI_DIR"
echo ""

# Test connection
echo "📡 Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 $PI_USER@$PI_IP "echo 'Connection successful'" 2>/dev/null; then
    echo "❌ ERROR: Cannot connect to Raspberry Pi"
    echo "   Please check:"
    echo "   1. IP address is correct: $PI_IP"
    echo "   2. Raspberry Pi is powered on and connected"
    echo "   3. SSH is enabled on the Pi"
    exit 1
fi
echo "✅ Connection successful!"
echo ""

# Create directory on Pi
echo "📁 Creating directory on Raspberry Pi..."
ssh $PI_USER@$PI_IP "mkdir -p $PI_DIR"
echo "✅ Directory created"
echo ""

# Transfer files
echo "📦 Transferring files (this may take a minute)..."
rsync -avz --progress \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.git' \
    --exclude 'venv' \
    --exclude '*.log' \
    --exclude '.vscode' \
    --exclude '*.swp' \
    --exclude '.DS_Store' \
    d:/DC-Motor_v2.0/ $PI_USER@$PI_IP:~/$PI_DIR/

if [ $? -eq 0 ]; then
    echo "✅ Files transferred successfully!"
else
    echo "❌ Transfer failed!"
    exit 1
fi
echo ""

# Rename to include space (optional)
echo "📝 Renaming directory to 'DC-Control v1.0'..."
ssh $PI_USER@$PI_IP "mv $PI_DIR 'DC-Control v1.0' 2>/dev/null || true"
PI_DIR="DC-Control v1.0"
echo ""

# Setup on Pi
echo "⚙️  Setting up on Raspberry Pi..."
ssh $PI_USER@$PI_IP "bash -s" << 'ENDSSH'
cd "DC-Control v1.0" || exit 1

echo "1️⃣  Checking Python version..."
python3 --version

echo ""
echo "2️⃣  Installing dependencies..."
pip3 install -r requirements.txt --user

echo ""
echo "3️⃣  Upgrading TensorFlow (important for security)..."
pip3 install --upgrade tensorflow --user

echo ""
echo "4️⃣  Generating model checksums (if models exist)..."
if [ -d "models" ]; then
    python3 << 'ENDPY'
from nn_models import compute_file_checksum, save_checksum
import os

if os.path.exists('models'):
    model_files = [f for f in os.listdir('models') if f.endswith('.h5')]
    if model_files:
        for f in model_files:
            path = f'models/{f}'
            checksum = compute_file_checksum(path)
            save_checksum(path, checksum)
            print(f'✓ Generated checksum for {f}')
    else:
        print('No .h5 model files found')
else:
    print('No models directory found - will be created when needed')
ENDPY
else
    echo "No models directory - will be created when needed"
fi

echo ""
echo "5️⃣  Running tests..."
if command -v pytest &> /dev/null; then
    pytest tests/ -v --tb=short || echo "⚠️  Some tests may fail without hardware"
else
    echo "⚠️  pytest not installed, skipping tests"
fi

echo ""
echo "6️⃣  Creating .env file from example..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env file - please review and customize"
else
    echo "⚠️  .env file already exists - not overwriting"
fi

echo ""
echo "✅ Setup complete!"
ENDSSH

echo ""
echo "=================================================="
echo "🎉 Deployment Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. SSH into your Raspberry Pi:"
echo "   ssh $PI_USER@$PI_IP"
echo ""
echo "2. Navigate to the project:"
echo "   cd '$PI_DIR'"
echo ""
echo "3. Review and customize .env file:"
echo "   nano .env"
echo ""
echo "4. Run the application:"
echo "   python3 modern_motor_gui.py"
echo ""
echo "📚 Documentation:"
echo "   - README.md - General overview"
echo "   - SECURITY.md - Security best practices"
echo "   - AUDIT_FIXES_SUMMARY.md - Recent security fixes"
echo ""
