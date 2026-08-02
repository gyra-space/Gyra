#!/usr/bin/env node

/**
 * Gyra CLI Launcher
 * 
 * This script wraps the Python-based Gyra tool,
 * handling installation and execution automatically.
 */

const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const os = require('os');

const INSTALL_DIR = process.env.GYRA_INSTALL_DIR || path.join(os.homedir(), '.gyra');
const REPO_URL = 'https://github.com/gyra-ai/Gyra.git';

// Colors for terminal output
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message) {
  console.log(`${colors.blue}[Gyra]${colors.reset} ${message}`);
}

function warn(message) {
  console.log(`${colors.yellow}[Warning]${colors.reset} ${message}`);
}

function error(message) {
  console.error(`${colors.red}[Error]${colors.reset} ${message}`);
  process.exit(1);
}

function success(message) {
  console.log(`${colors.green}[Success]${colors.reset} ${message}`);
}

function commandExists(command) {
  try {
    execSync(`which ${command}`, { stdio: 'ignore' });
    return true;
  } catch {
    return false;
  }
}

function ensureUv() {
  if (commandExists('uv')) {
    log('uv is already installed');
    return;
  }

  log('Installing uv (Python package manager)...');
  try {
    execSync('curl -LsSf https://astral.sh/uv/install.sh | sh', { 
      stdio: 'inherit',
      shell: true 
    });
    success('uv installed successfully');
  } catch (err) {
    error(`Failed to install uv: ${err.message}`);
  }
}

function ensureRepo() {
  if (fs.existsSync(path.join(INSTALL_DIR, '.git'))) {
    log('Gyra already installed, updating...');
    try {
      execSync('git pull origin main', { 
        cwd: INSTALL_DIR, 
        stdio: 'pipe' 
      });
    } catch (err) {
      warn('Failed to update, using existing version');
    }
    return;
  }

  log('Installing Gyra...');
  const parentDir = path.dirname(INSTALL_DIR);
  
  if (!fs.existsSync(parentDir)) {
    fs.mkdirSync(parentDir, { recursive: true });
  }

  try {
    execSync(`git clone --depth 1 ${REPO_URL} "${INSTALL_DIR}"`, {
      stdio: 'inherit'
    });
    success('Gyra repository cloned');
  } catch (err) {
    error(`Failed to clone repository: ${err.message}`);
  }
}

function installDeps() {
  log('Installing Python dependencies...');
  
  const extras = [
    'base',
    'proxy_openai',
    'rag',
    'storage_chromadb',
    'gyras',
    'storage_oss2',
    'client',
    'ext_base'
  ].map(e => `--extra "${e}"`).join(' ');

  try {
    execSync(`uv sync --all-packages --frozen ${extras}`, {
      cwd: INSTALL_DIR,
      stdio: 'inherit',
      shell: true,
      env: {
        ...process.env,
        PATH: `${path.join(os.homedir(), '.local/bin')}:${process.env.PATH}`
      }
    });
    success('Dependencies installed');
  } catch (err) {
    error(`Failed to install dependencies: ${err.message}`);
  }
}

function runGyra(args) {
  const uvPath = path.join(os.homedir(), '.local/bin/uv');
  const pythonCmd = fs.existsSync(uvPath) ? uvPath : 'uv';
  
  const child = spawn(pythonCmd, ['run', 'gyra', ...args], {
    cwd: INSTALL_DIR,
    stdio: 'inherit',
    env: process.env
  });

  child.on('error', (err) => {
    error(`Failed to start Gyra: ${err.message}`);
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}

function main() {
  const args = process.argv.slice(2);

  // Handle help
  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
${colors.cyan}Gyra CLI${colors.reset}

Usage: gyra [options] [command]

Options:
  -h, --help     Show this help message
  -v, --version  Show version information
  --update       Update to latest version

Commands:
  server         Start Gyra server
  
For more information: https://github.com/gyra-ai/Gyra
    `);
    return;
  }

  // Handle version
  if (args.includes('--version') || args.includes('-v')) {
    console.log('Gyra v0.2.0');
    return;
  }

  // Handle update
  if (args.includes('--update')) {
    ensureUv();
    ensureRepo();
    installDeps();
    success('Gyra updated successfully!');
    return;
  }

  // First run setup
  if (!fs.existsSync(INSTALL_DIR)) {
    ensureUv();
    ensureRepo();
    installDeps();
  }

  // Run Gyra
  runGyra(args);
}

main();
