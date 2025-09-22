# Studio API Error Signal Tests

This directory contains test scripts for sending error signals to the Studio API WebSocket server.

## Files

### Python Version
- `test_err_sig.py` - Main Python test script (recommended)
- `test_sdp_down.py` - Test for SDP down status updates
- `ws_client.py` - WebSocket client library
- `ws_sr.py` - Roulette game status updates

### JavaScript Versions
- `test_err_sig.js` - Full-featured Node.js test script (requires npm packages)
- `test_err_sig_simple.js` - Simple Node.js test script (no external dependencies)
- `test_err_sig_browser.html` - Browser-based test interface

### Configuration
- `../conf/ws.json` - WebSocket server configuration

## Usage

### Python (Recommended)
```bash
# Install dependencies
source ../../venv/bin/activate

# Run error signal test
python test_err_sig.py

# Run SDP down test
python test_sdp_down.py
```

### JavaScript (Node.js)
```bash
# Install dependencies (if using full version)
npm install

# Run full test suite
node test_err_sig.js

# Run simple test
node test_err_sig_simple.js
```

### Browser
1. Open `test_err_sig_browser.html` in a web browser
2. Click "Test Single Error Signal" or "Test Multiple Error Signals"
3. View real-time logs and results

## Error Signal Specification

The error signals follow this specification:

```javascript
// WebSocket Connection
const ws = new WebSocket('ws://localhost:8080?id=ARO-001_dealerPC&token=MY_TOKEN');

// Signal Types
type Signal = {
  msgId: string,
  metadata: {
    title: string,
    description: string,
    code: string,
    suggestion: string
  }
}

type ServiceException = {
  signal: Signal,
  cmd: any
}

// Error Signal Message
const msg = {
  event: 'exception',
  data: {
    signal: signal,
    cmd: {}
  }
}
```

## Configuration

Update `../conf/ws.json` to match your server settings:

```json
{
    "server_url": "ws://100.64.0.160:8081",
    "device_name": "dealerPC",
    "token": "0000",
    "tables": [
        {
            "table_id": "ARO-001",
            "name": "ARO-001"
        }
    ]
}
```

## Test Scenarios

### Single Error Signal
- Sends one roulette sensor stuck error signal
- Tests basic WebSocket connection and message format

### Multiple Error Signals
- Sends multiple different error types:
  - SENSOR STUCK (ARE.3)
  - CAMERA CONNECTION LOST (ARE.4)
  - SDP SERVICE DOWN (ARE.5)

## Error Codes

- `ARE.3` - Sensor stuck (Hardware issue)
- `ARE.4` - Camera connection lost (Network issue)
- `ARE.5` - SDP service down (Service issue)

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Check server URL and port in configuration
   - Verify WebSocket server is running

2. **Invalid Credentials**
   - Verify token in configuration matches server
   - Check device name format

3. **400/500 Errors**
   - Ensure message format matches specification exactly
   - Check that no extra parameters are included in metadata

### Debug Mode

Enable detailed logging by setting log level to DEBUG in the configuration.

## Dependencies

### Python
- `asyncio` - Async programming
- `websockets` - WebSocket client
- `json` - JSON handling
- `uuid` - UUID generation

### JavaScript
- `ws` - WebSocket client (Node.js version)
- `uuid` - UUID generation (Node.js version)
- Built-in WebSocket API (browser version)

## License

MIT License - See project root for details.
