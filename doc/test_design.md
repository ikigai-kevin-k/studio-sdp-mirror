# Test Design

## Unit Tests

### Test LOS Communication

#### Test Case 1: Check HTTP communication OK

#### Test Case 2: Check WebSocket Communication OK

#### Test Case 3: Receive Game Parameters Settings Command from LOS

### Test Roulette Communication

#### Test Case 1: Check Serial Port Communication OK

#### Test Case 2: Get Roulette Polling Results


### Test State Machine Data Processing

#### Test Case 1: Serial Data Processing Functionality

#### Test Case 2: State Machine Transition 

## Integration Tests

### Test Scenario 1

LOS sends Game Parameters Settings Command to SDP via HTTP, and SDP forwards the command to Roulette via Serial Port. The roulette then changes its game parameters accordingly. The roulette then sends the Polling Results back to SDP via Serial Port, and SDP forwards the results to LOS via HTTP.