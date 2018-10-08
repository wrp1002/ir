import pyslingerTEST
import urllib2
import cPickle as pickle
import re
import time
import RPi.GPIO as GPIO
import random

class CodeManager():
	def __init__(self):
		try:
			self.codes = []
			self.brands = []
			self.brands = self.LoadBrands()
			self.codes = self.LoadCodes()
			self.ir = pyslingerTEST.IR(3, "NEC")
			self.buttonNames = {"button0":"KEY_POWER", "1":"KEY_VOLUMEUP", "4":"KEY_VOLUMEDOWN", "2":"KEY_CHANNELUP", "5":"KEY_CHANNELDOWN", "A":"KEY_MUTE"}
			self.importantCodes = [["KEY_POWER"], ["KEY_VOLUMEUP", "VOL_UP", "KEY_VIDEO"], ["KEY_VOLUMEDOWN", "VOL_DWN", "MEMORY"], ["KEY_CHANNELUP", "CH_UP", "DIGITALZOOM+", "KEY_ZOOMIN", "ASPECT"], ["KEY_CHANNELDOWN", "CH_DWN", "CHDN", "DIGITALZOOM-", "KEY_ZOOMOUT", "COLOR-MODE"], ["KEY_MUTE", "KEY_ZOOMIN", "INPUT-A-B", "KEY_ESC"]]
			self.allMode = False

		except IOError:
			print "Brands file not found"

	def GetImportantCode(self, cmd):
		for iCode in self.importantCodes:
			for innerICode in iCode:
				if cmd == innerICode:
					return iCode[0]

		return ""

	def DeleteBrand(self, brand):
		if brand in self.brands:
			self.brands.remove(brand)
			self.codes = self.LoadCodes()
			
			for i in range(len(self.codes) - 1, -1, -1):
				if self.codes[i][0]["brand"] == brand:
					del self.codes[i]

			self.SaveCodes()
			self.SaveBrands()

			print "Deleted", brand
		else:
			print "Brand not found"

	def input(self, low, high):
		val = low - 1
		while val < low or val > high:
			try:
				val = int(raw_input(">"))
				if val < low or val > high: raise ValueError()

			except ValueError:
				print "Must enter number between ", low, "and", high
		return val
		

	def LoadBrands(self):
		return pickle.load(open("Resources/brands", "rb"))

	def SaveBrands(self):
		print "saving brands..."
		pickle.dump(self.brands, open("Resources/brands", "wb"), protocol=pickle.HIGHEST_PROTOCOL)

	def LoadCodes(self):
		return pickle.load(open("Resources/save", "rb"))

	def SaveCodes(self):
		print "saving codes..."
		pickle.dump(self.codes, open("Resources/save", "wb"), protocol=pickle.HIGHEST_PROTOCOL)

	#distribute codes so that codes with the same brand are as far apart as possible to avoid conflicts
	def DistributeCodes(self):
		temp = self.codes[:]
		brandsList = self.brands

		while len(temp) > 0:
			pass


	def SendCode(self, cmd, index):
		amount = len(self.codes)
		if not self.allMode:
			amount = 5
		else:
			index = 0

		#print index

		try:
			if cmd == "D":
				raise KeyboardInterrupt()
			elif cmd == "*":
				self.allMode = not self.allMode
				return False
			elif cmd == "B" or cmd == "C":
				pass
			else:
				for i in range(index, index + amount):
				#for i in range(len(self.codes)):

					if i >= len(self.codes):
						break
					
					code = self.codes[i]

					if cmd in self.buttonNames:
						codeName = self.buttonNames[cmd]
						if codeName in code[1]:
							for innerIndex in range(len(code[1][codeName])):
								innerCode = code[1][codeName][innerIndex]
								#print "index: ", i, "innerindex: ", innerIndex
								
								self.ir.send_processed_code(innerCode)
						else:
							print "Command not found"
					else:
						print "Button not found"
			return True

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
		random.shuffle(self.codes)


	def Download(self, mode):
		autosave = False
		print "\nAutosave?\n1. Yes\n2. No"
		if self.input(1, 2) == 1:
			autosave = True

		importantInfo = ["header", "one", "zero", "name", "bits", "ptrail", "pre_data_bits", "pre_data", "gap", "duty_cycle"]

		if mode == 0:
			self.codes = []
			self.brands = []
		elif mode == 1:
			pass
		elif mode == 2:
			self.codes = []

		startLen = len(self.codes)
		if mode == 0 or mode == 1:
			input = raw_input("Enter brands separated by commas: ")
		urls = []

		tempBrands = self.brands
		if mode == 0 or mode == 1:
			tempBrands = input.split(",")


		print "Codes: ", len(self.codes)
		print "brands: ", len(self.brands)

		for brand in tempBrands[:]:
			baseURL = "http://lirc.sourceforge.net/remotes/" + brand + "/"

			try:
				download = True
				if brand in self.brands:
					print "\n", brand, "already downloaded. Redownload?\n1. Yes\n2. No"
					if self.input(1, 2) == 1:
						self.DeleteBrand(brand)
					else:
						download = False
				if download:
					response = urllib2.urlopen(baseURL)
					html = response.read()
					urlsTemp = html[html.find("Parent Directory"):].rsplit("</tr>")[1:-2]

					for i in range(len(urlsTemp)):
							urlsTemp[i] = urlsTemp[i][urlsTemp[i].find("href="):urlsTemp[i].find("</a>")]
							urlsTemp[i] = urlsTemp[i][urlsTemp[i].find("\">")+2:]
							urlsTemp[i] = baseURL + urlsTemp[i]

					urls += urlsTemp
			except urllib2.HTTPError:
				tempBrands.remove(brand)
				print "Error: ", baseURL, "not found"
				print "Continue?\n1. Yes\n2. No"
				if self.input(1, 2) == 2:
					quit()


		print "URLs found:"
		for i in urls:
			print i


		print "Gathering codes..."

		times = []
		avgTime = 0
		amountMeasured = 0

		for url in urls:
			startTime = time.time()
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

			if "jpg" in url or "jpeg" in url or "gif" in url:
				print "Skipping ", url
				continue

			print "Opening", url
			response = urllib2.urlopen(url)

			html = response.read()

			print "Reading..."
 
			for i in html:
				if i != "\n":
					line += i
				else:
					if len(line) > 0 and line[0] != "#":
						lines.append(" ".join(line.split()).split("#", 1)[0])
					line = ""

			foundCodes = []
			for i in lines:
				split = i.find(' ')
				name = i[:split]
				val = i[split + 1:].strip(" ")

				#print name, val

				if i != "begin remote" and i != "begin codes" and i != "end codes" and i != "end codes":
					if startCodes:
						name = name.upper()
						foundCodes.append(name)

						tmp = self.GetImportantCode(name)
						if tmp and " " not in val:
							newCodes[tmp] = val
						elif " " in val:
							print "Error: Space found in code", name, val

					elif name in importantInfo:
						newInfo[name] = val
				elif i == "begin codes":
					startCodes = True

			if "header" in newInfo:
				#print newInfo["header"]
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

			print newCode

			#print newCode[0]

			for cmd in newCode[1]:
				converted = ""
				if "pre_data" in newCode[0] and "pre_data_bits" in newCode[0]:
					converted += bin(int(newCode[0]["pre_data"], 16))[2:].zfill(int(newCode[0]["pre_data_bits"]))

				converted += bin(int(newCode[1][cmd], 16))[2:].zfill(int(newCode[0]["bits"]))
				newCode[1][cmd] = [converted]

			#print newCode

			isTV = False
			found = []
			for i in newCodes:
				temp = self.GetImportantCode(i)
				if temp:
					found.append(temp)

			if len(found) == len(self.importantCodes):
				isTV = True
				print "----------TV----------------------------------"
			else:
				print "Names found", foundCodes
				if "name" in newInfo:
					print newInfo["name"]
				for iCode in self.importantCodes:
					found = False
					for innerCode in iCode:
						if innerCode in newCodes:
							found = True
							break
					if not found:
						print iCode, " not found"
			#isTV = True

			duplicate = False
			if isTV and len(self.codes) > 0:
				for i in range(len(self.codes)):
					otherCode = self.codes[i]
					sameDict = True

					if set(newCode[2].keys()) == set(otherCode[2].keys()) and newCode[0]["brand"] == otherCode[0]["brand"]:
						for info in newCode[2]:
							if info == "frequency" or info == "duty_cycle" or info == "trailing_pulse":
								if newCode[2][info] != otherCode[2][info]:
									print "different dict because ", info, newCode[2][info], " != ", otherCode[2][info]
									sameDict = False
									break
							elif abs(newCode[2][info] - otherCode[2][info]) > 300:
								print "different dict because ", info, abs(newCode[2][info] - otherCode[2][info]), " > 300"
								sameDict = False
								break
					else:
						print "Different dict because different dict keys or different brand"
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
							for cmd in otherCode[1]:
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

			times.append(time.time() - startTime)
			avgTime = sum(times) / len(times)
			timeLeft = avgTime * (len(urls) - len(times))
			minutes = int(timeLeft / 60)
			seconds = int(timeLeft % 60)

			print int(float(urls.index(url)) / len(urls) * 100), "%", timeLeft, " seconds left ", minutes, "m", seconds, "s"


		print "\nSave", len(self.codes) - startLen, " new codes?"
		print "1. Yes"
		print "2. No"
		input = 1 
		if not autosave:
			self.input(1, 2)

		if input == 1:
			self.SaveCodes()
			for b in tempBrands:
				self.brands.append(b)
			self.SaveBrands()

		#self.ConvertCodes()




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


