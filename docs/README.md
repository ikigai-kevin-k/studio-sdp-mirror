# Documentation

This directory contains the complete documentation for the Studio SDP Roulette System.

## Documentation Structure

- **Getting Started** - Installation and setup guides
- **Guides** - Detailed guides on system components
- **API Reference** - Complete API documentation
- **Deployment** - Deployment guides for different environments
- **Development** - Development setup and contribution guidelines
- **Troubleshooting** - Common issues and solutions
- **Resources** - Additional resources and integrations

## Building Documentation

### Prerequisites

```bash
pip install mkdocs-material
pip install mkdocs-git-revision-date-localized-plugin
pip install pymdown-extensions
```

### Build Locally

```bash
# Build documentation
mkdocs build

# Serve documentation locally
mkdocs serve
```

### View Documentation

Open http://127.0.0.1:8000 in your browser.

## Online Documentation

The documentation is automatically deployed to GitHub Pages:

- **URL**: https://studio-sdp.github.io/studio-sdp-roulette
- **Auto-deploy**: On push to `main` branch

## Contributing

When adding or updating documentation:

1. Edit files in `docs/` directory
2. Update `mkdocs.yml` if adding new sections
3. Test locally with `mkdocs serve`
4. Commit and push changes

## Related Files

- `mkdocs.yml` - MkDocs configuration
- `.github/workflows/docs.yml` - GitHub Pages deployment workflow

