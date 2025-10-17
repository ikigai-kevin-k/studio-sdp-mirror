# SDP Roulette System - Code Obfuscation and Security

## Overview

The SDP Roulette System now includes advanced code obfuscation and security features using PyArmor. This document describes the enhanced build process that protects the codebase against reverse engineering, debugging, and tampering.

## Security Features

### Code Obfuscation
- **Advanced Obfuscation**: Complex control flow and string obfuscation
- **Import Obfuscation**: Module imports are obfuscated
- **String Mixing**: String literals are mixed and obfuscated
- **Suffix Randomization**: Random suffixes added to obfuscated files

### Anti-Debugging Protection
- **Runtime Detection**: Detects debugging attempts
- **Process Monitoring**: Monitors for debugger attachment
- **Execution Integrity**: Validates code execution environment

### Anti-Tampering Protection
- **Code Integrity Checks**: Validates code hasn't been modified
- **Assertion Calls**: Adds integrity assertion calls
- **Import Assertions**: Validates module imports haven't been tampered with

### Additional Security
- **Private Mode**: No external dependencies for obfuscation
- **Restrict Mode**: Enhanced security restrictions
- **Compression**: Code is compressed for additional protection

## Build Process

### GitHub Actions Workflow

The enhanced build process follows these steps:

1. **Dependency Installation**
   ```yaml
   - name: Install dependencies
     run: |
       pip install shiv pyarmor
   ```

2. **Code Obfuscation**
   ```yaml
   - name: Obfuscate code with PyArmor
     run: |
       pyarmor gen \
         --output obfuscated_output \
         --recursive \
         --enable-suffix \
         --mix-str \
         --assert-call \
         --assert-import \
         --private \
         --restrict \
         .
   ```

3. **Integrity Verification**
   ```yaml
   - name: Verify obfuscated code integrity
     run: |
       # Verify obfuscated files can be imported
       # Check main entry points exist
   ```

4. **Executable Building**
   ```yaml
   - name: Build executables from obfuscated code
     run: |
       cd obfuscated_output
       shiv --compressed --compile-pyc --output-file ../sdp-vip.pyz --entry-point main_vip:main .
   ```

5. **Testing**
   ```yaml
   - name: Test obfuscated executables
     run: |
       python test_obfuscated_build.py
   ```

### Local Development

For local development and testing, you can use the obfuscation script:

```bash
# Run obfuscation script
python scripts/obfuscate_code.py . -o ./obfuscated_output -p sdp_roulette

# Test obfuscated code
python test_obfuscated_build.py
```

## File Structure

```
studio-sdp-roulette/
├── scripts/
│   └── obfuscate_code.py          # Obfuscation script
├── test_obfuscated_build.py       # Test script for obfuscated code
├── .github/workflows/
│   └── build.yml                  # Enhanced build workflow
└── obfuscated_output/             # Generated obfuscated code
    ├── main_vip.py               # Obfuscated VIP roulette
    ├── main_speed.py             # Obfuscated Speed roulette
    ├── main_sicbo.py             # Obfuscated SicBo
    └── main_baccarat.py          # Obfuscated Baccarat
```

## Obfuscation Script Usage

The `scripts/obfuscate_code.py` script provides comprehensive code obfuscation:

### Basic Usage
```bash
python scripts/obfuscate_code.py <source_dir> [-o output_dir] [-p project_name]
```

### Parameters
- `source_dir`: Directory containing Python code to obfuscate
- `-o, --output-dir`: Output directory (default: ./obfuscated_output)
- `-p, --project-name`: Project name for configuration (default: sdp_roulette)

### Features
- Automatic PyArmor installation
- Configuration file generation
- Source directory preparation
- Comprehensive obfuscation
- Integrity verification
- Detailed reporting

## Testing

### Test Script

The `test_obfuscated_build.py` script validates obfuscated executables:

```bash
# Test all executables
python test_obfuscated_build.py

# Test specific executable
python test_obfuscated_build.py sdp-vip.pyz
```

### Test Coverage
- **Zipapp Structure**: Validates zipapp file format
- **Module Import**: Tests module import from obfuscated code
- **Execution Test**: Validates executable can run

## Security Considerations

### Production Deployment
- Obfuscated code provides strong protection against reverse engineering
- Anti-debugging features prevent runtime analysis
- Anti-tampering protection detects code modifications
- Private mode ensures no external obfuscation dependencies

### Development Workflow
- Original source code remains unchanged
- Obfuscation is applied only during build process
- Debugging and development use original source code
- CI/CD pipeline automatically applies obfuscation

## Troubleshooting

### Common Issues

1. **PyArmor Installation Failed**
   ```bash
   pip install --upgrade pip
   pip install pyarmor
   ```

2. **Obfuscation Failed**
   - Check Python version compatibility (requires Python 3.8+)
   - Verify source code syntax is correct
   - Ensure sufficient disk space

3. **Import Errors After Obfuscation**
   - Verify all dependencies are included
   - Check module import paths
   - Ensure entry points are correctly specified

4. **Executable Won't Run**
   - Test with `--help` flag first
   - Check Python path and dependencies
   - Verify entry point configuration

### Debug Mode

To debug obfuscation issues:

1. Enable verbose output in PyArmor
2. Check obfuscation report
3. Test individual modules
4. Verify file permissions

## Performance Impact

### Build Time
- Obfuscation adds ~2-3 minutes to build process
- Additional verification steps add ~1 minute
- Total build time increase: ~3-4 minutes

### Runtime Performance
- Minimal impact on runtime performance
- Obfuscation overhead is negligible
- Security checks add minimal latency

## Maintenance

### Regular Updates
- Keep PyArmor updated for latest security features
- Monitor for new obfuscation techniques
- Update obfuscation parameters as needed

### Configuration Updates
- Modify `pyarmor_config.ini` for different security levels
- Adjust obfuscation parameters based on requirements
- Update exclusion patterns as needed

## Support

For issues related to code obfuscation:

1. Check this documentation
2. Review obfuscation logs
3. Test with minimal code examples
4. Contact development team

## Changelog

### Version 1.0.0
- Initial implementation of PyArmor obfuscation
- Added anti-debugging and anti-tampering features
- Integrated with GitHub Actions workflow
- Created comprehensive testing framework
- Added documentation and troubleshooting guides
