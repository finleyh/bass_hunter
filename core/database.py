# heavily borrowing from:
# Copyright (C) 2012-2013 Claudio Guarnieri.
# Copyright (C) 2014-2017 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.


import datetime
import json
import logging
import os
import hashlib


from cuckoo.common.utils import SuperLock, json_encode
from cuckoo.common.utils import Singleton, classlock


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

class Tag(Base):
	""" Tag for string descriptor """
	__tablename__ = "tags"


	id = Column(Integer(), primary_key=True)
	name = Column(String(255), nullable=False, unique=True)

	def __repr__(self):
		return "<Tag('{0}','{1}')>".format(self.id, self.name)

	def __init__(self, name):
		self.name= name

class Crawler(Base):
	""" Tracks a browser in flight """
	id = Column(Integer(), primary_key=True)
	status = Column(String(16), nullable=False)
	name = Column(String(255), nullable=False)
	user_agent=Column(String(255), nullable=False)
	started_on = Column(DateTime(timezone=False),
						default=datetime.datetime.now,
						nullable=False)
	shutdown_on = Column(DateTime(timezone=False), nullable=True)
	task_id = Column(Integer,
					 ForeignKey("task.id"),
					 nullable=False,
					 unique=True)

	def __repr__(self):
		return "<Crawler('{0}', '{1}')>".format(self.id, self.name)
	
	def to_dict(self):
		d={}
		for column in self.__table__.columns:
			value=getattr(self, column.name)
			if isinstance(value, datetime.datetime):
				d[column.name]=value.strftime("%Y-%m-%d %H:%M:%S")
			else:
				d[column.name] = value
		return d

	def to_json(self):
		return json.dumps(self.to_dict())

	def __init__(self, name, user_agent):
		self.name=name
		self.user_agent=user_agent

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
	__metaclass__ = Singleton
	
	def __init__(self, echo=False):
		"""
		@param dsn: database connection string.
		@param schema_check: disable or enable the db schema version check.
		@param echo: echo sql queries
		"""
		self._lock = SuperLock()
		self.schema_check = None
		self.echo = echo
	
	def connect(self, dsn=None, create=True):
		""" Connect to the database backend"""
		
		if not dsn:
			dsn = config("dota:database:connection")
		if not dsn:
			print "database connection information not found in config file. exiting"
		
		self._connect_database(dsn)
		#echo is for debugging
		self.engine.echo = self.echo
		#connection timeout
		self.engine.pool_timeout = config("cuckoo:database:timeout")
	
		#get db session
		self.Session = sessionmaker(bind=self.engine)
		
		if create:
			self._create_tables()
	def _create_tables(self):
		""" Createst database tables """
		try:
			Base.metadata.create_all(self.engine)
		except SQLAlchemyError as e:
			raise CuckooDatabaseError(
				"Unable tocreate or connect to database: %s" % e
			)
	
	def __del__(self):
		""" Disconnects pool."""
		self.engine.dispose()
	
	def _connect_database(self, connection_string):
		""" Connect to a database
		@param connection_string: Connection string specifying the databse """
		try:
			self.engine=create_engine(connection_string, connect_args={"sslmode":"disable"})
		except ImportError as e:
			lib = e.message.split()[-1]
	
	def _get_or_create(self, session, model, **kwargs):
		""" Get an ORM instance or create it if not exist.
		@param session: SQLAlchemy session object
		@param model: model to query
		@return: row instance
		"""
		instance = session.query(model).filter_by(**kwargs).first()
		return instance or model(**kwargs)

	@classlock
	def drop(self):
		""" Drop all tables. """
		try:
			Base.metadata.drop_all(self.engine)
		except SQLAlchemyError as e:
			raise CuckooDatabaseError(
				"Unable to drop all the tables of the db %s" % e 
			)

	@classlock
	def set_status(self, task_id, status):
		""" set task status 
		@param task_id: task identifier
		@param status: status of the task
		@return: operation status
		"""
		session = self.Session()
		try:
			row = session.query(Task).get(task_id)
			if not row:
				return
			row.status = status
			if status == TASK_RUNNING:
				row.started_on = datetime.datetime.now()
			elif status == TASK_COMPLETED:
				row.completed_on = datetime.datetime.now()

			session.commit()
		except SQLAlchemyError as e:
			log.debug("database error setting status {0}".format(e))
			session.rollback()
		finally:
			session.close()
	
	@classlock
	def set_route(self, task_id, route):
		"""Set the taken route of this task.
		@param task_id: task identifier
		@param route: route string
		@return: operation status
		"""
		session = self.Session()
		try:
			row = session.query(Task).get(task_id)
			if not row:
				return
			
			row.route= route
			session.commit()
		except SQLAlchemyError as e:
			log.debug("Database error setting route: {0}".format(e))
			session.rollback()
		finally:
			session.close()

	@classlock
	def fetch(self, machine=None, service=True):
		"""
			go and fetch a domain for testing
		"""
		session = self.Session()
		try:
			q=session.query(Task).filter_by(status=TASK_PENDING)
		
			row = q.order_by(Task.priority.desc(), Task.added_on).first()
			if row:
				self.set_status(task_id=row.id, status=TASK_RUNNING)
				session.refresh(row)
			
			return row
		except SQLAlchemyError as e:
			log.debug("Database error fetching task: {0}".format(e))
			session.refresh(row)
		
		finally:
			session.close()
