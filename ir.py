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

def Flash(amount):
	for i in range(amount):
		GPIO.output(GPIO_LED, GPIO.HIGH)
		time.sleep(.2)
		GPIO.output(GPIO_LED, GPIO.LOW)
		time.sleep(.2)

Flash(3)

def Menu():
	print "\nCurrent Brands: ", codeManager.brands
	print "Current code containers: ", len(codeManager.codes)
	print "\n1. Download New Codes"
	print "2. Load + Download Codes"
	print "3. Load Codes"
	print "4. Redownload all codes"
	print "5. Delete Brand"
	print "6. List codes"

	input = 3
	if not "go" in sys.argv:
		input = codeManager.input(1, 6)

	if input == 1:
		codeManager.Download(0)
		codeManager.ConvertCodes()

	elif input == 2:
		codeManager.codes = codeManager.LoadCodes()
		codeManager.Download(1)
		codeManager.ConvertCodes()

	elif input == 3:
		starTime = time.time()
		codeManager.codes = codeManager.LoadCodes()
		codeManager.ConvertCodes()
		print "Time spent:", time.time() - starTime

	elif input == 4:
		codeManager.Download(2)
		codeManager.ConvertCodes()

	elif input == 5:
		brand = raw_input("Enter brand to delete: ")
		print "\nAre you sure you want to permanently delete", brand, "?\n1. Yes\n2. No"
		if codeManager.input(1, 2) == 1:
			codeManager.DeleteBrand(brand)

		Menu()

	elif input == 6:
		brand = raw_input("Enter brand (or all): ")
		cmd = raw_input("Enter Code Name (or all): ")
		for codeHolder in codeManager.codes:
			if codeHolder[0]["brand"] == brand or brand == "all":
				print "Name(s): ", codeHolder[0]["name"]
				for code in codeHolder[1]:
					if code == cmd or cmd == "all":
						print code, codeHolder[1][code]
				print ""

		Menu()



Menu()

print len(codeManager.codes), "codes"

Flash(5)

try:
	index = 0
	holdTimer = 0
	pushed = False

	while 1:
		key = keypad.readKeys()

		if key != "-1":
			if holdTimer == 0:
				GPIO.output(GPIO_LED, GPIO.HIGH)
				startTime = time.time()

				codeManager.SendCode(key, index)

				print "Time: ", time.time() - startTime
				GPIO.output(GPIO_LED, GPIO.LOW)

			if key == "*":
				index = 0
				Flash(codeManager.allMode + 1)

			elif key == "C":
				index -= 5
				if index < 0:
					index += len(codeManager.codes)
				Flash(1)

			elif key == "B":
				index += 5
				if index >= len(codeManager.codes):
					index -= len(codeManager.codes)
				Flash(1)

			if not codeManager.allMode:
				specialKeyPushed = False
				if key == "button0" or key == "A" or key == "C":
					specialKeyPushed = True

				#if not specialKeyPushed:
				#	holdTimer = 16
					
				if holdTimer <= 10:
					holdTimer += 1

				if holdTimer > 10:
					GPIO.output(GPIO_LED, GPIO.HIGH)

					if key == "button0" or key == "A":
						index += 5

					if index % len(codeManager.codes) < index:
						print "-------index reset--------"
						index = 0

					index %= len(codeManager.codes)

					#print "index:", index

					codeManager.SendCode(key, index)

					GPIO.output(GPIO_LED, GPIO.LOW)

					if specialKeyPushed:
						time.sleep(.2)

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
