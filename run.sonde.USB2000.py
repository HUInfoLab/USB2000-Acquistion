#!/usr/bin/python

# ---------------------------------------
# File: run.sonde.py 
# Generates daily station files of:
#  T,RH-1: DTH22 (AOsong) - GPIO #24
#  T,RH-2: DTH22 (AOsong) - GPIO #25
#  pressure: BMP085  - I2C
#  AD board: ADS1x15  - I2C (2 boards 0x48,0x49)
#  gps:  ADAfruit ultimate GPS - RS232
#  magnetomer: ADAfruit HMC5883l - I2C
#  Spectroradiometer: USB2000 - serial(ttyUSB)
# ---------------------------------------
# Log:
#    2014/09/15: startng from run.stn5.py
#                Note that pigpio does not have start, but now we have to use pi!!!
#                    check this in DHT22 measurements!
#    2014/10/15: previous version run.sonde.2014-10-15.py
#                Incorporates CO2 & 2nd AD board
#    2014/10/21: previous version run.sonde.chem.py
#                taking off CO2 
#    2015/03/20: Incorporating USB2000 - problems running run.sonde.py and
#                PyBot_OO.py at same time.
#    2015/06/04: Bumping baud rate to 57600, changing time stamp in USB2000

import time
import os
import threading
import smbus
import math
import pigpio
import serial
#import atexit


from os.path import exists
from Adafruit_BMP085 import BMP085
from Adafruit_ADS1x15 import ADS1x15
from gps import *
from time import sleep

# Defining default values for USB2000 -------------------
class arg:
        port="/dev/ttyUSB0"
        baud=9600
        bite=8
        parity="None"
        stopbit=1
        inttime = "48"
        timeout=0.05
        path = "./"
        ext = ".dat"
        delay = 0.5
        verbose = False
print arg.port, arg.baud, arg.timeout
ser = serial.Serial(arg.port, arg.baud , timeout=arg.timeout)




# Defining flags and variables
Continua = True
Verbose = False
MaxTrys = 5
INTERVAL = 10  # sampling period


#----------------------------------------------------------------
# Initialise the DHT22 sensor using pigpio GPIO
#     NOTICE: piopiod daemon has to be running
#     Newer version: pigpio.start does not work

