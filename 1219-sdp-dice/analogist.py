#!/usr/bin/env python

import platform
import time
import sys
import asyncio
from typing import Iterable

# 根據操作系統選擇適當的GPIO實現
if platform.system() == "Linux" and "raspberrypi" in platform.uname().version.lower():
    import pigpio
    USE_REAL_GPIO = True
else:
    USE_REAL_GPIO = False

class MockPigpio:
    def __init__(self):
        self.connected = True
        self._pwm_channels = {}
        print("使用 GPIO 模擬器")
            
    def hardware_PWM(self, gpio_pin, frequency, duty_cycle):
        if gpio_pin not in self._pwm_channels:
            self._pwm_channels[gpio_pin] = {
                "frequency": frequency,
                "duty_cycle": duty_cycle
            }
        else:
            self._pwm_channels[gpio_pin]["frequency"] = frequency
            self._pwm_channels[gpio_pin]["duty_cycle"] = duty_cycle
            
        duty_percent = duty_cycle / 10000.0
        print(f"PWM 輸出 - PIN:{gpio_pin} 頻率:{frequency}Hz 工作週期:{duty_percent:.1f}%")
            
    def stop(self):
        print("停止 GPIO 模擬器")
        self._pwm_channels.clear()

    def connected(self):
        return True

print("Imports finished")

class AController:
    '''
    Duty cycle: 0..1
    '''
    def __init__(self, duty=0.5, pwm_freq=24000, gpio_pin=13, sample_freq_hz=100):
        print("Initing")
        self.duty = AController.dutyFix(duty)
        self.PWM_FREQ = pwm_freq
        self.PWM_PIN = gpio_pin
        self.PWM_DUTY_CYCLE = self.duty*1000000
        self.SAMPLE_FREQ_HZ = sample_freq_hz
        self.SAMPLE_INTERVAL_S = 1./self.SAMPLE_FREQ_HZ
        
        # 根據平台選擇GPIO實現
        if USE_REAL_GPIO:
            self.pi = pigpio.pi()
            if not self.pi.connected:
                print("CRITICAL: 無法連接到pigpio守護程序。退出")
                exit(1)
            print("LOG: Pigpio已連接")
        else:
            self.pi = MockPigpio()
            print("LOG: GPIO模擬器已連接")

    async def run(self, duty=.5678901234, timeSec=0):
        if timeSec == 0:
            timeSec = self.SAMPLE_INTERVAL_S
        self.setDuty(duty)
        self.pi.hardware_PWM(self.PWM_PIN, self.PWM_FREQ, self.PWM_DUTY_CYCLE)
        await asyncio.sleep(timeSec)

    async def runRoll(self, waveform, sample_freq_hz:float=100):
        self.SAMPLE_FREQ_HZ = sample_freq_hz
        self.SAMPLE_INTERVAL_S = 1./self.SAMPLE_FREQ_HZ
        
        # 處理異步生成器
        if hasattr(waveform, '__aiter__'):
            async for x in waveform:
                await self.run(duty=x, timeSec=self.SAMPLE_INTERVAL_S)
        # 處理普通迭代器
        else:
            for x in waveform:
                await self.run(duty=x, timeSec=self.SAMPLE_INTERVAL_S)

    def setDuty(self, duty):
        fduty = AController.dutyFix(duty)
        self.duty = fduty
        self.PWM_DUTY_CYCLE = int(self.duty*1000000)

    @staticmethod
    def dutyFix(duty):
        try:
            fduty = float(duty)
        except:
            print(f"ERROR: could not convert '{duty}' to number. Setting to '0'")
            fduty = 0
        if fduty<0:
            print(f"WARNING: duty cycle {fduty}<0. Setting to 0")      
            fduty = 0
        if fduty>1:
            print(f"WARNING: duty cycle {fduty}>1. Setting to 1.")
            fduty = 1
        return fduty

    def close(self):
        print("Stopping emulator")
        self.pi.hardware_PWM(self.PWM_PIN, 0, 0)
        self.pi.stop()
    
if __name__ == "__main__":
    ac = AController()
    mv = 100
    asyncio.run(ac.runRoll(((x%mv)/mv for x in range(100*mv))))
    ac.close()
