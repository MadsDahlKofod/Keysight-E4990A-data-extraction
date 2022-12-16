# -*- coding: utf-8 -*-
"""
Created on Wed Nov 30 12:21:09 2022

@author: Mads Kofod Dahl
"""
# -*- coding: utf-8 -*-
# Python for Test and Measurement

# Requires VISA installed on controlling PC
# 'http://www.keysight.com/find/visa'
#
# Requires PyVISA to use VISA in Python
# 'http://pyvisa.sourceforge.net/pyvisa/'

# Keysight IO Libraries 18.1.23218.2 32-Bit Keysight VISA (as primary)
# Anaconda Python 4.4.0 32 bit
# pyvisa 3.6.x

##"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
## Copyright © 2019 Keysight Technologies Inc. All rights reserved.
##
## You have a royalty-free right to use, modify, reproduce and distribute this
## example files (and/or any modified version) in any way you find useful, provided
## that you agree that Keysight has no warranty, obligations or liability for any
## Sample Application Files.
##
##"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

# Example Description:  
# A python sample program utilizing pyvisa to connect and control an E4990A
# swept impedance analyzer.
#
# The application performs the following:
#   Imports the pyvisa libraries and operating system dependent functionality;
#   Establishes a visa resource manager;
#   Opens a connection to a Keysight Technologies E4990A swept impedance analyzer
#    based on the instrument's VISA address as acquired via Keysight Connection Expert
#   Sets the visa time out (increasing the timeout as compared to the default). 
#   Clears the event status register and clears the error queue;
#   Queries the instrument via the '*IDN?' identification query;
#   Defines an error check function and checks the system error queue;
#   Performs a single trigger with hold-off;
#   Queries trace 1 and trace 2 data, as well as the frequency data, and transfers 
#   this data from the E4990A to the PC via a binary bin-block data transfer. 
#       

   
# Import the visa libraries
import pyvisa as visa

# Import csv libraries for saving data
import csv

#import MATLAB plot library for ease of plotting data
import matplotlib.pyplot as stimulusResponsePlot

# Open a VISA resource manager pointing to the installation folder for the Keysight Visa libraries. 
rm = visa.ResourceManager('C:\\Program Files (x86)\\IVI Foundation\\VISA\\WinNT\\agvisa\\agbin\\visa32.dll') 

# Based on the resource manager, open a session to a specific VISA resource string as provided via
# Keysight Connection Expert
# ALTER LINE BELOW - Updated VISA resource string to match your specific configuration
myE4990A = rm.open_resource("USB0::0x2A8D::0x5F01::MY54302532::0::INSTR")   
 
#Set Timeout - 10 seconds
myE4990A.timeout = 10000

# Clear the event status registers and empty the error queue
myE4990A.write("*CLS")

# Clear the display status bar cautions / error messages
myE4990A.write("DISPlay:CCLear")

# Query identification string *IDN? 
myE4990A.write("*IDN?")
print (myE4990A.read())

# **** Define Error Check Function **** 
def Errcheck():
    myError = []
    ErrorList = myE4990A.query("SYST:ERR?").split(',')
    Error = ErrorList[0]
    if int(ErrorList[0])==0:
        myError = ErrorList[1]
    else:
        while int(Error)!=0:
            print ("Error #: " + ErrorList[0])
            print ("Error Description: " + ErrorList[1])
            myError.append(ErrorList[0])
            myError.append(ErrorList[1])
            ErrorList = myE4990A.query("SYST:ERR?").split(',')
            Error = ErrorList[0]
            myError = list(myError)
    return myError

# **** A function for configuring parameters on the Keysight E4990A **** 
def configureE4990a(startfreq):
  
    # Define variables to allow flexibility in configuration
    #startFrequency = 50000.0
    #stopFrequency = 500000.0
    startFrequency = startfreq
    stopFrequency = startFrequency+50000.0
    numberOfPoints = 1602
    trace1MeasType = "G" #G: Real admittance
    trace2MeasType = "B" #B: Imaginary admittance
    
    apertureDuration = 1   # minimum of 1 and maximum of 5
    
    # Perform a system preset with hold-off
    myE4990A.query("SYSTem:PRESet;*OPC?")
    
    # Configure Trigger Source to support single trigger with synchronization
    myE4990A.write("TRIGger:SOURce BUS")
    myE4990A.write("INITiate:CONTinuous ON")
    
    # Set the aperture which affects trace noise and repeatability, i.e. averaging
    myE4990A.write("SENSe:APERture "+str(apertureDuration))
  
    # Set the start and stop frequencies via concatenated string and use of SCPI SENSe FREQuency branch
    myE4990A.write("SENSe:FREQuency:STARt "+str(startFrequency)+";STOP "+str(stopFrequency))
      
    # Set the number of trace points
    myE4990A.write("SENSe:SWEep:POINts "+str(numberOfPoints))
    
    # Select trace 1 and set measurement format
    myE4990A.write("CALCulate:PARameter1:DEFine "+trace1MeasType)
    
    # Select trace 1 and set measurement format
    myE4990A.write("CALCulate:PARameter2:DEFine "+trace2MeasType)
    
    # Set OSC level
    myE4990A.write(":SOUR1:VOLT 1000E-3") # Max 1V
       
    return

