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
wavelengthArray = spec.wavelengths()
intensityArray = spec.intensities()


for x in range(0, len(wavelengthArray)):
	f.write(str(wavelengthArray[x]))
	f.write(',')
	f.write(str(intensityArray[x]))
	f.write('\n')

#write the intensities captured by the spectrometer to the opened file
#f.write(spec.intensities())
#print spec.intensities()

#write the spectrum captured by the spectrometer to the opened file
#f.write(spec.spectrum())
#print spec.spectrum

f.close()