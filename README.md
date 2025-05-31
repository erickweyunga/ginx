# Ginx Documentation

![Ginx Logo](https://res.cloudinary.com/dsxjgnlco/image/upload/v1748659826/ginx-black_wrd4yn.jpg)

## Overview

Ginx is a command-line script runner powered by YAML configuration. It provides a unified interface for executing project scripts, managing dependencies, and automating development workflows.

## Table of Contents

- [Installation](#installation)
- [Configuration](#configuration)
- [Core Commands](#core-commands)
- [Plugin System](#plugin-system)
- [Version Management Plugin](#version-management-plugin)
- [Configuration Examples](#configuration-examples)
- [Advanced Usage](#advanced-usage)
- [Command Reference](#command-reference)

## Installation

### From Source

```bash
git clone https://github.com/erickweyunga/ginx.git
cd ginx
pip install -e .
```

### Dependencies

```bash
pip install typer[all] pyyaml rich
```

### Optional Dependencies

```bash
pip install packaging  # For version comparison features
```

## Configuration

Ginx looks for configuration files in the following order:

- `ginx.yaml`
- `ginx.yml`
- `.ginx.yaml`
- `.ginx.yml`

The configuration file uses YAML format and defines scripts under a `scripts` section.

### Basic Configuration Format

```yaml
scripts:
  script-name:
    command: "command to execute"
    description: "Description of what the script does"
    cwd: "/path/to/working/directory" # Optional
    env: # Optional environment variables
      VAR_NAME: "value"
```

### Simple String Format

```yaml
scripts:
  build: "python -m build"
  test: "pytest tests/"
```

## Core Commands

### `ginx list`

Lists all available scripts defined in the configuration file.

```bash
ginx list
```

**Output:**

- Script names
- Descriptions
- Commands

### `ginx run <script-name>`

Executes a specified script.

```bash
ginx run build
ginx run deploy "--force --region us-west"
```

**Options:**

- `--stream, -s`: Stream output in real-time
- `--dry-run, -n`: Show what would be executed without running
- `--verbose, -v`: Show verbose output including shell mode

**Example:**

```bash
ginx run test --stream --verbose
```

### `ginx init`

Creates a configuration file with common script examples.

```bash
ginx init
ginx init --file custom.yaml --force
```

**Options:**

- `--file, -f`: Specify output filename (default: ginx.yaml)
- `--force`: Overwrite existing configuration file

### `ginx validate`

Validates the YAML configuration file and checks for issues.

```bash
ginx validate
```

**Checks:**

- Required fields presence
- Command validity
- Working directory existence
- YAML syntax

### `ginx deps`

Checks dependencies for scripts and shows requirements file status.

```bash
ginx deps
```

**Output:**

- Available requirements files
- Script command dependencies
- Missing commands
- Installation suggestions

### `ginx install-deps`

Installs dependencies from requirements files or for missing script commands.

```bash
ginx install-deps --script-deps
ginx install-deps -r requirements.txt
ginx install-deps --dev --scope user
```

**Options:**

- `--requirements, -r`: Specific requirements file
- `--dev`: Install development dependencies only
- `--script-deps`: Install dependencies for script commands
- `--scope`: Installation scope (auto, global, user, venv, project)
- `--dry-run, -n`: Show what would be installed
- `--yes, -y`: Install without confirmation
- `--upgrade, -U`: Upgrade packages if already installed
- `--create-venv`: Create virtual environment if not in one

**Scopes:**

- `auto`: Detect environment and choose best option
- `global`: Install to global Python environment
- `user`: Install to user site-packages
- `venv`: Install to virtual environment
- `project`: Install to project directory

### `ginx generate-reqs`

Generates requirements file based on missing dependencies or virtual environment.

```bash
ginx generate-reqs --from-venv
ginx generate-reqs --script-deps
ginx generate-reqs --from-venv --dev -o requirements-dev.txt
```

**Options:**

- `--output, -o`: Output requirements file
- `--script-deps`: Include dependencies for script commands
- `--from-venv`: Generate from current virtual environment
- `--dev`: Generate development requirements
- `--exclude-system`: Exclude common system packages
- `--force`: Overwrite existing requirements file

### `ginx freeze`

Freezes current virtual environment packages to requirements file.

```bash
ginx freeze
ginx freeze --dev
ginx freeze -o custom-requirements.txt
```

**Options:**

- `--output, -o`: Output requirements file
- `--dev`: Generate requirements-dev.txt instead
- `--exclude-system`: Exclude common system packages
- `--force`: Overwrite existing requirements file

### `ginx env`

Shows current Python environment information.

```bash
ginx env
```

**Output:**

- Python version and executable path
- Virtual environment status
- Site packages locations
- Environment recommendations

### `ginx debug-plugins`

Debug plugin loading status and show registered plugins.

```bash
ginx debug-plugins
```

**Output:**

- Registered plugins count
- Plugin details (name, version, description)
- Plugin file existence checks
- Import status

## Plugin System

Ginx supports a plugin architecture for extending functionality. Plugins can add new commands, process scripts, and hook into execution lifecycle.

### Plugin Structure

```
src/plugins/
├── __init__.py
├── plugin_name/
│   ├── __init__.py
│   ├── core.py
│   └── utils.py
```

### Creating Plugins

Plugins inherit from `GinxPlugin` base class:

```python
from ginx.plugins import GinxPlugin
import typer

class MyPlugin(GinxPlugin):
    @property
    def name(self) -> str:
        return "my-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    def add_commands(self, app: typer.Typer) -> None:
        @app.command("my-command")
        def my_command():
            typer.echo("Hello from plugin!")
```

## Version Management Plugin

The version management plugin provides package version synchronization and update checking capabilities.

### `ginx check-updates`

Checks for package updates available on PyPI.

```bash
ginx check-updates
ginx check-updates -r requirements.txt
ginx check-updates --all --json
```

**Options:**

- `--requirements, -r`: Specific requirements file to check
- `--all`: Show all packages, not just outdated ones
- `--json`: Output results in JSON format
- `--timeout`: Timeout for PyPI requests in seconds

### `ginx sync-versions`

Syncs package versions with PyPI or requirements file.

```bash
ginx sync-versions --target latest
ginx sync-versions --target requirements -r requirements.txt
```

**Options:**

- `--target`: Sync target (latest, requirements, or specific file)
- `--requirements, -r`: Requirements file to sync with
- `--dry-run, -n`: Show what would be updated
- `--yes, -y`: Auto-confirm updates

**Note:** Full implementation coming soon.

### `ginx version-diff`

Compares package versions between environments.

```bash
ginx version-diff --file1 requirements.txt --file2 requirements-dev.txt
ginx version-diff --file1 prod.txt --file2 dev.txt --all
```

**Options:**

- `--file1`: First requirements file
- `--file2`: Second requirements file
- `--all`: Show all packages, not just differences

### `ginx pin-versions`

Pins all packages to specific versions.

```bash
ginx pin-versions
ginx pin-versions -r requirements.txt -o pinned.txt
```

**Options:**

- `--requirements, -r`: Requirements file to pin
- `--output, -o`: Output file for pinned requirements
- `--force`: Overwrite existing output file

## Configuration Examples

### Python Development Project

```yaml
scripts:
  install:
    command: "pip install -e ."
    description: "Install package in development mode"

  test:
    command: "pytest tests/ --cov=src"
    description: "Run tests with coverage"

  lint:
    command: "flake8 src/ && black --check src/"
    description: "Check code style"

  format:
    command: "black src/ && isort src/"
    description: "Format code"

  build:
    command: "python -m build"
    description: "Build distribution packages"

  pre-commit:
    command: "black src/ && isort src/ && flake8 src/ && pytest tests/ -x"
    description: "Run pre-commit checks"
```

### Node.js Project

```yaml
scripts:
  install:
    command: "npm install"
    description: "Install dependencies"

  dev:
    command: "npm run dev"
    description: "Start development server"

  build:
    command: "npm run build"
    description: "Build for production"

  test:
    command: "npm test"
    description: "Run tests"

  deploy:
    command: "npm run build && aws s3 sync dist/ s3://$S3_BUCKET/"
    description: "Build and deploy to S3"
    env:
      S3_BUCKET: "my-app-bucket"
```

### Docker Workflow

```yaml
scripts:
  build:
    command: "docker build -t myapp:latest ."
    description: "Build Docker image"

  run:
    command: "docker run -p 8080:8080 myapp:latest"
    description: "Run container locally"

  push:
    command: "docker push $REGISTRY/myapp:latest"
    description: "Push to registry"
    env:
      REGISTRY: "registry.example.com"

  compose-up:
    command: "docker-compose up -d"
    description: "Start all services"
    cwd: "./docker"
```

### Multi-Environment Setup

```yaml
scripts:
  dev-setup:
    command: "cp .env.development .env && docker-compose up -d db"
    description: "Setup development environment"

  prod-setup:
    command: "cp .env.production .env && kubectl apply -f k8s/"
    description: "Setup production environment"
    cwd: "./deployment"

  test-integration:
    command: "pytest tests/integration/"
    description: "Run integration tests"
    env:
      TEST_ENV: "integration"
      DATABASE_URL: "postgresql://test:test@localhost/testdb"
```

## Advanced Usage

### Shell Operators

Ginx automatically detects shell operators and executes commands through the shell:

```yaml
scripts:
  complex:
    command: "cmd1 && cmd2 || cmd3" # Uses shell execution

  simple:
    command: "python script.py" # Direct execution
```

**Detected operators:** `&&`, `||`, `;`, `|`, `>`, `<`, `&`, `$(`, backticks

### Environment Variables

Use environment variables in commands:

```yaml
scripts:
  deploy:
    command: "docker push $REGISTRY_URL/myapp:$BUILD_VERSION"
    description: "Deploy to registry"
    env:
      BUILD_VERSION: "1.0.0"
```

### Working Directories

Specify different working directories:

```yaml
scripts:
  frontend-build:
    command: "npm run build"
    cwd: "./frontend"

  backend-test:
    command: "pytest"
    cwd: "./backend"
```

### Script Chaining

Chain multiple operations:

```yaml
scripts:
  full-pipeline:
    command: "ginx run lint && ginx run test && ginx run build"
    description: "Complete CI pipeline"
```

## Command Reference

### Global Options

Most commands support these global patterns:

- `--help`: Show command help
- `--verbose, -v`: Verbose output
- `--dry-run, -n`: Show what would happen without executing
- `--yes, -y`: Auto-confirm prompts
- `--force`: Overwrite existing files

### Exit Codes

- `0`: Success
- `1`: General error
- `130`: Interrupted by user (Ctrl+C)
- Other: Command-specific exit codes

### Environment Variables

Ginx respects these environment variables:

- Standard shell variables (`PATH`, `HOME`, etc.)

### Configuration File Discovery

Ginx searches for configuration files in current directory and parent directories, making it possible to run commands from anywhere within a project hierarchy.

### Error Handling

- Configuration validation errors are reported with line numbers
- Command execution errors show both stdout and stderr
- Plugin loading errors are gracefully handled with warnings
- Network errors in version checking include timeout handling

## Best Practices

### Script Organization

- Use descriptive script names
- Group related scripts with consistent naming
- Provide clear descriptions for all scripts
- Use environment variables for configuration values

### Development Workflow

- Use `ginx validate` before committing configuration changes
- Include `ginx deps` output in documentation
- Pin dependency versions for production deployments
- Use virtual environments for isolation

### Performance

- Use `--stream` for long-running commands
- Set appropriate timeouts for network operations
- Cache dependency information when possible
- Use `--dry-run` to verify commands before execution

### Security

- Avoid hardcoding sensitive values in scripts
- Use environment variables for credentials
- Validate command inputs in custom plugins
- Review dependency updates for security implications
