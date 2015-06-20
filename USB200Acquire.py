import seabreeze
seabreeze.use('pyseabreeze')
import seabreeze.spectrometers as sb

devices = sb.list_devices()
spec = sb.Spectrometer(devices[0])

f = open('spectralCapture.txt', 'wb')

#While True:
	#intTime = input("What is your integration time")
	
	#spec.integration_time_microsec(intTime)
	
f.write(spec.wavelengths())
print spec.wavelengths()

f.write(spec.intensities())
print spec.intensities()