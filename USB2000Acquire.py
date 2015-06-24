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

#define capture function to be called on button press
def capture_spectrum():
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
        