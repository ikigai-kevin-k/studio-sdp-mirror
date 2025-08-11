# SDP Roulette System CI/CD Process Documentation

## 📋 Overview

This document provides detailed instructions for the Git Actions CI/CD process of the `studio-sdp-roulette` project, including build, testing, deployment, and other execution steps for each stage.

## 🏗️ Project Architecture

```
studio-sdp-roulette/
├── .github/
│   └── workflows/
│       ├── build.yml          # Main build and test process
│       ├── deploy.yml         # Deployment process
│       └── quick-build.yml    # Quick build process
├── src/                       # Source code directory
├── tests/                     # Test directory
├── conf/                      # Configuration files
├── pyproject.toml            # Project configuration
├── requirements.txt           # Dependency package list
├── test-ci.sh                # Local test script
└── CICD.md                   # This document
```

## 🔄 CI/CD Workflows

### 1. Main Build Process (build.yml)

**Trigger Conditions:**
- Push to `main`, `develop`, `feature/*` branches
- Create Pull Request to `main`, `develop` branches

**Execution Stages:**

#### Stage 1: Testing and Quality Check
```yaml
jobs:
  test:
    name: Test and Quality Check
    runs-on: ubuntu-latest
```

**Execution Steps:**
1. **Checkout Code** (`actions/checkout@v4`)
   - Download latest code from Git repository

2. **Setup Python Environment** (`actions/setup-python@v4`)
   - Install Python 3.12 version

3. **Cache Dependencies** (`actions/cache@v3`)
   - Cache pip dependencies to improve build speed

4. **Install Dependencies**
   ```bash
   python -m pip install --upgrade pip
   pip install -e ".[dev]"
   ```

5. **Code Quality Check**
   - **flake8**: Code style and error checking
   - **black**: Code formatting check
   - **mypy**: Type checking

6. **Unit Testing** (`pytest`)
   - Execute all test cases
   - Generate coverage reports
   - Upload coverage to Codecov

#### Stage 2: Build Executables
```yaml
jobs:
  build:
    name: Build Executables
    runs-on: ubuntu-latest
    needs: test  # Depends on successful test stage
```

**Execution Steps:**
1. **Environment Preparation**
   - Checkout code
   - Setup Python 3.12
   - Install dependencies and shiv tool

2. **Package with Shiv**
   ```bash
   # VIP Roulette
   PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-vip.pyz -e main_vip:main .
   
   # Speed Roulette
   PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-speed.pyz -e main_speed:main .
   
   # SicBo
   PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-scibo.pyz -e main_scibo:main .
   
   # Baccarat
   PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-baccarat.pyz -e main_baccarat:main .
   ```

3. **Upload Artifacts**
   - Upload all `.pyz` files as GitHub Actions artifacts
   - Retain for 30 days

#### Stage 3: Security Scan
```yaml
jobs:
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: test  # Depends on successful test stage
```

**Execution Steps:**
1. **Install Security Check Tool**
   ```bash
   pip install safety
   ```

2. **Execute Security Check**
   ```bash
   safety check --json --output safety-report.json
   ```

3. **Upload Security Report**
   - Upload security check report as artifact

### 2. Deployment Process (deploy.yml)

**Trigger Conditions:**
- When `build.yml` workflow completes successfully
- Only triggers on `main` branch

**Execution Stages:**

#### Stage 1: Deploy to Staging Environment
```yaml
jobs:
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
```

**Execution Steps:**
1. **Download Build Artifacts**
   - Download all executable files from `build.yml`

2. **Deploy to Staging**
   - Execute Staging environment deployment logic
   - Send deployment notifications

#### Stage 2: Deploy to Production Environment
```yaml
jobs:
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}
    environment: production
    needs: deploy-staging  # Depends on successful Staging deployment
```

**Execution Steps:**
1. **Download Build Artifacts**
2. **Deploy to Production**
3. **Send Deployment Notifications**

#### Stage 3: Rollback Mechanism
```yaml
jobs:
  rollback:
    name: Rollback on Failure
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'failure' }}
```

**Execution Steps:**
1. **Execute Rollback Logic**
2. **Send Rollback Notifications**

### 3. Quick Build Process (quick-build.yml)

**Trigger Conditions:**
- Manual trigger (`workflow_dispatch`)
- Can select game type and Python version

**Execution Steps:**
1. **Select Build Parameters**
   - Game type: vip, speed, scibo, baccarat
   - Python version: Default 3.12

