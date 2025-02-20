#!/usr/bin/env python

import argparse
import logging
import argparse
import time
import asyncio
from dotenv import dotenv_values
import json

server = None
driver = None
ledder = None

log = None
mqttc = None
runMotor = None
motorBuys = None

def parseArgs():
    parser = argparse.ArgumentParser(description="Launcher for dice-shaker. Will connect to MQTT server, control shaker motor driver and LED lights", formatter_class=argparse.RawTextHelpFormatter)
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument('-q', '--quiet', action='count', default=0, help="Suppress output (err level). Use -qq for Quite quiet(crit level). And -qqq for Quompletely Quietest quiet")
    verbosity_group.add_argument('-v', '--verbose', action='count', default=0, help="Verbose mode (info level). Use -vv for very verbose (debug level).")
    parser.add_argument('-p', '--mqtt_port', type=int, default=1883, help="Broker server mqtt port")
    parser.add_argument('-a', '--mqtt_server', type=str, default='rnd-al.local', help="Broker server mqtt address")
    parser.add_argument('-m', '--motor_off',  action='store_true', default=False, help="Act as if motor does not exist")
    parser.add_argument('-l', '--led_off',  action='store_true', default=False, help="Do not use report pin for LED driving")

    # Parse arguments
    args = parser.parse_args()

    # Handle verbosity to be passed to logger
    verbLevel = args.verbose - args.quiet + 3 # magic constant to make 0 suppress even critical and 5 allow debug
    args.verbose = verbLevel

    return args

def fixSettings(s):
    s['mqtt_port'] = int(s['mqtt_port'])
    s['driv_pin_apos'] = int(s['driv_pin_apos'])
    s['driv_pin_ena'] = int(s['driv_pin_ena'])
    s['led_pin_state'] = int(s['led_pin_state'])
    if s['led_off']:
        s['led_pin_state'] = None
    return s

class ColouredLoggerFormatter(logging.Formatter):
    COLOURS = {"DEBUG": "\033[90m", "INFO":"\033[97m", "WARNING":"\033[93m", "ERROR":"\033[91m", "CRITICAL":"\033[31m", "RESET":"\033[0m"}

    def format(self, record):
        col = self.COLOURS.get(record.levelname, self.COLOURS["RESET"])
        reset = self.COLOURS["RESET"]
        timestamp = time.strftime("%H-%M-%S", time.localtime(record.created))
        message_formatted = f"\033[90m{timestamp}/{record.levelname[:3]}/{record.funcName}: {col}{record.msg}{reset}"
        return message_formatted

def init_logger(verbLevel):
    logger = logging.getLogger("CLogger")
    IGNORE_ALL_LEVEL = 60
    logger.setLevel([IGNORE_ALL_LEVEL, logging.CRITICAL, logging.ERROR, logging.WARNING, logging.INFO, logging.DEBUG][verbLevel])
    handler = logging.StreamHandler()
    handler.setFormatter(ColouredLoggerFormatter())
    logger.addHandler(handler)
    return logger

def initMQTT(addr:str, port:str, user:str, password:str, listenChan:str, sayChan:str, shakerID:str='none', loglevel=3):
    import mqtt
    mqtt.log = log
    #mqtt.log = mqtt.init_logger(0)
    log.debug("before")
    mqttc = mqtt.init(user, password, loglevel=loglevel, serverAddr=addr, port=port, listenThis=listenChan, sayHere=sayChan, shakerID=shakerID)
    log.debug("after")
    return mqttc

def initMotor(pin_pwm, pin_state):
    import generator
    generator.log = log
    # Init with pin report will init state report automatically when runroll is executed
    piOut = generator.init(gpio_pin=pin_pwm , pin_shaking_report=pin_state)
    
    def runMotor(shape, time, p1, p2, amplitude=1, endLevel=0.8, infinum=0.2, supremum=1.):
        waveform = generator.genShapeWaveform(shape, time, p1, p2, amplitude=amplitude, sampling_freq=generator.SAMPLING_FREQ_HZ, infinum=infinum, supremum=supremum)
        asyncio.run(piOut.runRoll(waveform, sample_freq_hz=generator.SAMPLING_FREQ_HZ))
        # TODO: make it smooth maybe
        asyncio.run(piOut.run(duty=endLevel, timeSec=0))
    def motorBusy():
        return 1 if not piOut.motorIdle else 0
    return runMotor, motorBusy


