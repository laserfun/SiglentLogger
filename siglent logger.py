# -*- coding: utf-8 -*-
"""
This program acquires spectra using a ANDO 6315E and rotates a Thorlabs K10CR1 rotation stage.
By Grace Kerber and Dan Hickstein
This program requires that the Thorlabs Kinesis drivers are in the same folder as this program.
pyVISA is used to communicate with the ANDO OSA using GPIB.
"""
from __future__ import print_function
import ctypes as c
import numpy as np
import os
import time
import sys
import datetime
import platform
import pyvisa as visa


delay = 2  # time delay between points in seconds
num_points = 1e9  # number of points to collect
# Determines what angles to collect data at

# attempt to make data align to overall grid instead of fixed delay


# set up the siglent:
print('Looking for the Siglent')
rm = visa.ResourceManager()
print('    Found the following instruments:', rm.list_resources())

siglentFound = False
for device in rm.list_resources():
    print('    Checking %s' % device, end='')
    sys.stdout.flush()
    if 'SSA' in device:
        print('  <---- This is the one!')
        # Replace with specific USB information from scope
        sds = rm.open_resource(device)
        sds.write("*IDN?")
        answer = sds.read()
        print('    *IDN? > ' + answer)
        sds.write(":INITiate:CONTinuous OFF")
        siglentFound = True
    else:
        print('  Nope.')

if siglentFound == False:
    raise ValueError('The Siglent could not be found! Is it connected and powered on? Please note, the siglent does not seem to work with pyvisa-py. You need the real National Instruments VISA. Sorry David.')



# ---Create Base Directory for saving data
today = datetime.datetime.now().strftime("%Y-%m-%d")
cwd = os.getcwd()
base_dir = os.path.join(cwd, today)
if not(os.path.isdir(base_dir)):
    os.mkdir(base_dir)

run_counter = 1
run_folder = 'run %04i' % (run_counter)

# find the first available file name:
while os.path.isdir(os.path.join(base_dir, run_folder)):
    run_counter = run_counter + 1
    run_folder = 'run %04i' % (run_counter)
new_base_dir = os.path.join(base_dir, run_folder)
os.mkdir(new_base_dir)


logfile = open(os.path.join(new_base_dir, 'LOGFILE.txt'), 'w')
time_now = datetime.datetime.now().strftime("%Y-%m-%d %X")
logfile.write('Start time\t'+time_now+'\n')

print('Saving to:   %s\n' % (new_base_dir))


def get_siglent_settings(sds, display=False):
    
    output_text = ''
    
    # datetime
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %X")
    output_text += 'Current data and time: %s\n'%time_now
    
    # rbw
    sds.write(':SENSe:BWIDth:RESolution?')
    rbw = float(sds.read())
    output_text += 'RBW (Hz): %.1e Hz\n'%rbw
    
    # vbw:
    sds.write(':SENSe:BWIDth:VIDeo?')
    rbw = float(sds.read())
    output_text += 'VBW (Hz): %.1e Hz\n'%rbw
    
    # ref level
    sds.write(':DISPlay:WINDow:TRACe:Y:SCALe:RLEVel?')
    ref_lev = float(sds.read())
    output_text += 'Reference level: %.1f\n'%ref_lev
    
    # attenuation
    sds.write(':SENSe:POWer:RF:ATTenuation?')
    atten = float(sds.read())
    output_text +='Attenuation: %.1f\n'%atten
    
    # pre-amp state
    sds.write(':SENSe:POWer:RF:GAIN:STATe?')
    preamp = sds.read()
    if '1' in preamp:
        preamp='ON'
    else:
        preamp='OFF'
    output_text += 'Pre-amp: %s\n'%preamp
    
    # amplitude unit
    sds.write(':UNIT:POWer?')
    ampunit = sds.read().strip('\n')
    output_text += 'Amplitude unit: %s\n'%ampunit
    
    # Y scale type (lin or log)
    sds.write(':DISPlay:WINDow:TRACe:Y:SCALe:SPACing?')
    yscaletype = sds.read().strip('\n')
    output_text += 'Y Scale: %s\n'%yscaletype
    
    # X scale type (lin or log)
    sds.write(':DISPlay:WINDow:TRACe:X:SCALe:SPACing?')
    xscaletype = sds.read().strip('\n')
    output_text += 'X Scale: %s\n'%xscaletype
    
    # impedance
    sds.write(':SENSe:CORRection:IMPedance:INPut:MAGNitude?')
    impedance = sds.read().strip('\n')
    output_text += 'Impedance: %s\n'%impedance
    
    # averages 
    sds.write(':SENSe:AVERage:TRACe1:COUNt?\n')
    averages = float(sds.read().strip('\n'))
    output_text += 'Averages: %.0f\n'%averages
    
    if display:
        print(output_text)
    
    return output_text
    

# This is where the magic happens. #
start_time = time.time()
for count in range(int(num_points)):
    tt = time.time()

    # read from siglent
    sds.write(':INITiate:IMMediate')
    time.sleep(0.01)
    sds.write('*OPC?')  # wait for the sweep to be done.
    status = sds.read()

    sds.write(':TRACe:DATA? 1')
    rawdata = sds.read()
    data = [float(x) for x in rawdata.split(',')[:-1]]
    data = np.array(data)

    sds.write(':FREQuency:STARt?')
    fstart = float(sds.read()) * 1e-6

    sds.write(':FREQuency:STOP?')
    fstop = float(sds.read()) * 1e-6

    MHz = np.linspace(fstart, fstop, data.size)

    with open(os.path.join(new_base_dir, 'Siglent-data_' + today +
                           '_%04i.txt' % (count)), 'w') as outfile:

        outfile.write(get_siglent_settings(sds))
        outfile.write('\nFrequency(MHz) Power(dBm)\n')
        for f, pwr in zip(MHz, data):
            outfile.write('%.6f %.4f\n' % (f, pwr))
    
    # Time Stamp
    time_now = datetime.datetime.now().strftime("%Y-%m-%d %X")

    if count < 1:
        start_time = time.time()
    logfile.write('%i, %.2f, %s\n'%(count, time.time() - start_time, time_now))
    logfile.flush()
    
    wait_time = (tt + delay) - time.time()
    
    if wait_time > 0:
        time.sleep(wait_time)
        
    print('% 3i - %.2f sec'%(count, time.time() - tt))

sds.write(":INITiate:CONTinuous ON")


