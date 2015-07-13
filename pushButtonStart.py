import RPi.GPIO as GPIO
#GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

import subprocess
import time
ts = time.time()
#import datetime module to timestamp all data being collected 
import datetime
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

import USB2000Acquire as ocean

import HTU21DF


f = open('data/spectralCapture' + st +'.txt', 'w')

while True:
	input_state = GPIO.input(18)	
	#time.sleep(15)
	if input_state == False:		
		print('Button Pressed')	
		
		f.write(str(st))
		f.write('\n')
		
		HTU21DF.htu_reset
		temperature = HTU21DF.read_temperature()
		f.write("Temperature: %f " % temperature)
		f.write('\n')
		time.sleep(1)
		humidity = HTU21DF.read_humidity()
		f.write("Humidity: %F " % humidity)
		f.write('\n')
		
		#capture spectrum
		ocean.capture_spectrum(f)
			
		
		#LED indicator to confirm data capture
		GPIO.output(24, 1)
		time.sleep(.5)		
		GPIO.output(24, 0)
		time.sleep(.5)
		GPIO.output(24, 1)
		time.sleep(.5)		
		GPIO.output(24, 0)
		