def init():
    # Set up mqtt client and command to run motor with additional status pin
    global mqttc, runMotor, motorBusy
    env = dotenv_values('.env')
    # Convert to dictionary
    args = vars(parseArgs())
    # Make args override .env settings. Perhaps to be reconsidered in the future
    settings = {**env, **args}
    # Basically typecasting. Also sets led pin to none if -l flag is set
    settings = fixSettings(settings)

    global log
    log = init_logger(settings['verbose'])
    log.debug(f"Run parameters:\n{settings}")
    
    s = settings
    # 修改 MQTT 主題設定
    s['mqtt_listen'] = "ikg/idp/dice/command"  # 接收命令的主題
    s['mqtt_say'] = "ikg/idp/dice/response"    # 發送回應的主題
    
    mqttc = initMQTT(s['mqtt_server'], s['mqtt_port'], s['mqtt_user'], s['mqtt_pass'], 
                     s['mqtt_listen'], s['mqtt_say'], 
                     shakerID=s['mqtt_shaker_id'], 
                     loglevel=s['verbose'])

    if s['motor_off']:
        fdummy = lambda *args, **kwargs: None
        ffalse = lambda *args, **wargs: False
        runMotor, motorBusy = fdummy, ffalse
    else:
        runMotor, motorBusy = initMotor(s['driv_pin_apos'], s['driv_pin_ena'])
    log.debug("One cycle of shaker for init")
    # runMotor('sin', .2, 5, 0, amplitude=.2)

def parseCommand(command):
    if not command:
        return None
    command = command.decode("utf-8") 
    
    # 只處理 JSON 格式的 shake command
    try:
        cmd_data = json.loads(command)
        if isinstance(cmd_data, dict):
            # 只接受 shake 命令
            if cmd_data.get('command') == 'shake':
                log.debug(f"Received shake command: {command}")
                return ['shake', cmd_data.get('arg', {})]
            else:
                # 忽略非 shake 命令
                log.debug(f"Ignoring non-shake command: {cmd_data.get('command')}")
                return None
    except json.JSONDecodeError:
        log.error(f"Invalid JSON command: {command}")
        return None
    
    return None

def executeCycle(parameters:dict):
    lshapes = ['sin', 'sinharm', 'chirp', 'meander', 'saw', 'noise']
    shapeNum = parameters['pattern']
    try:
        shape = lshapes[shapeNum]
    except IndexError:
        log.error(f"Requested shape number is IndexError: {shapeNum}/{len(lshapes)}")
        return True
    p = parameters
    runMotor(shape, p['duration'], p['parameter1'], p['parameter2'], amplitude=p['amplitude'])
    return False

def executeMicroshake():
    runMotor('sin', 1, 0, 1, amplitude=.05)

def executeShake():
    """Execute shake command with predefined parameters"""
    log.debug("Executing shake command with sine wave")
    # 使用 sine wave，持續 7 秒
    runMotor('sin', 7, 5, 0, amplitude=0.8)
    return False

def obeyTheLeader(command:str, error=0):
    parsedCommand = parseCommand(command)
    if parsedCommand is None:
        # 不是 shake 命令就直接返回，不記錄錯誤
        return error

    order = parsedCommand[0]
    if order == 'shake':
        log.debug(f"Leader says 'Shake the dice!'")
        if executeShake():
            error = 4
    # 移除其他命令的處理
    else:
        log.warning(f"Unexpected command: {order}")
    
    return error

def run():
    shape = 'sin'
    timeShakeSec = 7
    timeIdleSec = 12
    p1 = 10
    p2 = 0
    amp = 1
    inf = .1
    sup = .9
    error = 0
    errReported = False
    while True:
        command = mqttc.message
        if command is not None:
            mqttc.message = None
            error = obeyTheLeader(command, error=error)
            if error == 0:
                errReported = False
            else:
                if not errReported:  
                    mqttc.send(f'E{error}')
                    errReported = True
        time.sleep(.1)

if __name__ == "__main__":
    init()
    try:
        log.info("Shaker client started. Waiting for commands...")
        run()
    except KeyboardInterrupt:
        log.info("Shutting down shaker client...")
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise
    
