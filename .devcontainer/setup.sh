#!/usr/bin/env bash
set -e

echo "Installing ffmpeg and fonts..."
sudo apt-get update -qq
sudo apt-get install -y -qq ffmpeg fonts-noto fonts-noto-cjk fonts-dejavu > /dev/null

echo "Installing Python dependencies..."
pip install --quiet -r requirements.txt

echo "Downloading NLTK sentence tokenizer data..."
python -m nltk.downloader punkt punkt_tab

echo ""
echo "Setup complete."
echo "Run the app with:  python app.py"
echo "Then open the forwarded port 5000 from the 'Ports' tab in VS Code."
