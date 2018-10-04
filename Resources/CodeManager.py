import pyslingerTEST
import urllib2
import cPickle as pickle
import re
import time
import RPi.GPIO as GPIO

class CodeManager():
	def __init__(self):
		try:
			self.codes = []
			self.brands = []
			self.brands = self.LoadBrands()
			self.codes = self.LoadCodes()
			self.ir = pyslingerTEST.IR(3, "NEC")
			self.buttonNames = {"button0":"KEY_POWER", "1":"KEY_VOLUMEUP", "4":"KEY_VOLUMEDOWN", "2":"KEY_CHANNELUP", "5":"KEY_CHANNELDOWN", "A":"KEY_MUTE"}

		except IOError:
			print "Brands file not found"

	def LoadBrands(self):
		return pickle.load(open("Resources/brands", "rb"))

	def SaveBrands(self):
		pickle.dump(self.brands, open("Resources/brands", "wb"), protocol=pickle.HIGHEST_PROTOCOL)

	def LoadCodes(self):
		return pickle.load(open("Resources/save", "rb"))

	def SaveCodes(self):
		print "saving..."
		pickle.dump(self.codes, open("Resources/save", "wb"), protocol=pickle.HIGHEST_PROTOCOL)

	def SendCode(self, index, cmd):
		try:
			if cmd == "D":
				raise KeyboardInterrupt()
			#for i in range(index, index + 10):
			for i in range(len(self.codes)):
				if i >= len(self.codes) - 1:
					return 

				code = self.codes[i]

				if cmd in self.buttonNames:
					codeName = self.buttonNames[cmd]
					if codeName in code[1]:
						for innerCode in code[1][codeName]:
							print innerCode
							#self.ir.send_code(innerCode, code[2])
							self.ir.send_processed_code(innerCode)
					else:
						print "Command not found"
				else:
					print "Button not found"

		except KeyboardInterrupt:
			print "Cleaning up"
			self.ir.cleanup()
			GPIO.cleanup()
			quit()

		except ValueError:
			print "Error with code", code
			return

	def ConvertCodes(self):
		print "Converting..."
		startLen = len(self.codes)
		for i in range(len(self.codes)):
			print int(float(i) / startLen * 100), "%"
			for code in self.codes[i][1]:
				#print code, self.codes[i][1][code]
				for j in range(len(self.codes[i][1][code])):
					temp = self.ir.process_and_return(self.codes[i][1][code][j], self.codes[i][2])
					self.codes[i][1][code][j] = temp
					#print innerCode
					#pass
					


	def Download(self):
		importantInfo = ["header", "one", "zero", "name", "bits", "ptrail", "pre_data_bits", "pre_data", "gap", "duty_cycle"]
		importantCodes = ["KEY_POWER", "KEY_VOLUMEUP", "KEY_VOLUMEDOWN", "KEY_CHANNELUP", "KEY_CHANNELDOWN", "KEY_MUTE"]

		self.codes = []
		startLen = len(self.codes)
		input = raw_input("Enter brands separated by commas: ")
		urls = []

		tempBrands = input.split(",")


		for brand in tempBrands:
			baseURL = "http://lirc.sourceforge.net/remotes/" + brand + "/"

			response = urllib2.urlopen(baseURL)
			html = response.read()
			urlsTemp = html[html.find("Parent Directory"):].rsplit("</tr>")[1:-2]

			for i in range(len(urlsTemp)):
					urlsTemp[i] = urlsTemp[i][urlsTemp[i].find("href="):urlsTemp[i].find("</a>")]
					urlsTemp[i] = urlsTemp[i][urlsTemp[i].find("\">")+2:]
					urlsTemp[i] = baseURL + urlsTemp[i]

			urls += urlsTemp

		print "URLs found:"
		for i in urls:
			print i


		print "Gathering codes..."

		for url in urls:
			newInfo = {}
			newCodes = {}
			newDict = {
				"frequency":38000,
				"duty_cycle":0.5,
				"leading_pulse_duration":9000,
				"leading_gap_duration":4500,
				"one_pulse_duration":562,
				"one_gap_duration":1687,
				"zero_pulse_duration":562,
				"zero_gap_duration":562,
				"trailing_pulse":1
			}

			lines = []
			line = ""
			startCodes = False
			tempURL = url[:url.rfind("/")]
			brand = tempURL[tempURL.rfind("/") + 1:]
			newInfo["brand"] = brand

			print int(float(urls.index(url)) / len(urls) * 100), "%"

			if "jpg" in url or "jpeg" in url or "gif" in url:
				print "Skipping ", url
				continue

			print "Opening", url
			response = urllib2.urlopen(url)

			html = response.read()

			print "Reading..."
 #\t to match a tab character (ASCII 0x09), \r for carriage return (0x0D) and \n for line feed (0x0A). More exotic non-printables are \a (bell, 0x07), \e (escape, 0x1B), and \f (form feed, 0x0C). Remember that Windows text files use \r\n
			for i in html:
				if i != "\n":
					line += i
				else:
					if len(line) > 0 and line[0] != "#":
						lines.append(" ".join(line.split()).split("#", 1)[0])
					line = ""

			for i in lines:
				split = i.find(' ')
				name = i[:split]
				val = i[split + 1:]

				#print name, val

				if i != "begin remote" and i != "begin codes" and i != "end codes" and i != "end codes":
					if startCodes:
						if name in importantCodes:
							newCodes[name] = val

					elif name in importantInfo:
						newInfo[name] = val
				elif i == "begin codes":
					startCodes = True


			if "header" in newInfo:
				print newInfo["header"]
				newDict["leading_pulse_duration"] = int(newInfo["header"].split(" ")[0])
				newDict["leading_gap_duration"] = int(newInfo["header"].split(" ")[1])

			if "one" in newInfo:
				newDict["one_pulse_duration"] = int(newInfo["one"].split(" ")[0])
				newDict["one_gap_duration"] = int(newInfo["one"].split(" ")[1])

			if "zero" in newInfo:
				newDict["zero_pulse_duration"] = int(newInfo["zero"].split(" ")[0])
				newDict["zero_gap_duration"] = int(newInfo["zero"].split(" ")[1])

			if "duty_cycle" in newInfo:
				newDict["duty_cycle"] = int(newInfo["duty_cycle"]) / 100.0
			if "frequency" in newInfo:
				newDict["frequency"] = int(newInfo["frequency"])

			newCode = [newInfo, newCodes, newDict]

			print newCode[0]

			for cmd in newCode[1]:
				converted = ""
				if "pre_data" in newCode[0] and "pre_data_bits" in newCode[0]:
					converted += bin(int(newCode[0]["pre_data"], 16))[2:].zfill(int(newCode[0]["pre_data_bits"]))

				converted += bin(int(newCode[1][cmd], 16))[2:].zfill(int(newCode[0]["bits"]))
				newCode[1][cmd] = [converted]

			#print newCode

			isTV = False
			if all(name in newCodes for name in importantCodes):
				isTV = True
				print "----------TV----------------------------------"
			else:
				if "name" in newInfo:
					print newInfo["name"]
				for name in importantCodes:
					if not name in newCodes:
						print name, " not found"
			#isTV = True

			duplicate = False
			if isTV and len(self.codes) > 0:
				for i in range(len(self.codes)):
					otherCode = self.codes[i]
					sameDict = True

					if set(newCode[2].keys()) == set(otherCode[2].keys()):
						for info in newCode[2]:
							if info == "frequency" or info == "duty_cycle" or info == "trailing_pulse":
								if newCode[2][info] != otherCode[2][info]:
									print "different dict because ", info, newCode[2][info], " != ", otherCode[2][info]
									sameDict = False
									break
							elif abs(newCode[2][info] - otherCode[2][info]) > 150:
								print "different dict because ", info, abs(newCode[2][info] - otherCode[2][info]), " > 150"
								sameDict = False
								break
					else:
						print "Different dict because different dict keys"
						sameDict = False

					if sameDict:
						print "same dictionaries!"
						print newCode[1]
						print otherCode[1]
						sameCodes = False

						for cmd in otherCode[1]:
							if cmd in newCode[1]:
								for c in range(len(otherCode[1][cmd])):
									if newCode[1][cmd][0] == otherCode[1][cmd][c]:
										print "Same Code: ", cmd
										sameCodes = True
										duplicate = True
										if "name" in newCode[0]:
											if "name" in self.codes[i][0]:
												self.codes[i][0]["name"] += "," + newCode[0]["name"]
											else:
												self.codes[i][0]["name"] = newCode[0]["name"]
										break
							
							if sameCodes:
								for c in range(len(otherCode[1][cmd])):
									if newCode[1][cmd][0] not in otherCode[1][cmd]:
										print "Differnet Code Added: ", cmd
										self.codes[i][1][cmd].append(newCode[1][cmd][0])
							else:
								print "No codes in common"
								
			else:
				duplicate = False

			#duplicate = False

			if isTV and not duplicate:
				self.codes.append(newCode)
			else:
				print "Not Added:"
				if not isTV:
					print "Not TV"
				elif duplicate:
					print "Duplicate"

		print "\nSave", len(self.codes) - startLen, " new codes?"
		print "1. Yes"
		print "2. No"
		input = raw_input("Enter Option: ")

		if input == "1":
			self.SaveCodes()
			self.brands = tempBrands
			self.SaveBrands()

		self.ConvertCodes()




	def DownloadOld(self):
		self.codes = []
		startLen = len(self.codes)
		input = raw_input("Enter brands separated by commas: ")
		urls = []

		tempBrands = input.split(",")


		for brand in tempBrands:
			baseURL = "http://lirc.sourceforge.net/remotes/" + brand + "/"

			response = urllib2.urlopen(baseURL)
			html = response.read()
			urlsTemp = html[html.find("Parent Directory"):].rsplit("</tr>")[1:-2]

			for i in range(len(urlsTemp)):
					urlsTemp[i] = urlsTemp[i][urlsTemp[i].find("href="):urlsTemp[i].find("</a>")]
					urlsTemp[i] = urlsTemp[i][urlsTemp[i].find("\">")+2:]
					urlsTemp[i] = baseURL + urlsTemp[i]

			urls += urlsTemp

		print "URLs found:"
		for i in urls:
			print i



		print "Gathering codes..."

		for url in urls:
			print int(float(urls.index(url)) / len(urls) * 100), "%"

			if "jpg" in url or "jpeg" in url or "gif" in url:
				print "Skipping ", url
				continue
			print "Opening", url
			response = urllib2.urlopen(url)

			html = response.read()

			print "Reading..."

			lines = []
			line = ""
			codesDict = {}
			info = {}
			startCodes = False

			for i in html:
				if i != "\n":
					line += i
				else:
					if len(line) > 0 and line[0] != "#":
						lines.append(re.sub(r'( )\1+', ' ', line.lstrip()).split("#", 1)[0])
					line = ""

			for i in lines:
				split = i.find(' ')
				name = i[:split]
				val = i[split + 1:]

				if i != "begin remote" and i != "begin codes" and i != "end codes" and i != "end codes":
					if startCodes:
						codesDict[name] = val
					else:
						info[name] = val
				elif i == "begin codes":
					startCodes = True

			dict = {
				"frequency":38000,
				"duty_cycle":0.5,
				"leading_pulse_duration":9000,
				"leading_gap_duration":4500,
				"one_pulse_duration":562,
				"one_gap_duration":1687,
				"zero_pulse_duration":562,
				"zero_gap_duration":562,
				"trailing_pulse":1
			}

			#print info
			#print codesDict

			if "header" in info:
				dict["leading_pulse_duration"] = int(info["header"].split(" ")[0])
				dict["leading_gap_duration"] = int(info["header"].split(" ")[1])

			if "one" in info:
				dict["one_pulse_duration"] = int(info["one"].split(" ")[0])
				dict["one_gap_duration"] = int(info["one"].split(" ")[1])

			if "zero" in info:
				dict["zero_pulse_duration"] = int(info["zero"].split(" ")[0])
				dict["zero_gap_duration"] = int(info["zero"].split(" ")[1])

			#if len(codes) > 0 and [codesDict, dict] in [zip(*codes)[1], zip(*codes)[2]]:
			#	print "Duplicate!"
			#else:

			importantCodes = ["KEY_POWER", "KEY_VOLUMEUP", "KEY_VOLUMEDOWN", "KEY_CHANNELUP", "KEY_CHANNELDOWN", "KEY_MUTE"]

			isTV = False
			if all(name in codesDict for name in importantCodes):
				isTV = True

			#for testing
			isTV = True

			duplicate = False
			if len(self.codes) > 0:
				currentCodes = zip(*self.codes)[1]


		#		print currentCodes.
				#print currentCodes.values

				for iCode in importantCodes:
					for codeList in currentCodes:
						if set(codesDict) == set(codeList):
							duplicate = True
							break
					if duplicate:
						break

			for codeName in codesDict.keys():
				if not codeName in importantCodes:
					del codesDict[codeName]


			if not duplicate and isTV or len(self.codes) == 0:
				self.codes.append([info, codesDict, dict])
			else:
				if duplicate:
					print "Duplicate"
				print "Not Adding"

		#codes = Convert(codes)

		print "\nSave", len(self.codes) - startLen, " new codes?"
		print "1. Yes"
		print "2. No"
		input = raw_input("Enter Option: ")

		if input == "1":
			self.SaveCodes()
			self.brands = tempBrands
			self.SaveBrands()


