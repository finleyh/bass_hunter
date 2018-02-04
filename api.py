#!/usr/bin/env python
import datetime
import hashlib
import io
import multiprocessing
import os
import socket
import tarfile
import zipfile

from flask import Flask, request, jsonify 

from core.database import Database, Task
from core.database import REPORTED, COMPLETED, RUNNING


db=Database()


app = Flask(__name__)


#define a connection string to your database
#db conn string here    #ignoreline

#define  the base api path
API_PATH='/api/v1/'


print "testing ignore line" #ignoreline


@app.route('/')
def index():
	return "Testing: Hello, World!"
#/api/v1/domains
# list domains
@app.route(API_PATH+'domains', methods=['GET'])
def list_domains():
	#TODO list domains
	return jsonify({''}), 201

#create a new domain to monitor
@app.route(API_PATH+'domains', methods=['POST'])
def remove_domains():
	return jsonify({''}), 201

#delete a given domain
@app.route(API_PATH+'domains/<domain>', methods=['DELETE'])

#/api/v1/domain/$1/images -- list all images
@app.route(API_PATH+'domain/<domain>/images',methods=['GET'])
def show_domain_images():
	return jsonify({''}), 201


if __name__=='__main__':
	app.run(debug=True)
