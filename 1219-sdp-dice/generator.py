import analogist as ao
import argparse
import logging
import time
from math import pi, cos
import asyncio
from typing import Iterable
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from collections import deque

log = None
SAMPLING_FREQ_HZ=1000
piout = ao.AController(pwm_freq=200000, sample_freq_hz=SAMPLING_FREQ_HZ)

PLOT_WINDOW = 1000  # 顯示最近的1000個採樣點
data_buffer = deque(maxlen=PLOT_WINDOW)
fig, ax = plt.subplots()
line, = ax.plot([], [])

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

def parseArgs():
    parser = argparse.ArgumentParser(description="RPI analog output PWM generator for dice shaker.\n\
Modes parameters:\n\
chirp:  p1 - starting frequency, p2 - end frequency\n\
sin:    p1 - frequency, p2 - number of wave packets\n\
saw:    p1 - frequency, p2 - position of peak in period 0..1\n\
meander:    p1 - frequency, p2 - smooth factor msec\n\
noise:  p1 - smooth factor msec, p2 - reserved\n\
sinharm:    \
", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument( '-t', '--time', type=float, help="Time in seconds (float)", default=5)
    parser.add_argument( '-s', '--shape', choices=['sin', 'saw', 'meander', 'chirp', 'random', 'noise', 'sinharm'], help="Shape of the waveform", default='random' )
    parser.add_argument( '-a', '--amplitude', type=float,  help="Amplitude (0 to 1)", default=1.) # Allow values between 0.0 and 1.0
    verbosity_group = parser.add_mutually_exclusive_group()
    verbosity_group.add_argument( '-q', '--quiet', action='count', default=0, help="Suppress output (err level). Use -qq for Quite quiet(crit level). And -qqq for Quompletely Quietest quiet")
    verbosity_group.add_argument( '-v', '--verbose', action='count', default=0, help="Verbose mode (info level). Use -vv for very verbose (debug level).")
    parser.add_argument( '-p1', type=float, help="First waveform parameter (float)", default=1.)
    parser.add_argument( '-p2', type=float, help="Second waveform parameter (float)", default=1.)
    parser.add_argument( '-e', '--end-level', nargs='?', type=float, default=None, const=0.9, help="Analog level of idle state. Default: stay where waveform finished")
    
    # Parse arguments
    args = parser.parse_args()

    # Handle verbosity to be passed to logger
    verbLevel = args.verbose - args.quiet + 3 # magic constant to make 0 suppress even critical and 5 allow debug
    args.verbose = verbLevel
    
    return args

def fixArguments(args):
    # Fix amplitude
    if args.amplitude < 0:
        log.warning("Amplitude<0. Setting to 0")
        args.amplitude = 0
    if args.amplitude > 1:
        log.warning("Amplitude>1. Setting to 1")    
        args.amplitude = 1

    # Fix time
    if args.time<=0:
        log.warning("Negative time detected: {args.time}. Setting to default 5sec")
        args.time = 5

    return args

def genChirp(time_sec: float, startFreq: float, endFreq: float, amp: float, sampling_freq: int):
    log.debug("Chirping with params:"+str((time_sec, startFreq, endFreq, amp, sampling_freq)))
    sampleNum = int(time_sec*sampling_freq)
    waveform = (amp*.5*(1-cos(x*(startFreq - (startFreq-endFreq)*(x/sampleNum))*2*pi/sampling_freq)) for x in range(sampleNum))
    return waveform

def genSin(time: float, freq_hz: float, meander_cycles: int, amp: float, sampling_freq: int):
    ''' will generate freq_hz sine wave and will modulate it 1-0-1 meander_cycles times '''
    log.debug("Sinning with params:"+str((time,freq_hz, meander_cycles, amp, sampling_freq)))
    if meander_cycles<=0:
        log.warning("Non-positive meander cycles: {meander_cycles}. Resetting to 1")
        meander_cycles = 1
    
    sampleNum = int(time*sampling_freq)
    multipliersNum = 2*meander_cycles-1
    flipIn = sampleNum/multipliersNum
    waveform = (amp*0.5*(1-cos(x*freq_hz*2*pi/sampling_freq))  if x%(2*flipIn)<flipIn else 0 for x in range(sampleNum))
    return waveform

def genSaw(time_sec: float, freq_hz: float, peakPos: float, amp: float, sampling_freq: int):
    ''' peakPos is 0..1 which is responsible for this: |\ .. /\ .. /| '''
    log.debug("Sawing with params:"+str((time_sec,freq_hz, peakPos, amp, sampling_freq)))
    if peakPos < 0:
        log.warning("Peak position is negative: {peakPos}. Resetting to 0")
        peakPos = 0
    if peakPos > 1:
        log.warning("Peak position is too big: {peakPos}. Resetting to 1")
        peakPos = 1
    sampleNum = int(time_sec*sampling_freq)
    rising = int(sampling_freq/freq_hz*(peakPos))
    falling = int(sampling_freq/freq_hz*(1-peakPos))
    period = int(sampling_freq/freq_hz)
    waveform = (amp*(x%period)/rising if x%period<rising else amp*(1-(x%period-rising)/falling) for x in range(sampleNum))
    return waveform

def _smooth(input_gens: Iterable, length: float)-> Iterable:
    ''' Running average '''
    from collections import deque
    accu = 0
    window = deque(maxlen = length)
    iiterator = iter(input_gens) # this will make lists and generators become positively Iterable
    for _ in range(length):
        try:
            x = next(iiterator)
        except StopIteration:
            return
        window.append(x)
        accu+=x
        yield accu/length
    for x in iiterator:
        # Getting blind popleft resulted in errors sometimes
        try: 
            oldest = window.popleft()
        except IndexError:
            return
        window.append(x)
        accu += x - oldest
        yield accu/length
    
def genMeander(time_sec: float, freq_hz: float, smoothing_msec: float, amp: float, sampling_freq: int):
    ''' smoothing will roll average the meander '''
    log.debug("Meandring with params:"+str((time_sec, freq_hz, smoothing_msec, amp, sampling_freq)))
    smoothing = smoothing_msec*sampling_freq/1000
    ismoothing = int(smoothing)
    if smoothing < 0:
        log.warning("Smoothing is negative: {smoothing}. Setting to 0")
        smoothing = 0
    period = sampling_freq/freq_hz
    sampleNum = int(time_sec*sampling_freq)
    meander = list((amp if x%period < period/2 else 0 for x in range(sampleNum)))
    smeander = _smooth(meander, ismoothing)
    def _positify(ingen):
        for x in ingen:
            yield max(0,x)
    return _positify(smeander)

def genNoise(time_sec:float, smoothing_msec:float, param2: float, amp: float, sampling_freq: int):
    ''' 
    Generate pseudo-noise, then make it 12 samples per second, stretch, smooth 
    Pseudo-noise means that consecutive steps should be at least .4 amplitude apart
    '''
    log.debug("Noising with params:"+str((time_sec, smoothing_msec, param2, amp, sampling_freq)))
    smoothing_samples = smoothing_msec*sampling_freq/1000
    ismoothing_samples = int(smoothing_samples)
    if smoothing_samples < 0:
        log.warning("Smoothing is negative: {smoothing_samples}. Setting to 0")
        smoothing_samples = 0
    NOISE_RATE_HZ = 12
    from random import random
    noise_raw = (random() for _ in range(int(NOISE_RATE_HZ*time_sec)))
    def _fixNoiseAmplitudes(input_gens, delta=.3):
        prev = 0
        for x in input_gens:
            diff = x-prev
            prev = x
            if abs(diff)<delta:
                yield (x + diff/abs(diff)*0.5)%1.
            yield x
    def _stretch(input_gens, factor: int):
        for x in input_gens:
            for _ in range(factor):
                yield x
    stretch_factor = int(sampling_freq/NOISE_RATE_HZ)
    snoise = _smooth(_stretch(_fixNoiseAmplitudes(noise_raw, delta=.3), stretch_factor), ismoothing_samples)
    return snoise 
    
def genSinharm(time_sec: float, freq: int, num_harm: float, amp: float, sampling_freq: int):
    ''' Generate signal of freq with num_harm harmonics. Amplitudes are not controllable per-harmonic '''
    log.debug("Harmonising with params:" + str((time_sec, freq, num_harm, amp, sampling_freq)))
    sample_num = int(time_sec*sampling_freq) 
    num_harm = int(num_harm)
    def _nextHarm(phase, num_harm):
        rv = 0
        for n in range(1,2+num_harm):
            rv+=cos((2*(n-1)+1)*phase)
        return rv/(num_harm+1)/2+.5
    waveform = (amp*_nextHarm(x*2*pi*freq/sampling_freq, num_harm) for x in range(sample_num))
    listform = list(waveform)
    log.debug(f"Min-max of sin harm: {min(listform)} : {max(listform)}")
    return listform
    
def _random_args(shape: str):
    ''' generate sane random parameters for given shape 
    Return (time, p1, p2, amplitude) '''
    log.warning("Random modes are not set up to be production-ready. Used for demonstration purposes only")
    from random import random, randint

    TIME_MIN_S = 4
    TIME_MAX_S = 10
    time = TIME_MIN_S + random()*(TIME_MAX_S-TIME_MIN_S)

    AMP_MIN = .8
    AMP_MAX = 1
    amp = AMP_MIN + random()*(AMP_MAX-AMP_MIN) # Warning: will reroll for sinharm because it is too evil

    FRE_MAX = 15
    FRE_MAX_MIN = 11
    if shape == 'chirp':
        FRE_MIN = 1
        start_freq = FRE_MIN + random()*(FRE_MAX - FRE_MIN)
        end_freq = FRE_MAX_MIN + random()*(FRE_MAX - FRE_MAX_MIN)
        p1, p2 = start_freq, end_freq
    if shape == 'sin':
        MAX_WAVE_PACKETS = 4
        freq = FRE_MAX_MIN + random()*(FRE_MAX - FRE_MAX_MIN)
        cycles = randint(1,MAX_WAVE_PACKETS)
        p1, p2 = freq, cycles
    if shape == 'saw':
        freq = FRE_MAX_MIN + random()*(FRE_MAX - FRE_MAX_MIN)
        pos_peak = random()
        p1, p2 = freq, pos_peak
        AMP_MIN_SAW = .7
        amp = min(amp, AMP_MIN_SAW)
    if shape == 'meander':
        FRE_MIN_MEANDER = 4
        FRE_MAX_MEANDER = 9
        freq = FRE_MIN_MEANDER + random()*(FRE_MAX_MEANDER - FRE_MIN_MEANDER)
        smooth_max_sec = min(1./freq/8, 20)
        smooth_msec = random()*smooth_max_sec*1000
        AMP_MIN_MEANDER = .6
        AMP_MAX_MEANDER = .8
        amp = AMP_MIN_MEANDER + (AMP_MAX_MEANDER - AMP_MIN_MEANDER)*random()
        p1, p2 = freq, smooth_msec
    if shape == 'noise':
        smooth_ms = 1000*1/18/2* random()
        p1, p2 = smooth_ms, 1
    if shape == 'sinharm':
        fundamental = randint(3,FRE_MAX)
        num_harm_min = max(0, 14-fundamental)
        num_harm = randint(num_harm_min, 10)
        amp = .4+.21*random()
        p1, p2 = fundamental, num_harm
    return time, p1, p2, amp
    
def init_plot():
    ax.set_xlim(0, PLOT_WINDOW)
    ax.set_ylim(-0.1, 1.1)
    ax.grid(True)
    return line,

def update_plot(frame):
    line.set_data(range(len(data_buffer)), list(data_buffer))
    return line,

class PlotterMixin:
    def plot_value(self, value):
        data_buffer.append(value)

async def plot_and_generate(generator_func, *args):
    # 設置動畫
    ani = FuncAnimation(fig, update_plot, init_func=init_plot, 
                       interval=20, blit=True)
    plt.show(block=False)
    
    # 生成並繪製波形
    for value in generator_func(*args):
        data_buffer.append(value)
        plt.pause(0.001)  # 給繪圖一個更新的機會
        yield value
    
    # 不要關閉視窗，而是保持顯示
    plt.ioff()  # 關閉互動模式
    plt.show()  # 阻塞式顯示

if __name__ == "__main__":
    args = parseArgs()
    log = init_logger(args.verbose)
    args = fixArguments(args)
    log.info("Shake it baby")
    if args.shape == 'random':
        from random import randint
        options =['sin', 'saw', 'meander', 'chirp', 'noise', 'sinharm'] 
        args.shape = options[randint(0,len(options)-1)]
        args.time, args.p1, args.p2, args.amplitude = _random_args(args.shape)
        log.info(f"Rolled random shaking mode: {args.shape}")
    if args.shape == 'chirp':
        asyncio.run(piout.runRoll(genChirp(args.time, args.p1, args.p2, args.amplitude, SAMPLING_FREQ_HZ), sample_freq_hz=SAMPLING_FREQ_HZ))
    if args.shape == 'sin':
        asyncio.run(piout.runRoll(genSin(args.time, args.p1, args.p2, args.amplitude, SAMPLING_FREQ_HZ), sample_freq_hz=SAMPLING_FREQ_HZ))
    if args.shape == 'saw':
        asyncio.run(piout.runRoll(genSaw(args.time, args.p1, args.p2, args.amplitude, SAMPLING_FREQ_HZ), sample_freq_hz=SAMPLING_FREQ_HZ))
    if args.shape == 'meander':
        wave_gen = genMeander(args.time, args.p1, args.p2, args.amplitude, SAMPLING_FREQ_HZ)
        async def run_wave():
            ani = FuncAnimation(fig, update_plot, init_func=init_plot, 
                              interval=20, blit=True)
            plt.show(block=False)
            
            for value in wave_gen:
                data_buffer.append(value)
                plt.pause(0.001)
                yield value
            
            plt.close()
        
        asyncio.run(piout.runRoll(run_wave(), sample_freq_hz=SAMPLING_FREQ_HZ))
    if args.shape == 'noise':
        asyncio.run(piout.runRoll(genNoise(args.time, args.p1, args.p2, args.amplitude, SAMPLING_FREQ_HZ), sample_freq_hz=SAMPLING_FREQ_HZ))
    if args.shape == 'sinharm':
        asyncio.run(piout.runRoll(genSinharm(args.time, args.p1, args.p2, args.amplitude, SAMPLING_FREQ_HZ), sample_freq_hz=SAMPLING_FREQ_HZ))

    if args.end_level is not None:
        asyncio.run(piout.run(duty=args.end_level, timeSec=.1))
