sudo apt update
sudo apt install --reinstall ca-certificates
sudo update-ca-certificates

# Was just a misset clock last time
date
sudo timedatectl set-ntp true
date