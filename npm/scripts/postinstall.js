#!/usr/bin/env node

/**
 * Post-install script for Gyra npm package
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

const INSTALL_DIR = process.env.GYRA_INSTALL_DIR || path.join(os.homedir(), '.gyra');
const REPO_URL = 'https://github.com/gyra-ai/Gyra.git';

const colors = {
  reset: '\x1b[0m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m'
};

function log(message) {
  console.log(`${colors.cyan}[gyra]${colors.reset} ${message}`);
}

function success(message) {
  console.log(`${colors.green}[gyra]${colors.reset} ${message}`);
}

function warn(message) {
  console.log(`${colors.yellow}[gyra]${colors.reset} ${message}`);
}

function commandExists(command) {
  try {
    execSync(`which ${command}`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function installUv() {
  if (commandExists('uv')) {
    return;
  }

  log('Installing uv package manager...');
  try {
    execSync('curl -LsSf https://astral.sh/uv/install.sh | sh', {
      stdio: 'inherit',
      shell: true
    });
    success('uv installed successfully');
  } catch (err) {
    warn('Failed to install uv automatically');
    warn('Please install manually: https://github.com/astral-sh/uv');
  }
}

function cloneRepo() {
  if (fs.existsSync(path.join(INSTALL_DIR, '.git'))) {
    log('Gyra already exists, skipping clone');
    return;
  }

  log('Cloning Gyra repository...');
  const parentDir = path.dirname(INSTALL_DIR);
  
  if (!fs.existsSync(parentDir)) {
    fs.mkdirSync(parentDir, { recursive: true });
  }

  try {
    execSync(`git clone --depth 1 ${REPO_URL} "${INSTALL_DIR}"`, {
      stdio: 'inherit'
    });
    success('Repository cloned successfully');
  } catch (err) {
    warn('Failed to clone repository automatically');
    warn(`You can manually clone: git clone ${REPO_URL} ${INSTALL_DIR}`);
  }
}

function main() {
  console.log('');
  log('Setting up Gyra...');
  console.log('');

  installUv();
  cloneRepo();

  console.log('');
  success('Setup complete! 🎉');
  console.log('');
  console.log('Next steps:');
  console.log('  1. Configure API keys in:');
  console.log(`     ${path.join(INSTALL_DIR, 'configs/gyra-proxy-aliyun.toml')}`);
  console.log('  2. Run: gyra --help');
  console.log('  3. Start server: gyra-server');
  console.log('');
  console.log('Documentation: https://github.com/gyra-ai/Gyra');
  console.log('');
}

main();