# **** A function for forcing a single trigger with hold-off synchronization **** 
def triggerSingle():
    
    # Abort and reset sweep if active 
    myE4990A.write("ABORt")
    
    # Force single trigger with hold-off. Note high aperture counts may result
    # in sweep times in excess of 40s. For these conditions the timeout setting 
    # must be altered to allow for this long duration else timeout errors will occur.
    
    #opcomplete = myE4990A.query("TRIGGer:SINGle;*OPC?")
    myE4990A.query("TRIGGer:SINGle;*OPC?")
    
    # Once trigger complete has occurred auto scale both trace 1 and trace 2
    myE4990A.write("DISPlay:WINDow:TRACe1:Y:SCALe:AUTO")
    myE4990A.write("DISPlay:WINDow:TRACe2:Y:SCALe:AUTO")
    return

# **** A function for returning the analyzer to free run triggering mode **** 
def triggerToFreeRun():
    # Set trigger source to internal to allow free run post data acquisition
    myE4990A.write("TRIGger:SOURce INTernal")
    return

    
# **** A function for acquiring real 64-bit binary block data **** 
# This includes trace 1 and trace 2 response arrays and the frequency array 
#  i.e. stimulus array.
def binBlockDataAcq():
    
    # Set data format to binary bin block as real 64-bit
    myE4990A.write("FORMat:DATA REAL") #REAL: IEEE 64-bit floating point binary transfer format
    
    # Now query Trace1 and Trace 2 stimulus arrays as Real64-bit binary blocks. 
    myE4990A.write("CALCulate:PARameter1:SELect")
    trace1Data =  myE4990A.query_binary_values("CALCulate:DATA:FDATA?", datatype='d', is_big_endian=True)
    
    myE4990A.write("CALCulate:PARameter2:SELect")
    trace2Data =  myE4990A.query_binary_values("CALCulate:DATA:FDATA?", datatype='d', is_big_endian=True)
    
    # Query the stimulus array as well
    stimulusData =  myE4990A.query_binary_values("SENSe:FREQuency:DATA?", datatype='d', is_big_endian=True)
    
    # For each of the formatted response or data arrays every other 
    # value is a zero place holder thus strip this
    trace1DataTrimmed = trace1Data[0::2]
    trace2DataTrimmed = trace2Data[0::2]
    print("*********************** Trace 1 Impedance data ***********************")
    print(trace1DataTrimmed)
    print( "\n")
    
    print("*********************** Trace 2 Impedance data ***********************")
    print(trace2DataTrimmed)
    print("\n")
    
    print("*********************** Frequency data ***********************")
    print(stimulusData)
    print("\n")
    
    # Return data format back to ASCII on completion 
    myE4990A.write("FORMat:DATA ASCii") #ASCii: ASCII transfer format

    return trace1DataTrimmed, trace2DataTrimmed, stimulusData

# **** A function for plotting acquired data: trace 1, trace 2 and the frequency array **** 
def plotData(freqdata, trace1, trace2):
#    # plot trace data and stimulus data as X-Y trace. 
    stimulusResponsePlot.title ("Keysight E4990A Impedance Data via Python - PyVisa - SCPI")
    stimulusResponsePlot.xlabel("Frequency")
    stimulusResponsePlot.plot(freqdata,trace1,color="yellow",label="Re")
    stimulusResponsePlot.plot(freqdata,trace2, color = "blue",label="Im")
    stimulusResponsePlot.legend()
#    stimulusResponsePlot.grid(True,'major')
#    #stimulusResponsePlot.plot(stimulusData,trace1DateTrimmed)
#    
#    # Plot details
#    stimulusResponsePlot.autoscale(True, True, True) 
#    stimulusResponsePlot.show()
    return
#%%

Frequency = []
Trace1Savelocal = []
Trace2Savelocal = []

i = 50000

while i<500000:  

    print(i)
    # Call the functions here
    print("\nInitial Error Check Results: ")
    print(Errcheck())
    configureE4990a(i)
    triggerSingle()
    trace1DataTrimmed, trace2DataTrimmed, stimulusData = binBlockDataAcq()
    #plotData()
    triggerToFreeRun()
    
    #On completion of the application, query the error queue via the ErrCheck function.
    # If the application is written correctly, barring any hardware issues, it should 
    # run stem to stern without causing an error.
    print ("\nFinal Error Check Results: ")
    print (Errcheck())
    
    
    if i < 500000:
        Trace1Savelocal.extend(trace1DataTrimmed[0:1601])
        Trace2Savelocal.extend(trace2DataTrimmed[0:1601])
        Frequency.extend(stimulusData[0:1601])
    if i > 500000:
        Trace1Savelocal.extend(trace1DataTrimmed[0:1602])
        Trace2Savelocal.extend(trace2DataTrimmed[0:1602])
        Frequency.extend(stimulusData[0:1602])
        
    
    i = i + 50000
    

print("Plotting data!\n")

plotData(Frequency, Trace1Savelocal,Trace2Savelocal)


with open('Rod1_Damaged_Minus10Degrees.csv', 'w') as file:
    writer = csv.writer(file,delimiter =";")
    writer.writerow(Frequency)
    writer.writerow(Trace1Savelocal)
    writer.writerow(Trace2Savelocal)