class DHT22_sensor:
   """
   A class to read relative humidity and temperature from the
   DHT22 sensor.  The sensor is also known as the AM2302.

   The sensor can be powered from the Pi 3V3 or the Pi 5V rail.

   Powering from the 3V3 rail is simpler and safer.  You may need
   to power from 5V if the sensor is connected via a long cable.

   For 3V3 operation connect pin 1 to 3V3 and pin 4 to ground.

   Connect pin 2 to a gpio.

   For 5V operation connect pin 1 to 5V and pin 4 to ground.

   The following pin 2 connection works for me.  Use at YOUR OWN RISK.

   5V--5K_resistor--+--10K_resistor--Ground
                    |
   DHT22 pin 2 -----+
                    |
   gpio ------------+
   """

   def __init__(self, pi, gpio, LED=None, power=None):
      """
      Instantiate with the Pi and gpio to which the DHT22 output
      pin is connected.

      Optionally a LED may be specified.  This will be blinked for
      each successful reading.

      Optionally a gpio used to power the sensor may be specified.
      This gpio will be set high to power the sensor.  If the sensor
      locks it will be power cycled to restart the readings.

      Taking readings more often than about once every two seconds will
      eventually cause the DHT22 to hang.  A 3 second interval seems OK.
      """

      self.pi = pi
      self.gpio = gpio
      self.LED = LED
      self.power = power

      if power is not None:
         pi.write(power, 1) # Switch sensor on.
         time.sleep(2)

      self.powered = True

      self.cb = None

      #atexit.register(self.cancel)

      self.bad_CS = 0 # Bad checksum count.
      self.bad_SM = 0 # Short message count.
      self.bad_MM = 0 # Missing message count.
      self.bad_SR = 0 # Sensor reset count.

      # Power cycle if timeout > MAX_TIMEOUTS.
      self.no_response = 0
      self.MAX_NO_RESPONSE = 2

      self.rhum = -999
      self.temp = -999

      self.tov = None

      self.high_tick = 0
      self.bit = 40

      pi.set_pull_up_down(gpio, pigpio.PUD_OFF)

      pi.set_watchdog(gpio, 0) # Kill any watchdogs.

      self.cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cb)

   def _cb(self, gpio, level, tick):
      """
      Accumulate the 40 data bits.  Format into 5 bytes, humidity high,
      humidity low, temperature high, temperature low, checksum.
      """
      diff = pigpio.tickDiff(self.high_tick, tick)

      if level == 0:

         # Edge length determines if bit is 1 or 0.

         if diff >= 50:
            val = 1
            if diff >= 200: # Bad bit?
               self.CS = 256 # Force bad checksum.
         else:
            val = 0

         if self.bit >= 40: # Message complete.
            self.bit = 40

         elif self.bit >= 32: # In checksum byte.
            self.CS  = (self.CS<<1)  + val

            if self.bit == 39:

               # 40th bit received.

               self.pi.set_watchdog(self.gpio, 0)

               self.no_response = 0

               total = self.hH + self.hL + self.tH + self.tL

               if (total & 255) == self.CS: # Is checksum ok?

                  self.rhum = ((self.hH<<8) + self.hL) * 0.1

                  if self.tH & 128: # Negative temperature.
                     mult = -0.1
                     self.tH = self.tH & 127
                  else:
                     mult = 0.1

                  self.temp = ((self.tH<<8) + self.tL) * mult

                  self.tov = time.time()

                  if self.LED is not None:
                     self.pi.write(self.LED, 0)

               else:

                  self.bad_CS += 1

         elif self.bit >=24: # in temp low byte
            self.tL = (self.tL<<1) + val

         elif self.bit >=16: # in temp high byte
            self.tH = (self.tH<<1) + val

         elif self.bit >= 8: # in humidity low byte
            self.hL = (self.hL<<1) + val

         elif self.bit >= 0: # in humidity high byte
            self.hH = (self.hH<<1) + val

         else:               # header bits
            pass

         self.bit += 1

      elif level == 1:
         self.high_tick = tick
         if diff > 250000:
            self.bit = -2
            self.hH = 0
            self.hL = 0
            self.tH = 0
            self.tL = 0
            self.CS = 0

      else: # level == pigpio.TIMEOUT:
         self.pi.set_watchdog(self.gpio, 0)
         if self.bit < 8:       # Too few data bits received.
            self.bad_MM += 1    # Bump missing message count.
            self.no_response += 1
            if self.no_response > self.MAX_NO_RESPONSE:
               self.no_response = 0
               self.bad_SR += 1 # Bump sensor reset count.
               if self.power is not None:
                  self.powered = False
                  self.pi.write(self.power, 0)
                  time.sleep(2)
                  self.pi.write(self.power, 1)
                  time.sleep(2)
                  self.powered = True
         elif self.bit < 39:    # Short message receieved.
            self.bad_SM += 1    # Bump short message count.
            self.no_response = 0

         else:                  # Full message received.
            self.no_response = 0

   def temperature(self):
      """Return current temperature."""
      return self.temp

   def humidity(self):
      """Return current relative humidity."""
      return self.rhum

   def staleness(self):
      """Return time since measurement made."""
      if self.tov is not None:
         return time.time() - self.tov
      else:
         return -999

   def bad_checksum(self):
      """Return count of messages received with bad checksums."""
      return self.bad_CS

   def short_message(self):
      """Return count of short messages."""
      return self.bad_SM

   def missing_message(self):
      """Return count of missing messages."""
      return self.bad_MM

   def sensor_resets(self):
      """Return count of power cycles because of sensor hangs."""
      return self.bad_SR

   def trigger(self):
      """Trigger a new relative humidity and temperature reading."""
      if self.powered:
         if self.LED is not None:
            self.pi.write(self.LED, 1)

         self.pi.write(self.gpio, pigpio.LOW)
         time.sleep(0.017) # 17 ms
         self.pi.set_mode(self.gpio, pigpio.INPUT)
         self.pi.set_watchdog(self.gpio, 200)

   def cancel(self):
      """Cancel the DHT22 sensor."""

      self.pi.set_watchdog(self.gpio, 0)

      if self.cb != None:
         self.cb.cancel()
         self.cb = None


