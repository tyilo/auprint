from sys import exit
import socket
from subprocess import check_call, check_output, CalledProcessError
from getpass import getpass
import configparser
from urllib.parse import quote


class Config(object):
	def __init__(self, filename):
		self._cp = configparser.ConfigParser()
		self._filename = filename
		self._cp.read(filename)

	def __setattr__(self, key, value):
		if key.startswith('_'):
			super().__setattr__(key, value)
			return

		if value is None:
			self._cp.remove_option(self._cp.default_section, key)
		else:
			self._cp.set(self._cp.default_section, key, value)

		with open(self._filename, 'w') as f:
			self._cp.write(f)

	def __getattribute__(self, key):
		if key.startswith('_'):
			return super().__getattribute__(key)

		return self._cp.get(self._cp.default_section, key, fallback=None)


class AUAuthenticationError(BaseException):
	pass


class PrinterNotFoundError(BaseException):
	pass


class AUPrint(object):
	HOST = 'print.uni.au.dk'
	IP = socket.gethostbyname(HOST)
	PPD = '/usr/share/ppd/cupsfilters/Generic-PDF_Printer-PDF.ppd'
	DOMAIN = 'uni'
	BUILDING_NAMES = {
		'1530': 'matematik',

		'5335': 'nygaard',
		'5340': 'babbage',
		'5341': 'turing',
		'5342': 'ada',
		'5343': 'bush',
		'5344': 'benjamin',
		'5345': 'dreyer',
		'5346': 'hopper',
		'5347': 'wiener',
	}
	BUILDING_NUMBERS = {v: k for k, v in BUILDING_NAMES.items()}

	auid = None
	password = None
	printers = None

	def __init__(self, auid, password):
		self.auid = auid
		self.password = password

		try:
			self.printers = self.get_remote_printer_list()
		except CalledProcessError:
			raise AUAuthenticationError()

	def pretty_name(self, name):
		parts = name.split('-')
		if len(parts) == 1:
			return name

		building = self.BUILDING_NAMES.get(parts[0], parts[0])
		number = parts[1]

		return '%s-%s' % (building, number)

	def get_remote_printer_list(self):
		out = str(check_output(['smbclient', '-I', self.HOST, '-L', self.HOST, '-U',
								'{}\\{}%{}'.format(self.DOMAIN, self.auid, quote(self.password, safe=''))]), 'utf-8')
		printers = {}
		for l in out.split('\n'):
			if not l.startswith('\t'):
				continue

			parts = l.strip().split(maxsplit=2)
			if len(parts) != 3:
				continue

			name, typ, description = parts
			if typ != 'Printer':
				continue

			printers[name] = description

		return printers

	def local_printer_names(self):
		try:
			out = str(check_output(['lpstat', '-p']), 'utf-8')
			printers = []
			for l in out.split('\n'):
				if not l.startswith('printer'):
					continue

				name = l.split()[1]
				printers.append(name)

			return printers
		except CalledProcessError:
			return []

	def install_printer(self, name, install_name):
		if name in self.printers:
			check_call(['lpadmin', '-p', install_name, '-E', '-P', self.PPD, '-v',
			            'smb://{}\\{}:{}@{}/{}'.format(self.DOMAIN, self.auid, quote(self.password, safe=''), self.IP, name)])
		else:
			raise PrinterNotFoundError()

	def delete_printer(self, name):
		if name in self.local_printer_names():
			check_call(['lpadmin', '-x', name])
		else:
			raise PrinterNotFoundError()

	def print(self, name, f):
		if name in self.local_printer_names():
			check_call(['lpr', '-E', '-P', name, f])
		else:
			raise PrinterNotFoundError()


if __name__ == '__main__':
	config = Config('config.ini')

	logged_in = False
	while not logged_in:
		while not config.auid:
			config.auid = input('AUID: ').strip()
			if not config.auid.startswith('au'):
				config.auid = None

		while not config.password:
			config.password = getpass().strip()

		try:
			auprint = AUPrint(config.auid, config.password)
			logged_in = True
		except AUAuthenticationError:
			print('Invalid auid/password combination')
			config.auid = None
			config.password = None

	printers = auprint.get_remote_printer_list()

	building = input('Building number/name: ')
	building_number = AUPrint.BUILDING_NUMBERS.get(building, building)

	matched_printers = [p for p in printers if p.startswith(building_number)]
	if len(matched_printers) == 0:
		print('No printers found')
	else:
		print('Available printers: ')
		for i, p in enumerate(matched_printers):
			print('(%s)\t%s' % (i + 1, p))

		opt = input('Printer to install: ')
		try:
			opt = int(opt)
		except ValueError:
			exit()

		opt -= 1
		if not (0 <= opt < len(matched_printers)):
			exit()

		printer = matched_printers[opt]
		name = auprint.pretty_name(printer)

		print()
		print('Selected', printer)
		custom_name = input('Install name [%s]: ' % name)
		if custom_name:
			name = custom_name

		auprint.install_printer(printer, name)

		print('Successfully added printer %s as %s' % (printer, name))
