#!/usr/bin/env python3
# Python IR transmitter
# Requires pigpio library
# Supports NEC, RC-5 and raw IR.
# Danijel Tudek, Aug 2016

import ctypes
import time
import copy

# This is the struct required by pigpio library.
# We store the individual pulses and their duration here. (In an array of these structs.)
class Pulses_struct(ctypes.Structure):
    _fields_ = [("gpioOn", ctypes.c_uint32),
                ("gpioOff", ctypes.c_uint32),
                ("usDelay", ctypes.c_uint32)]

# Since both NEC and RC-5 protocols use the same method for generating waveform,
# it can be put in a separate class and called from both protocol's classes.
class Wave_generator():
    def __init__(self,protocol):
        self.protocol = protocol
        MAX_PULSES = 12000 # from pigpio.h
        Pulses_array = Pulses_struct * MAX_PULSES
        self.pulses = Pulses_array()
        self.pulse_count = 0

    def add_pulse(self, gpioOn, gpioOff, usDelay):
        self.pulses[self.pulse_count].gpioOn = gpioOn
        self.pulses[self.pulse_count].gpioOff = gpioOff
        self.pulses[self.pulse_count].usDelay = usDelay
        self.pulse_count += 1

    # Pull the specified output pin low
    def zero(self, duration):
        self.add_pulse(0, 1 << self.protocol.master.gpio_pin, duration)

    # Protocol-agnostic square wave generator
    def one(self, duration):
        period_time = 1000000.0 / self.protocol.frequency
        on_duration = int(round(period_time * self.protocol.duty_cycle))
        off_duration = int(round(period_time * (1.0 - self.protocol.duty_cycle)))
        total_periods = int(round(duration/period_time))
        total_pulses = total_periods * 2

        # Generate square wave on the specified output pin
        for i in range(total_pulses):
            if i % 2 == 0:
                self.add_pulse(1 << self.protocol.master.gpio_pin, 0, on_duration)
            else:
                self.add_pulse(0, 1 << self.protocol.master.gpio_pin, off_duration)

# NEC protocol class
class NEC():
    def __init__(self,
                master,
                frequency=38000,
                duty_cycle=0.5,
                leading_pulse_duration=9000,
                leading_gap_duration=4500,
                one_pulse_duration = 562,
                one_gap_duration = 1687,
                zero_pulse_duration = 562,
                zero_gap_duration = 562,
                trailing_pulse = 1):
        self.master = master
        self.wave_generator = Wave_generator(self)
        self.frequency = frequency # in Hz, 38000 per specification
        self.duty_cycle = duty_cycle # duty cycle of high state pulse
        # Durations of high pulse and low "gap".
        # The NEC protocol defines pulse and gap lengths, but we can never expect
        # that any given TV will follow the protocol specification.
        self.leading_pulse_duration = leading_pulse_duration # in microseconds, 9000 per specification
        self.leading_gap_duration = leading_gap_duration # in microseconds, 4500 per specification
        self.one_pulse_duration = one_pulse_duration # in microseconds, 562 per specification
        self.one_gap_duration = one_gap_duration # in microseconds, 1686 per specification
        self.zero_pulse_duration = zero_pulse_duration # in microseconds, 562 per specification
        self.zero_gap_duration = zero_gap_duration # in microseconds, 562 per specification
        self.trailing_pulse = trailing_pulse # trailing 562 microseconds pulse, some remotes send it, some don't
        #print("NEC protocol initialized")

    # Send AGC burst before transmission
    def send_agc(self):
        #print("Sending AGC burst")
        self.wave_generator.one(self.leading_pulse_duration)
        self.wave_generator.zero(self.leading_gap_duration)

    # Trailing pulse is just a burst with the duration of standard pulse.
    def send_trailing_pulse(self):
        #print("Sending trailing pulse")
        self.wave_generator.one(self.one_pulse_duration)

    def send_pause(self):
        self.wave_generator.zero(15000)

    # This function is processing IR code. Leaves room for possible manipulation
    # of the code before processing it.
    def process_code(self, ircode):
        if (self.leading_pulse_duration > 0) or (self.leading_gap_duration > 0):
            self.send_agc()
        for i in ircode:
            if i == "0":
                self.zero()
            elif i == "1":
                self.one()
            else:
                print("ERROR! Non-binary digit!")
                return 1
        if self.trailing_pulse == 1:
            self.send_trailing_pulse()

        self.send_pause()
        return 0

    # Generate zero or one in NEC protocol
    # Zero is represented by a pulse and a gap of the same length
    def zero(self):
        self.wave_generator.one(self.zero_pulse_duration)
        self.wave_generator.zero(self.zero_gap_duration)

    # One is represented by a pulse and a gap three times longer than the pulse
    def one(self):
        self.wave_generator.one(self.one_pulse_duration)
        self.wave_generator.zero(self.one_gap_duration)


