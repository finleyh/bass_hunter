#!/usr/bin/env python
import datetime
import hashlib
import io
import multiprocessing
import os
import socket
import tarfile
import zipfile
import ConfigParser

from flask import Flask, request, jsonify 

from common.constants import API_PATH
from core.database import Database, Task


db=Database()
Config = ConfigParser.ConfigParser()

def loadconfig():
	try:
		exec_path = os.path.dirname(os.path.realpath(__file__))	
		Config.read(os.path.join(exec_path,'config.ini'))
	except Exception as e:
		print "An error has occured"+str(e)
	finally:
		return


app = Flask(__name__)


#define a connection string to your database
#db conn string here    #ignoreline

#define  the base api path
API_=API_PATH


print "testing ignore line" #ignoreline


@app.route('/')
def index():
	return "Testing: Hello, World!"
#/api/v1/domains
#
#     DOMAINS
#
#read domains
@app.route(API_+'domains', methods=['GET'])
def list_domains():
	#TODO list domains
	return jsonify({''}), 201

#create domain
@app.route(API_+'domains', methods=['POST'])
def add_domains():
	return jsonify({''}), 201

#delete a domain
@app.route(API_+'domains/<domain>', methods=['DELETE'])
def remove_domain():
	return jsonify({''}), 201


#
# Results
#


@app.route(API_+'results',methods=['GET'])
def list_results():
	#only list the results of testing for the current day
	return jsonify({''}), 201

@app.route(API_+'results/<dtstring>',methods=['GET'])
def list_specific_tasks(dtstring):
	return jsonify({''}), 201


#
# images
#


#/api/v1/domain/$1/images -- list all images
@app.route(API_+'images/<domain>',methods=['GET'])
def images_by_domain(domain):
	#return only a few per page
	return jsonify({''}), 201

@app.route(API_+'images/<sha256>',methods=['GET'])
def images_by_hash(sha256):
	return jsonify({''}),201

@app.route(API_+'images/<dtstring>',methods=['GET'])
	def images_by_date(dtstring):
		return jsonify({''}),201

if __name__=='__main__':
	app.run(debug=True)