2. **Build Specified Game Controller**
3. **Upload Artifacts**
4. **Basic Validation**

## 🚀 Execution Steps

### Prerequisites

#### 1. Environment Setup
```bash
# Enter project directory
cd kevin/studio-sdp-roulette

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e ".[dev]"
```

#### 2. Check Configuration
```bash
# Check Python version
python --version  # Should be 3.12.x

# Check required tools
shiv --version
flake8 --version
black --version
mypy --version
pytest --version
```

### Local Testing

#### 1. Execute Complete CI/CD Test
```bash
# Use test script
./test-ci.sh

# Or manually execute each step
```

#### 2. Manual Testing of Each Step
```bash
# Code quality check
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
black --check --diff .
mypy . --ignore-missing-imports

# Unit testing
pytest tests/ -v --cov=. --cov-report=term-missing

# Shiv packaging test
PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-vip.pyz -e main_vip:main .
python -c "import zipimport; z = zipimport.zipimporter('roulette-vip.pyz'); print('✅ Packaging successful')"
```

### Trigger CI/CD Process

#### 1. Automatic Trigger
```bash
# Commit changes
git add .
git commit -m "feat: add new feature or fix issue"
git push origin main

# This will automatically trigger the build.yml workflow
```

#### 2. Manual Trigger
1. Go to GitHub project page
2. Click `Actions` tab
3. Select workflow to execute
4. Click `Run workflow`
5. Set parameters (if applicable)
6. Click `Run workflow`

### Monitor Execution Status

#### 1. View Workflow Status
- Check execution progress on GitHub Actions page
- Green checkmark indicates success
- Red X indicates failure

#### 2. View Detailed Logs
- Click workflow name to view detailed execution logs
- Click specific step to view detailed output for that step

#### 3. Download Artifacts
- After successful build, download artifact files on `Actions` page
- Artifacts include: `roulette-vip.pyz`, `roulette-speed.pyz`, etc.

## 🔧 Troubleshooting

### Common Issues

#### 1. Python Version Mismatch
```bash
# Check Python version
python --version

# If version is incorrect, use pyenv or conda to switch versions
pyenv install 3.12.0
pyenv local 3.12.0
```

#### 2. Dependency Installation Failure
```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 3. Test Failure
```bash
# Check test environment
pytest --collect-only

# Execute single test file
pytest tests/test_main_vip.py::TestVIPRoulette::test_import_main_vip -v
```

#### 4. Shiv Packaging Failure
```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Manually set PYTHONPATH
export PYTHONPATH=.

# Retry packaging
shiv --compressed --compile-pyc -o roulette-vip.pyz -e main_vip:main .
```

### Workflow Failure Handling

#### 1. Check Failure Cause
- View GitHub Actions logs
- Check error messages and stack traces

#### 2. Reproduce Problem Locally
- Reproduce failed steps in local environment
- Use `test-ci.sh` script for testing

#### 3. Fix Problem
- Fix code or configuration based on error messages
- Re-test to ensure problem is resolved

## 📊 Best Practices

### 1. Branch Strategy
- Use `main` branch to trigger complete process
- Use `develop` branch for development testing
- Use `feature/*` branches for feature development

### 2. Commit Messages
- Use clear commit messages
- Follow Conventional Commits specification
- Facilitate change tracking and automated version management

### 3. Test Coverage
- Maintain high test coverage
- Regularly check and improve test cases
- Use coverage reports to identify untested code

### 4. Dependency Management
- Use Dependabot to automatically update dependencies
- Regularly check for security vulnerabilities
- Lock dependency versions to ensure stability

### 5. Deployment Strategy
- Use blue-green deployment or canary deployment
- Implement automatic rollback mechanisms
- Monitor deployment status and performance metrics

## 📚 Related Resources

- [GitHub Actions Official Documentation](https://docs.github.com/en/actions)
- [Shiv Packaging Tool Documentation](https://shiv.readthedocs.io/)
- [Python Project Structure Best Practices](https://docs.python-guide.org/writing/structure/)
- [Pytest Testing Framework Documentation](https://docs.pytest.org/)
- [Mypy Type Checking Documentation](https://mypy.readthedocs.io/)

## 📞 Support

If you encounter issues while using the CI/CD process:

1. Check the troubleshooting section of this document
2. View GitHub Actions execution logs
3. Report issues in project Issues
4. Contact development team for assistance

---

*Last Updated: August 2024*
*Version: 1.0.0*
