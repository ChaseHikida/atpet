# Install essential tools
sudo apt install -y git vim htop screen curl wget net-tools
sudo apt install -y python3 python3-pip python3-venv
sudo apt install -y i2c-tools python3-smbus python3-rpi.gpio

# Some git shit
git config --global init.defaultBranch main

# Enable I2C interface
sudo raspi-config