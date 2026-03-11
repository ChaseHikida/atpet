# Install modem software
sudo apt install -y modemmanager libqmi-utils
sudo systemctl start ModemManager
sudo systemctl enable ModemManager