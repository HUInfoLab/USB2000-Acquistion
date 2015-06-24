import RPi.GPIO as GPIO
import time
import USB2000Acquire as ocean

GPIO.setmode(GPIO.BCM)

GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

while True:
    input_state = GPIO.input(18)
    if input_state == False:
		ocean.capture_spectrum()
		print('Button Pressed')		
		time.sleep(0.2)