#!/usr/bin/env python3

from sys import exit
import socket
from subprocess import check_call, check_output, CalledProcessError
from getpass import getpass
from urllib.parse import quote
import argparse
import keyring
from pathlib import Path


class LocalAuth:
	def __init__(self, filename):
		self.filename = filename
		try:
			with open(filename) as f:
				self.username = f.read().strip()
		except IOError:
			self.username = None

		self.password = keyring.get_password('auprint', 'auid')

	def __setattr__(self, key, value):
		super().__setattr__(key, value)

		if key == 'username':
			try:
				if value == None:
					Path(self.filename).unlink()
				else:
					with open(self.filename, 'w') as f:
						f.write(self.username)
			except IOError:
				pass
		elif key == 'password':
			if value == None:
				try:
					keyring.delete_password('auprint', 'auid')
				except keyring.errors.PasswordDeleteError:
					pass
			else:
				keyring.set_password('auprint', 'auid', value)


class AUAuthenticationError(BaseException):
	pass


class PrinterNotFoundError(BaseException):
	pass


class AUPrint:
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

	def printer_url(self, name):
		return 'smb://{}\\{}:{}@{}/{}'.format(self.DOMAIN, self.auid, quote(self.password, safe=''), self.IP, name)

	def update_authentication(self, name, install_name):
		check_call(['lpadmin', '-p', install_name, '-v', self.printer_url(name)])

	def get_local_printers(self):
		try:
			out = str(check_output(['lpstat', '-v']), 'utf-8').strip()
			printers = []
			for l in out.split('\n'):
				url = l.split()[-1]
				if not url.startswith('smb://{}/'.format(self.IP)):
					continue

				name = url.split('/')[-1]
				install_name = l.split()[2].split(':')[0]
				printers.append((name, install_name))

			return printers
		except CalledProcessError:
			return []

	def install_printer(self, name, install_name):
		if name in self.printers:
			check_call(['lpadmin', '-p', install_name, '-E', '-P', self.PPD, '-v',
			            self.printer_url(name)])
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
	parser = argparse.ArgumentParser(description='Manages installed printers at AU')
	parser.add_argument('--update-passwords', action='store_true', help='Update passwords used for printers')

	args = parser.parse_args()

	auth = LocalAuth('auid.txt')

	logged_in = False
	while not logged_in:
		while not auth.username:
			auth.username = input('AUID: ').strip()
			if not auth.username.startswith('au'):
				auth.username = None

		while not auth.password:
			auth.password = getpass().strip()

		try:
			auprint = AUPrint(auth.username, auth.password)
			logged_in = True
		except AUAuthenticationError:
			print('Invalid auid/password combination')
			auth.username = None
			auth.password = None

	printers = auprint.get_remote_printer_list()

	if args.update_passwords:
		printers = auprint.get_local_printers()
		for name, install_name in printers:
			auprint.update_authentication(name, install_name)
			print('Updated password for {} at {}'.format(name, install_name))
	else:
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
