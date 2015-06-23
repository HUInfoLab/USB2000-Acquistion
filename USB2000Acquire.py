import time
ts = time.time()

#import datetime module to timestamp all data being collected 
import datetime
st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')


#import the seabreeze library to interact with Ocean Optics Spectrometers 
import seabreeze

#set parameter "backend" to 'pyseabreeze'
seabreeze.use('pyseabreeze')

#create object sb with access to the methods associated with the spectrometers class
import seabreeze.spectrometers as sb

#get list of spectrometers attached to raspberry pi
devices = sb.list_devices()

#assign the first connected device to a new object
spec = sb.Spectrometer(devices[0])

#open file to write data to
f = open('spectralCapture.txt', 'w')

#While True:
	#intTime = input("What is your integration time")
	
	#spec.integration_time_microsec(intTime)

#write the wavelengths captured by the spectrometer to the opened file	
#f.write(spec.wavelengths())
#print spec.wavelengths()

try:
	while True:
		wavelengthArray = spec.wavelengths()
		intensityArray = spec.intensities()

		f.write(str(st))
		f.write('\n')

		for x in range(0, len(wavelengthArray)):
			f.write(str(wavelengthArray[x]))
			f.write(',')
			f.write(str(intensityArray[x]))
			f.write('\n')
		print("Data collected")
		time.sleep(3)	
except KeyboardInterrupt:
	print("We closed")
	f.close()


# while True:
    # var = input("Start Data collecting with an input of 2: ")
    # if not var:
        # continue

    # try:
        # while var == 2: 
			# # wavelengthArray = spec.wavelengths()
			# # intensityArray = spec.intensities()

			# # f.write(str(st))
			# # f.write('\n')

			# # for x in range(0, len(wavelengthArray)):
				# # f.write(str(wavelengthArray[x]))
				# # f.write(',')
				# # f.write(str(intensityArray[x]))
				# # f.write('\n')
	
			# # time.sleep(3)		
	# except KeyboardInterrupt:
		# f.close()
        