# starting pigpio:
pi=pigpio.pi()
sensor1 = DHT22_sensor(pi,24,LED=16,power=8)
sensor2 = DHT22_sensor(pi,25,LED=16,power=8)

# ---------------------------------------------------------------
# Initialise the BMP085 and use STANDARD mode (default value)
# bmp = BMP085(0x77, debug=True)
bmp = BMP085(0x77)

# To specify a different operating mode, uncomment one of the following:
# bmp = BMP085(0x77, 0) # ULTRALOWPOWER Mode
# bmp = BMP085(0x77, 1) # STANDARD Mode
# bmp = BMP085(0x77, 2) # HIRES Mode
# bmp = BMP085(0x77, 3) # ULTRAHIRES Mode

# ---------------------------------------------------------------
# Analog-Digital converser
ad_value  = [-9999.,-9999.,-9999.,-9999.]
ad_value2 = [-9999.,-9999.,-9999.,-9999.]

# Gain can be 6144, 4096, 2048, 1024,512, and 256 (these are the Full Scale)
gain  = [ 256,6144,6144,6144]
gain2 = [6144,6144,6144,6144]

# AD board initialization:
ADS1015 = 0x00        # 12-bit ADC
ADS1115 = 0x01        # 16-bit ADC

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# ToDo: Change the value below depending on which chip you're using!
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
ADS_Current = ADS1115


# Initialise the ADCs using the default mode (use default I2C address)
adc  = ADS1x15(address=0x48,ic=ADS_Current)
adc2 = ADS1x15(address=0x49,ic=ADS_Current)

# ---------------------------------------------------------------
# GPS initialization & defining functions
gpsd = None #seting the global variable

