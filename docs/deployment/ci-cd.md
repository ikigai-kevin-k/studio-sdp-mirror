# CI/CD Deployment Guide

This guide explains the CI/CD process for the Studio SDP System.

## Overview

The system uses GitHub Actions for automated CI/CD:

1. **Testing** - Automated testing and quality checks
2. **Building** - Create standalone executables
3. **Deployment** - Automated deployment to staging and production

## Workflows

### Main Build Process (`build.yml`)

**Trigger Conditions:**
- Push to `main`, `develop`, `feature/*`, `gitaction` branches
- Create Pull Request to `main`, `develop` branches

**Execution Stages:**

1. **Testing and Quality Check**
   - Code quality (flake8, black, mypy)
   - Unit testing (pytest)
   - Coverage reporting

2. **Build Executables**
   - Package with Shiv
   - Create `.pyz` files for all games
   - Upload artifacts

3. **Security Scan**
   - Dependency security check
   - Vulnerability scanning

### Deployment Process (`deploy.yml`)

**Trigger Conditions:**
- When `build.yml` completes successfully
- Triggers on `main` and `gitaction` branches

**Execution Stages:**

1. **Deploy to Staging**
   - Download build artifacts
   - Deploy to staging environment
   - Send notifications

2. **Deploy to Production**
   - Deploy to production environment
   - Send notifications

3. **Rollback Mechanism**
   - Automatic rollback on failure

## Local Testing

### Run CI/CD Tests Locally

```bash
# Use test script
./test-ci.sh

# Or manually execute each step
```

### Manual Testing Steps

```bash
# Code quality check
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
black --check --diff .
mypy . --ignore-missing-imports

# Unit testing
pytest tests/ -v --cov=. --cov-report=term-missing

# Shiv packaging test
PYTHONPATH=. shiv --compressed --compile-pyc -o roulette-vip.pyz -e main_vip:main .
```

## Triggering CI/CD

### Automatic Trigger

```bash
# Commit and push changes
git add .
git commit -m "feat: add new feature"
git push origin main
```

### Manual Trigger

1. Go to GitHub project page
2. Click `Actions` tab
3. Select workflow to execute
4. Click `Run workflow`
5. Set parameters (if applicable)
6. Click `Run workflow`

## Monitoring

### View Workflow Status

- Check execution progress on GitHub Actions page
- Green checkmark indicates success
- Red X indicates failure

### View Detailed Logs

- Click workflow name to view detailed execution logs
- Click specific step to view detailed output

### Download Artifacts

- After successful build, download artifact files on `Actions` page
- Artifacts include: `roulette-vip.pyz`, `roulette-speed.pyz`, etc.

## Troubleshooting

### Common Issues

#### Python Version Mismatch

```bash
# Check Python version
python --version

# Use pyenv to switch versions
pyenv install 3.12.0
pyenv local 3.12.0
```

#### Dependency Installation Failure

```bash
# Clear pip cache
pip cache purge

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### Test Failure

```bash
# Check test environment
pytest --collect-only

# Execute single test file
pytest tests/test_main_vip.py::TestVIPRoulette::test_import_main_vip -v
```

#### Shiv Packaging Failure

```bash
# Check PYTHONPATH
echo $PYTHONPATH

# Manually set PYTHONPATH
export PYTHONPATH=.

# Retry packaging
shiv --compressed --compile-pyc -o roulette-vip.pyz -e main_vip:main .
```

## Best Practices

### Branch Strategy

- Use `main` branch to trigger complete process
- Use `develop` branch for development testing
- Use `feature/*` branches for feature development

### Commit Messages

- Use clear commit messages
- Follow Conventional Commits specification
- Facilitate change tracking

### Test Coverage

- Maintain high test coverage
- Regularly check and improve test cases
- Use coverage reports to identify untested code

### Dependency Management

- Use Dependabot to automatically update dependencies
- Regularly check for security vulnerabilities
- Lock dependency versions to ensure stability

## Related Documentation

- [CICD.md](../../GITACTION_DOC/CICD.md) - Detailed CI/CD documentation
- [Deployment Overview](overview.md) - General deployment guide
- [Standalone Deployment](standalone.md) - Standalone executable deployment

