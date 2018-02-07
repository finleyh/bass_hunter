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
from core.database import REPORTED, COMPLETED, RUNNING


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
def remove_domains():
	return jsonify({''}), 201

#delete a domain
@app.route(API_+'domains/<domain>', methods=['DELETE'])
def add_domain():
	return jsonify({''}), 201

#
# Browser
#

@app.route(API_+'browsers',methods=['GET'])
def list_browsers():
	return jsonify({''}), 201

#create browser
@app.route(API_+'browsers', methods=['POST'])
def remove_browsers():
	return jsonify({''}), 201

#delete a browser
@app.route(API_+'browsers/<browser_name>', methods=['DELETE'])
def add_browser():
	#browser needs to accept a label, user_agent
	return jsonify({''}), 201


#
# Tasks
#


@app.route(API_+'tasks',methods=['GET'])
def list_tasks():
	return jsonify({''}), 201

#create task
@app.route(API_+'tasks', methods=['POST'])
def remove_tasks():
	return jsonify({''}), 201


#
# images
#


#/api/v1/domain/$1/images -- list all images
@app.route(API_+'domain/<domain>/images',methods=['GET'])
def show_domain_images():
	return jsonify({''}), 201


if __name__=='__main__':
	app.run(debug=True)