class GpsPoller(threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    global gpsd #bring it in scope
    gpsd = gps(mode=WATCH_ENABLE) #starting the stream of info
    self.current_value = None
    self.running = True #setting the thread running to true

  def run(self):
    global gpsd
    while gpsp.running:
      gpsd.next() #this will continue to loop and grab EACH set of gpsd info to clear the buffer


gpsp = GpsPoller() # create the thread
gpsp.start() # start it up

# ---------------------------------------------------------------
# magnetometer HMC5883l based on http://blog.bitify.co.uk/2013/11/connecting-and-calibrating-hmc5883l.html
address = 0x1E
MaxTrys = 5

i2c = smbus.SMBus(1)

def read_word(adr):
            high = i2c.read_byte_data(address, adr)
            low =  i2c.read_byte_data(address, adr+1)
            val = (high << 8) + low
            return val

def read_word_2c(adr):
            val = read_word(adr)
            if (val >= 0x8000):
                return -((65535 - val) + 1)
            else:
                return val


# USB2000 Reading serial port now -------------------------------------------
#print arg.port, arg.baud, arg.timeout
#ser = serial.Serial(arg.port, arg.baud , timeout=arg.timeout)

# initiating USB2000

print "Initializing USB2000 "
ser.write("aA")
lixo = ser.readline()
print "Ascii mode: ",lixo

comando = ''.join(["I",arg.inttime])
print "comando =",comando
ser.write(comando)
lixo = ser.readline()
print "Integration time: ",lixo[2:]

ser.write("G1")
lixo = ser.readline()
print "Integration time: ",lixo[2:]

ser.write("v")
lixo = ser.readline()
lixo1 = ser.readline()
print "v: lixo: ",lixo[2:], "\nlixo1=",lixo1[2:]

ser.write("?x0")
lixo = ser.readline()
lixo1 = ser.readline()
print "?x0: lixo: ",lixo[2:], "\nlixo1=",lixo1[2:]

ser.write("?xA")
lixo = ser.readline()
lixo1 = ser.readline()
print "?xA: lixo: ",lixo[2:], "\nlixo1= ",lixo1[2:]

time.sleep(2)


# ---------------------------------------------------------------
# Opening file & putting header if file is new:
tCurrent = time.gmtime()
tstamp = format(time.strftime("%Y-%m-%d_%H-%M-%S",tCurrent))
arqout = ''.join(['sonde.USB2000.',tstamp,'UT.dat'])
print "output file name:",arqout,"\n"

if(exists(arqout)):
	print "File ",arqout," exists!\n"

else:
	fout=open(arqout,'w')
	fout.write("Generated by python code run.sonde.USB2000.py\n")
	fout.write('USB2000_integration-time: {0}'.format(arg.inttime))
	fout.write("\n") 
	fout.write("YYYY Mo DD HH Mi SS ")
	fout.write("Ta1(C) RH1(%) stal1(s) Ta2(C) RH2(%) stal2(s) ")
	fout.write("Tbmp085(C) press(mb) ")
	fout.write("AD-0(V) AD-1(V) AD-2(V) AD-3(V) ")
	fout.write("AD-4(V) AD-5(V) AD-6(V) AD-7(V) ")
	fout.write("lat lon alt eps epx epv ept speed climb track mode ")
	fout.write("x_out y_out z_out angle ")
	fout.write("co2")
	fout.write("\n")
	fout.close()

# ---------------------------------------------------------------
#  measuring here
jj = 0
staleness1 = 0
staleness2 = 0
bad_checksum1 = 0
bad_checksum2 = 0
next_reading = time.time()


while Continua:
        try:
                jj = jj +1
		# getting time ---------------
		tCurrent = time.gmtime()
		if(Verbose):
			print "================= jj= ",jj
                        print "time stamp: ",time.strftime("(yy/mo/dd) %Y/%m/%d %H:%M:%S",tCurrent)
			

		# DHT22 sensors start here ----------------------

		# checking to see if have to restart pigpio
		if(staleness1 > 5 or staleness2 > 5  ):
			if(Verbose):
				print "DHT22 stopped"
				print "Staleness1: ",staleness1," Staleness2: ",staleness2
			# stopping sensors & pigpio
			#sensor1.cancel()
			#sensor2.cancel()
			#pi.stop()
			# re-starting pigpio & sensor
			#pigpio.pi()
			#sensor1 = DHT22_sensor(pi,24,LED=16,power=8)
			#sensor2 = DHT22_sensor(pi,25,LED=16,power=8)

		# T,RH-1 reading here -------------

		try:
      			sensor1.trigger()
      			time.sleep(0.2)
			Tair1 = sensor1.temperature()
			RH1 = sensor1.humidity()
			staleness1 = sensor1.staleness()
			bad_checksum1 = sensor1.bad_checksum()
		except:
			Tair1 = 9999.
			RH1 = 9999.
			staleness1 = 9999.
			bad_checksum1 = 9999.


		if(Verbose):
			print "Tair1 %.2f C" %Tair1
			print "RH1 %.1f " % RH1
			print "staleness1 %.2f " % staleness1
			print "badchecksum %f " % bad_checksum1

                # T,RH-2 reading here -------------
		try:
                	sensor2.trigger()
                	time.sleep(0.2)
                	Tair2 = sensor2.temperature()
                	RH2 = sensor2.humidity()
                	staleness2 = sensor2.staleness()
                	bad_checksum2 = sensor2.bad_checksum()
		except:
			Tair2 = 9999.
			RH2 = 9999.
			staleness2 = 9999.
			bad_checksum2 = 9999.


                if(Verbose):
                        print "Tair2 %.2f C" %Tair2
                        print "RH2 %.1f " % RH2
                        print "staleness2 %.2f " % staleness2
                        print "badchecksum2 %f " % bad_checksum2



		# Pressure reading here ---------------
		# print Temperature
		Tbmp085 = bmp.readTemperature()
		# Read the current barometric pressure level
		pressure = bmp.readPressure()
		pressure = pressure / 100.

		# Forcing an exception if temp and pressure are not in a range:
		#if( temp < -10 or temp > 50 or pressure < 95000 or pressure > 105000):
		#	erro = 1/0;
		# To calculate altitude based on an estimated mean sea level pressure
		# (1013.25 hPa) call the function as follows, but this won't be very accurate
		##### altitude = bmp.readAltitude()
		# To specify a more accurate altitude, enter the correct mean sea level
		# pressure level. For example, if the current pressure level is 1023.50 hPa
		# enter 102350 since we include two decimal places in the integer value
		# altitude = bmp.readAltitude(102350)
		if(Verbose): 
			print "Temperature: %.2f C" % Tbmp085
			print "Pressure: %.2f hPa" % pressure 
			#print "Altitude: %.2f" % altitude

		# AD board reading here ---------------
		# Initialise the ADC using the default mode (use default I2C address)
		#adc  = ADS1x15(address=0x48,ic=ADS_Current)
		#adc2 = ADS1x15(address=0x49,ic=ADS_Current)

		# Read channels in single-ended mode
		for jad in range(0,4):
			j2 = 0
        		while j2 < MaxTrys:
				try:
					j2=j2+1
					result = adc.readADCSingleEnded(jad,pga=gain[jad])
					result2 = adc2.readADCSingleEnded(jad,pga=gain2[jad])
					if ADS_Current == ADS1015:
   						# For ADS1015 at max range (+/-6.144V) 1 bit = 3mV (12-bit values)
						ad_value[jad] = result*0.003
						ad_value2[jad] = result2*0.003
						if(Verbose):
  							print "Channel %d = %.3f V" %(jad , (result * 0.003))
  							print "Channel %d = %.3f V" %(jad+4 , (result2 * 0.003))
					else:
  						# For ADS1115 at max range (+/-6.144V) 1-bit = 0.1875mV (16-bit values)
						ad_value[jad] = result*0.0001875
						ad_value2[jad] = result2*0.0001875
						if(Verbose):
  							print "Channel %d = %.6f V" %(jad , (result * 0.0001875))
  							print "Channel %d = %.6f V" %(jad+4  , (result2 * 0.0001875))
					break;
				except:
					ad_value[jad] = -9999.
					ad_value2[jad] = -9999.
                			print "entrou no except ADC:" 
					blank1=0;


		# gps reading here ---------------
		lat = gpsd.fix.latitude
		lon = gpsd.fix.longitude
		alt = gpsd.fix.altitude
      		eps = gpsd.fix.eps
      		epx = gpsd.fix.epx
      		epv = gpsd.fix.epv
      		ept = gpsd.fix.ept
      		speed = gpsd.fix.speed
      		climb = gpsd.fix.climb
      		track = gpsd.fix.track
      		mode = gpsd.fix.mode
      		sats = gpsd.satellites
		if(Verbose):
			print "lat: %s " % lat
			print "lon: %s " % lon
			print "alt: %s " % alt
			print "Sat: %s " % sats 

		# magnetometer reading here ------------------	
	        jj = 0

	        while jj < MaxTrys:
	        	try:
       		        	jj = jj+1

				if(Verbose):
                			print "---> magnetometer: try", jj

                		# sending command
                		i2c.write_byte_data(address,0,0b01110000) # Set to 8 samples @ 15Hz
                		i2c.write_byte_data(address,1,0b00100000) # 1.3 gain LSb / Gauss 1090 (default)
                		i2c.write_byte_data(address,2,0b00000000) # Continuous sampling

		                scale = 0.92

               			x_out = read_word_2c(3) * scale
		        	y_out = read_word_2c(7) * scale
	                	z_out = read_word_2c(5) * scale

				bearing  = math.atan2(y_out, x_out)
				if (bearing < 0):
					bearing += 2 * math.pi
				bearing_deg = math.degrees(bearing)

				if(Verbose):
					print "x_out: ",x_out
					print "y_out: ",y_out
					print "z_out: ",z_out
                			print "Bearing: ", bearing_deg
				break;
           		except:
                		print "entrou no magnotometer except"
                		blank =0;

		# writting to output file: ---------------------
                fout=open(arqout,'a')


		# time stamp, temp & pressure
		fout.write('{0} '.format(
		time.strftime("%Y %m %d %H %M %S",tCurrent))) 

		#DHT22-1 Tair1,RH1
		fout.write('{0} {1} {2:.2f} '.format(
		Tair1,RH1,staleness1))

		#DHT22-2 Tair2,RH2
		fout.write('{0} {1} {2:.2f} '.format(
		Tair2,RH2,staleness2))

		# BMP085 temp & pressure
		fout.write('{0} {1} '.format(Tbmp085,pressure))

		# AD-1 values
		fout.write('{0} {1} {2} {3} '.format(
		ad_value[0],ad_value[1],ad_value[2],ad_value[3]))

		# AD-2 values
		fout.write('{0} {1} {2} {3} '.format(
		ad_value2[0],ad_value2[1],ad_value2[2],ad_value2[3]))

		# GPS
		fout.write('{0} {1} {2} {3} {4} {5} {6} {7} {8} {9} {10} '.format(
		lat,lon,alt,eps,epx,epv,ept,speed,climb,track,mode))

		# magnetometer 
		fout.write('{0} {1} {2} {3:5.1f} '.format(
		x_out,y_out,z_out,bearing_deg)) 

		# CO2 
		co2Val = 9999.
		fout.write('{0} '.format(co2Val))

		fout.write('\n')

		# NOW readling USB2000 spectrometer --------------------------
		#     Doing that because it takes 8 sec to send data to RS232
        	if(arg.verbose):
                	print "Sending spectrum command now"
                tCurrent=time.gmtime() # moved to here 06/04/2015
	        ser.write("S")
	        data = ser.readline()
	        if(arg.verbose):
	                print "raw spectra: ",data
	        len_data= len(data)
	        data = data[10:(len_data-2)]
	        if(arg.verbose):
	                print "spectra: ",data
	                print "len_data: ",len_data

		# writting USB2000 spectrometer data:
                #tCurrent=time.gmtime() - commented on 06/04/2015
               	fout.write('{0} '.format(
                           time.strftime("%Y %m %d %H %M %S",tCurrent)))
		if(len_data > 8000):
                	fout.write('{0}\n'.format(data))
		else:
			for ii in range(1,2056):
				fout.write(' -999')
			fout.write('\n')
			
		# closing file ------------------------------------
		fout.close()

		# sleeping now -----------------------------------
      		#next_reading += INTERVAL
      		#time.sleep(next_reading-time.time()) # Overall INTERVAL second polling.


        except (KeyboardInterrupt, SystemExit): #when you press ctrl+c
                print "\nKilling Thread..."
		sensor1.cancel()
		sensor2.cancel()
		pi.stop()
		print "Cancelling T,RH"
		Continua = False
		print "Stopping gps"
    		gpsp.running = False
    		gpsp.join() # wait for the thread to finish what it's doing

	except ZeroDivisionError:
		if(Verbose):
			print "----------------> ERROR! "
			print "Temperature: %.2f C" % temp
			print "Pressure: %.2f hPa" % pressure 

print "Done.\nExiting."

