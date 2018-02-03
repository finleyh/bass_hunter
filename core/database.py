#

import datetime
import json
import logging
import os
import hashlib

from sqlalchemy import create_engine, Column, not_, func
from sqlalchemy import Interger, String, Boolean, DateTime, Enum
from sqlalchemy import ForeignKey, Text, Index, Table, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relationship, joinedload

Base = declartive_base()

#Base database setup
#enumerative types to describe tasks

PENDING="pending"
RUNNING = "running"
COMPLETED = "completed"
RECOVERED = "recovered"
FAILED = "failed"

task_status = Enum(
	PENDING, RUNNING, COMPLETED, REPORTED, FAILED, name="status_type"
)

class Domain(Base):
	""" Submitted domain for analysis """
	__tablename__ = "domains"

	id = Column(Integer(), primary_key=True)
	domain_name = Column(String(255), nullable=False)
	md5 = Column(String(8), nullable=False)
	sha256 = Column(String(64), nullable=False)
	__table_args__ = Index("hash_index","sha256",unique=True),
	
	def __repr__(self):
		return "<Domain('{0}','{1}')>".format(self.id,self.sha256)

	def to_dict(self):
	"""Converts object to dict.
	@return: dict
	"""
		d = {}
		for column in self.__table__.columns:
			d[column.name] = getattr(self, column.name)
		return d
	
	def to_json(self):
		"""Converts object to JSON.
		@return: JSON data
		"""
		json.dumps(self.to_dict())

	def __init__(self, domain_name, md5, sha256):
		self.domain_name = domain_name
		self.md5 = hashlib.md5(domain_name)
		self.sha256 = hashlib.sha256(domain_name)


class Task(Base):
	""" Analysis Tasks """
	__tablename__ = "tasks"

	id = Column(Integer(), primary_key=True)
	target = Column(Text(), nullable=False) #domain to analyze
	package = Column(String(255), nullable=True)
	owner = Column(String(64), nullable=True)
	tags = relationship("Tag", secondary=tasks_tags, single_parent=True, backref="task", lazy="subquery")
	added_on = Column(DateTime(timezone=False),
		default=datetime.datetime.now,
		nullable=False)
	started_on = Column(DateTime(timezone=False), nullable=True)
	completed_on = Column(DateTime(timezone=False), nullable=True)
	status = Column(status_type, server_default=TASK_PENDING, nullable=False)
	sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True)
	submit_id = Column(
		Integer,ForeignKey("submit.id"), nullable=True, index=True
	)
	domain = relationship("Domain", backref="tasks")
	submit = relationship("Submit", backref="tasks")
	errors = relationship("Error", backref="tasks", cascade="save-update, delete")
	
	def duration(self):
		if self.started_on and self.completed_on:
			return (self.completed_on - self.started_on).seconds
		return -1
	
	@hybrid_property
    	def options(self):
        	if not self._options:
        	    	return {}
        	return parse_options(self._options)

    	@options.setter
    	def options(self, value):
        	if isinstance(value, dict):
        		self._options = emit_options(value)
        	else:
			self._options = value

	def to_dict(self, dt=False):
        """Converts object to dict.
        @param dt: encode datetime objects
        @return: dict
        """
        	d = Dictionary()
        	for column in self.__table__.columns:
        		value = getattr(self, column.name)
        		if dt and isinstance(value, datetime.datetime):
        			d[column.name] = value.strftime("%Y-%m-%d %H:%M:%S")
        		else:
        			d[column.name] = value

        	# Tags are a relation so no column to iterate.
        	d["tags"] = [tag.name for tag in self.tags]
        	d["duration"] = self.duration()
 	       return d

	def to_json(self):
		"""Converts object to JSON.
		@return: JSON data
		"""
		return json_encode(self.to_dict())

	def __init__(self, target=None, id=None, category=None):
		self.target = target
		self.id = id
		self.category = category

	def __repr__(self):
		return "<Task('{0}','{1}')>".format(self.id, self.target)

class Database(object):
	"""Analysis queueu database.
		
	this class handles the creation of the database user for internal queue management, and provides functions for interacting with it """
	__metaclass__=Singleton
