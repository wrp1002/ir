import RPi.GPIO as GPIO
import time

class Keypad:
	def __init__(self, rows, cols, keys, buttons):
		self.GPIO_rows = rows
		self.GPIO_cols = cols
		self.keys = keys
		self.buttons = buttons

		for i in self.buttons:
			GPIO.setup(i, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

		for i in self.GPIO_rows:
			GPIO.setup(i, GPIO.OUT)

		for i in self.GPIO_cols:
			GPIO.setup(i, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

	def readKeys(self):
		key = "-1"

		for i in range(len(self.buttons)):
			if GPIO.input(self.buttons[i]):
				return "button" + str(i)


		for y in range(len(self.GPIO_rows)):
			GPIO.output(self.GPIO_rows[y], GPIO.HIGH)
			for x in range(len(self.GPIO_cols)):
				if GPIO.input(self.GPIO_cols[x]):
					key = self.keys[y][x]
			GPIO.output(self.GPIO_rows[y], GPIO.LOW)
		return key


if __name__=="__main__":
	GPIO.setmode(GPIO.BOARD)
	keys = [["1","2","3","A"],["4","5","6","B"],["7","8","9","C"],["*","0","#","D"]]
	keypad = Keypad([37, 35, 33, 31], [40, 38, 36, 32], keys, [19])
	while 1:
		key = keypad.readKeys()
		if key != "-1":
			print key
		time.sleep(.1)
