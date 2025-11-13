# WSL2 Docker Setup Guide

## Option 1: Docker Desktop for Windows (Recommended)

This is the easiest setup for WSL2.

### Install Docker Desktop

1. **Download Docker Desktop for Windows**
   - https://www.docker.com/products/docker-desktop/

2. **Install and enable WSL2 backend**
   - During installation, ensure "Use WSL 2 instead of Hyper-V" is checked
   - Restart Windows if prompted

3. **Enable WSL2 integration**
   - Open Docker Desktop
   - Settings → Resources → WSL Integration
   - Enable integration for your Ubuntu distribution
   - Click "Apply & Restart"

4. **Verify in WSL2**
   ```bash
   docker --version
   docker-compose --version
   docker ps
   ```

### Then run setup

```bash
cd ~/repos/listfig-claude
./scripts/setup-dev.sh
```

---

## Option 2: Docker Engine in WSL2 (Advanced)

If you prefer Docker Engine directly in WSL2:

### Install Docker Engine

```bash
# Update packages
sudo apt-get update

# Install prerequisites
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add your user to docker group
sudo usermod -aG docker $USER

# Start Docker daemon
sudo service docker start
```

### Configure Docker to start automatically

Add to your `~/.bashrc`:

```bash
# Start Docker daemon automatically
if ! service docker status > /dev/null 2>&1; then
    sudo service docker start > /dev/null 2>&1
fi
```

### Apply group changes

```bash
# Logout and login again, or run:
newgrp docker

# Verify
docker ps
```

---

## Quick Fix for Permission Issues

If you have Docker Desktop installed but getting permission errors:

```bash
# Check if Docker Desktop is running (in Windows)
# Then in WSL2:

# Verify Docker is accessible
docker ps

# If still permission denied, check WSL integration in Docker Desktop settings
```

---

## After Docker is Working

1. **Set your OpenAI API key**
   ```bash
   cd ~/repos/listfig-claude
   cp .env.example .env
   nano .env  # or vim, code, etc.
   ```

   Add your key:
   ```bash
   OPENAI_API_KEY=sk-proj-your-key-here
   ```

2. **Run setup**
   ```bash
   ./scripts/setup-dev.sh
   ```

3. **Test email processing**
   ```bash
   ./scripts/test-email.sh
   ```

---

## Troubleshooting

### "Cannot connect to Docker daemon"

**Using Docker Desktop:**
- Make sure Docker Desktop is running in Windows
- Check Settings → Resources → WSL Integration is enabled for Ubuntu

**Using Docker Engine:**
```bash
sudo service docker start
docker ps
```

### "Permission denied" on docker.sock

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and back in, or:
newgrp docker
```

### Snap Docker (if installed via snap)

If Docker is installed via snap, you may have issues. Recommended to uninstall snap version and use Docker Desktop instead:

```bash
# Check if snap docker
snap list | grep docker

# If found, remove it
sudo snap remove docker

# Then install Docker Desktop for Windows
```

---

## Verify Everything Works

```bash
# Check Docker
docker --version
docker ps

# Check Docker Compose
docker compose version

# Run setup
cd ~/repos/listfig-claude
./scripts/setup-dev.sh
```

---

## WSL2-Specific Notes

- **File system performance**: Keep your code in WSL2 filesystem (`~/repos/`) not Windows filesystem (`/mnt/c/`)
- **Memory limits**: Docker Desktop allows you to set WSL2 memory limits in settings
- **Port forwarding**: Windows automatically forwards WSL2 ports, so `localhost:8000` works from Windows too
