import RPi.GPIO as GPIO
import time
import USB2000Acquire as ocean
#GPIO.cleanup()
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


GPIO.setup(24, GPIO.OUT)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)


while True:
	input_state = GPIO.input(18)
	# GPIO.output(24, GPIO.LOW)
	# time.sleep(5)
	# GPIO.output(24, GPIO.HIGH)
	# time.sleep(5)
	if input_state == False:
		ocean.capture_spectrum()
		print('Button Pressed')	
		GPIO.output(24, 1)
		time.sleep(.5)
		GPIO.output(24, 0)