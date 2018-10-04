import RPi.GPIO as GPIO
import cPickle as pickle
import time
import sys
import os

#os.chdir("/home/pi/Documents/Python/ir/Resources/")
sys.path.append("./Resources")
from CodeManager import CodeManager
import keypad

GPIO_BUTTON = 19
GPIO_LED = 8
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(GPIO_BUTTON, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
GPIO.setup(GPIO_LED, GPIO.OUT)
GPIO.output(GPIO_LED, GPIO.LOW)
keypad = keypad.Keypad([37, 35, 33, 31], [40, 38, 36, 32], [["1","2","3","A"],["4","5","6","B"],["7","8","9","C"],["*","0","#","D"]], [19])

codeManager = CodeManager()

#for i in range(0,5):
#	GPIO.output(GPIO_LED, GPIO.HIGH)
#	time.sleep(.2)
#	GPIO.output(GPIO_LED, GPIO.LOW)
#	time.sleep(.2)

def Menu():
	print "Current Brands: ", codeManager.brands
	print "1. Download New Codes"
	print "2. Load + Download Codes"
	print "3. Load Codes"

	input = "3"
	if not "go" in sys.argv:
		input = raw_input("Enter Option: ")

	if input == "1":
		codeManager.Download()
	elif input == "2":
		pass
	elif input == "3":
		codeManager.codes = codeManager.LoadCodes()
		codeManager.ConvertCodes()
		pass


Menu()

print len(codeManager.codes), "codes"

try:
	index = 0
	triedCodes = []
	holdTimer = 0
	pushed = False
	startIndex = 0

	while 1:
		key = keypad.readKeys()

		if key != "-1":
			if holdTimer == 0:
				GPIO.output(GPIO_LED, GPIO.HIGH)
				startTime = time.time()
				codeManager.SendCode(index, key)
				print "Time: ", time.time() - startTime
				GPIO.output(GPIO_LED, GPIO.LOW)
				startIndex = index

			if holdTimer <= 20:
				holdTimer += 1
			if holdTimer > 20:
				GPIO.output(GPIO_LED, GPIO.HIGH)
				index += 10
				if index > len(codes):
					print "-------index reset--------"
					index = 0
					triedCodes = []
					for i in range(0,3):
						GPIO.output(GPIO_LED, GPIO.HIGH)
						time.sleep(.2)
						GPIO.output(GPIO_LED, GPIO.LOW)
						time.sleep(.2)


				#triedCodes.append(CodeManager.SendCode(codes, index, "KEY_POWER", triedCodes))

				GPIO.output(GPIO_LED, GPIO.LOW)
		else:
			holdTimer = 0
			triedCodes = []



		#dispCodes = []
		#for code in zip(*codes)[1]:
		#	if not code in dispCodes:
		#		dispCodes.append(code)
		#print dispCodes
		#cmd = raw_input("Enter Button Name (exit to quit): ")

		time.sleep(.1)


except  KeyboardInterrupt:
	print "Cleaning up"
	ir.cleanup()
	GPIO.cleanup()
