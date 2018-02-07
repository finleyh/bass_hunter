import os
import ConfigParser

from common.constants import BASS_HUNTER_ROOT
from common.exceptions import BassHunterConfigError

class Config:
	""" Configuration File Parser """

	def __init__(self, file_name="config.ini", cfg=None):
		config = ConfigParser.ConfigParser()

		if cfg:
			config.read(cfg)
		else:
			config.read(os.path.join(BASS_HUNTER_ROOT, "conf", "%s" % file_name)

		self.fullconfig = config._sections

		for section in config.sections():
			setattr(self, section, Dictionary())
			for name, raw_value in config.items(section):
				try:
					if config.get(section, name) in ["0", "1"]:
						raise ValueError
					
					value = config.getboolean(section, name)
				except ValueError:
					try:
						value=config.getint(section, name)
					except ValueError:
						value=config.get(section, name)

				setattr(getattr(self, section), name, value)
	def get(self, section):
		""" Get option
		@param section: section to fetch
		@raise BassHunterConfigError: if section not found.
		@return: option value.
		"""
		try:
			return getattr(self, section)
		except AttributeError as e:
			raise BassHunterConfigError("Option %s is not found in configuration, error: %s" % (section, e))	

	def get_config(self):
		return self.fullconfig
