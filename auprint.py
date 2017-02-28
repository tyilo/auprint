import socket
from subprocess import check_call, check_output, CalledProcessError, DEVNULL
from getpass import getpass

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
		'1530': 'Matematik',

		'5335': 'Nygaard',
		'5340': 'Babbage',
		'5341': 'Turing',
		'5342': 'Ada',
		'5343': 'Bush',
		'5344': 'Benjamin',
		'5345': 'Dreyer',
		'5346': 'Hopper',
		'5347': 'Wiener',
	}

	MANGLE_SUFFIX = '__auprint__'
	
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
	
	def mangle_name(self, name):
		return MANGLE_SUFFIX + name

	def demangle_name(self, name):
		if name.startswith(MANGLE_SUFFIX):
			return name[len(MANGLE_SUFFIX):]
		else:
			return None
	
	def is_auprint_printer(self, name):
		return demangle_name(name) != None

	def pretty_name(self, name):
		parts = name.split('-')
		if len(parts) == 1:
			return None
		
		building = parts[0]
		if building not in BUILDING_NAMES:
			return None

		parts[0] = BUILDING_NAMES[parts[0]]
		return '-'.join(parts)

	def get_remote_printer_list(self):
		out = str(check_output(['smbclient', '-I', self.HOST, '-L', self.HOST, '-U',
								'{}\\{}%{}'.format(self.DOMAIN, self.auid, self.password)], stderr=DEVNULL), 'utf-8')
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
				if self.is_auprint_printer(name):
					printers.append(self.demangle_name(name))

			return printers
		except CalledProcessError:
			return []

	def install_printer(self, name):
		if name in self.printers:
			check_call(['lpadmin', '-p', self.mangle(name), '-E', '-P', self.PPD, '-v',
				        'smb://{}\\{}:{}@{}/{}'.format(self.DOMAIN, self.auid, self.password, self.IP, name)])
		else:
			raise PrinterNotFoundError()

	def delete_printer(self, name):
		if name in self.local_printer_names():
			check_call(['lpadmin', '-x', self.mangle(name)])
		else:
			raise PrinterNotFoundError()
	
	def print(self, name, f):
		if name in self.local_printer_names():
			check_call(['lpr', '-E', '-P', self.mangle(name), f])
		else:
			raise PrinterNotFoundError()

if __name__ == '__main__':
	auid = 'au522953'
	password = getpass()

	P = AUPrint(auid, password)
	p = '5335-394-c'
	P.install_printer(p)
	P.print(p, '/home/asger/Downloads/pdf-sample.pdf')


