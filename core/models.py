import datetime
import hashlib
import random

from  bass_hunter.app import db
from sqlalchemy.dialects.postgresql import JSON

def make_random():
	random = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])
	return hashlib.md5(random)


class Result(db.Model):
	''' this is the result of the word association analysis '''
	__tablename__='nlp_results'
	
	id = db.Column(db.Integer, primary_key=True)
	url = db.Column(db.String)
	result_all = db.Column(JSON)
	result_no_stop_words = db.Column(JSON)
	added = db.Column(db.Datetime, default=datetime.datetime.now)

	def __init__(self, url, result_all, result_no_stop_words):
		self.url = url
		self.result_all = result_all
		self.result_no_stop_words = result_no_stop_words

	def __repr__(self):
		return '<id {}>'.format(self.id)

class API_Users(db.Model):
	''' api_users table '''
	__tablename__='api_users'
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String, nullable=False)
	added = db.Column(db.Datetime, default=datetime.datetime.now)
	disabled = db.Column(db.Boolean, default=False)	
	auth_hash = db.Column(db.String, default=make_random())
	
	def __init__(self, username):
		self.username=username
	
	def __repr__(self):
		return '<id {}>'.format(self.id)

class Images(db.Model):
	''' table for the images that are taken when dota screenshots an image '''
	__tablename__='images'
	id = db.Column(db.Integer, primary_key=True)
	url = db.Column(db.String)
	image_hash = db.Column(db.String)
	path_to_file = db.Column(db.Text)
	ocr_data = db.Column(db.Text)
	added = db.Column(db.Datetime, default=datetime.datetime.now)
	
	def __init__(self, url, image_hash, path_to_file, ocr_data):
		self.url = url
		self.image_hash = image_hash
		self.path_to_file = path_to_file
		self.ocr_data = ocr_data

	def __repr__(self):
		return '<id {}'.format(self.id)