class IR():
    def __init__(self, gpio_pin, protocol):
        #print("Starting IR")
        #print("Loading libpigpio.so")
        self.pigpio = ctypes.CDLL('libpigpio.so')
        #print("Initializing pigpio")
        PI_OUTPUT = 1 # from pigpio.h
        self.pigpio.gpioInitialise()
        self.gpio_pin = gpio_pin
        #print("Configuring pin %d as output" % self.gpio_pin)
        self.pigpio.gpioSetMode(self.gpio_pin, PI_OUTPUT) # pin 17 is used in LIRC by default
        #print("Initializing protocol")
        #print("IR ready")

    def process_and_return(self, ircode, protocol_config):
        self.protocol = NEC(self, **protocol_config)
        code = self.protocol.process_code(ircode)
        if code != 0:
            print("Error in processing IR code!")
            return 1
        return self.protocol.wave_generator

    # send_code takes care of sending the processed IR code to pigpio.
    # IR code itself is processed and converted to pigpio structs by protocol's classes.
    def send_code(self, ircode, protocol_config):
        #print("Processing IR code: %s" % ircode)
	#start = time.time()
        self.protocol = NEC(self, **protocol_config)
	#print "protocol creation: ", time.time() - start

	#start = time.time()
        code = self.protocol.process_code(ircode)
        if code != 0:
            print("Error in processing IR code!")
            return 1
	#print "processing: ", time.time() - start

	#start = time.time()
        clear = self.pigpio.gpioWaveClear()
        if clear != 0:
            print("Error in clearing wave!")
            return 1
	#print "clearing", time.time() - start


	#start = time.time()
        pulses = self.pigpio.gpioWaveAddGeneric(self.protocol.wave_generator.pulse_count, self.protocol.wave_generator.pulses)
	#print "pulse_count: ", self.protocol.wave_generator.pulse_count
	#print "Pulses: ", self.protocol.wave_generator

        if pulses < 0:
            print("Error in adding wave!")
            return 1
        wave_id = self.pigpio.gpioWaveCreate()
        # Unlike the C implementation, in Python the wave_id seems to always be 0.
        if wave_id >= 0:
            #print("Sending wave...")
            result = self.pigpio.gpioWaveTxSend(wave_id, 0)
            if result >= 0:
                #print("Success! (result: %d)" % result)
                pass
            else:
                print("Error! (result: %d)" % result)
                return 1
        else:
            print("Error creating wave: %d" % wave_id)
            return 1

	#print "creating: ", time.time() - start

	#start = time.time()
        while self.pigpio.gpioWaveTxBusy():
            #time.sleep(0.1)
            pass
        #print("Deleting wave")
        self.pigpio.gpioWaveDelete(wave_id)
        #self.pigpio.gpioTerminate()
	#print "Cleanup: ", time.time() - start


    def send_processed_code(self, code):
	#start = time.time()
        pulses = self.pigpio.gpioWaveAddGeneric(code.pulse_count, code.pulses)
	#print "pulse_count: ", self.protocol.wave_generator.pulse_count
	#print "Pulses: ", self.protocol.wave_generator

        if pulses < 0:
            print("Error in adding wave!")
            return 1
        wave_id = self.pigpio.gpioWaveCreate()
        # Unlike the C implementation, in Python the wave_id seems to always be 0.
        if wave_id >= 0:
            #print("Sending wave...")
            result = self.pigpio.gpioWaveTxSend(wave_id, 0)
            if result >= 0:
                #print("Success! (result: %d)" % result)
                pass
            else:
                print("Error! (result: %d)" % result)
                return 1
        else:
            print("Error creating wave: %d" % wave_id)
            return 1

	#print "creating: ", time.time() - start

	#start = time.time()
        while self.pigpio.gpioWaveTxBusy():
            #time.sleep(0.1)
            pass
        #print("Deleting wave")
        self.pigpio.gpioWaveDelete(wave_id)
        #self.pigpio.gpioTerminate()
	#print "Cleanup: ", time.time() - start


    # send_code takes care of sending the processed IR code to pigpio.
    # IR code itself is processed and converted to pigpio structs by protocol's classes.
    def send_code(self, ircode, protocol_config):
        #print("Processing IR code: %s" % ircode)
	#start = time.time()
        self.protocol = NEC(self, **protocol_config)
	#print "protocol creation: ", time.time() - start

	#start = time.time()
        code = self.protocol.process_code(ircode)
        if code != 0:
            print("Error in processing IR code!")
            return 1
	#print "processing: ", time.time() - start

	#start = time.time()
        clear = self.pigpio.gpioWaveClear()
        if clear != 0:
            print("Error in clearing wave!")
            return 1
	#print "clearing", time.time() - start


	#start = time.time()
        pulses = self.pigpio.gpioWaveAddGeneric(self.protocol.wave_generator.pulse_count, self.protocol.wave_generator.pulses)
	#print "pulse_count: ", self.protocol.wave_generator.pulse_count
	#print "Pulses: ", self.protocol.wave_generator

        if pulses < 0:
            print("Error in adding wave!")
            return 1
        wave_id = self.pigpio.gpioWaveCreate()
        # Unlike the C implementation, in Python the wave_id seems to always be 0.
        if wave_id >= 0:
            #print("Sending wave...")
            result = self.pigpio.gpioWaveTxSend(wave_id, 0)
            if result >= 0:
                #print("Success! (result: %d)" % result)
                pass
            else:
                print("Error! (result: %d)" % result)
                return 1
        else:
            print("Error creating wave: %d" % wave_id)
            return 1

	#print "creating: ", time.time() - start

	#start = time.time()
        while self.pigpio.gpioWaveTxBusy():
            #time.sleep(0.1)
            pass
        #print("Deleting wave")
        self.pigpio.gpioWaveDelete(wave_id)
        #self.pigpio.gpioTerminate()
	#print "Cleanup: ", time.time() - start

    def cleanup(self):
        print("Terminating pigpio")
        self.pigpio.gpioTerminate()

if __name__ == "__main__":
    protocol = "RC-5"
    gpio_pin = 17
    protocol_config = dict(one_duration = 820,
                            zero_duration = 820)
    ir = IR(gpio_pin, protocol, protocol_config)
    ir.send_code("11000000001100")
    print("Exiting IR")
