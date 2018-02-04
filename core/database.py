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


from common.utils import SuperLock, json_encode
from common.utils import Singleton, classlock


from sqlalchemy import create_engine, Column, not_, func
from sqlalchemy import Integer, String, Boolean, DateTime, Enum
from sqlalchemy import ForeignKey, Text, Index, Table, TypeDecorator
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import sessionmaker, relationship, joinedload

Base = declarative_base()

#Base database setup
#enumerative types to describe tasks

PENDING="pending"
RUNNING = "running"
COMPLETED = "completed"
REPORTED = "reported"
RECOVERED = "recovered"
FAILED = "failed"

status_type = Enum(
	PENDING, RUNNING, COMPLETED, REPORTED, FAILED, name="status_type"
)

#secondary table used in association Broser - tag
browsers_tags = Table(
	"browsers_tags", Base.metadata,
	Column("browsers_id", Integer, ForeignKey("browsers.id")),
	Column("tag_id", Integer, ForeignKey("tags.id"))
)

# Secondary table used in association Task - Tag.
tasks_tags = Table(
    "tasks_tags", Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id")),
    Column("tag_id", Integer, ForeignKey("tags.id"))
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

class JsonTypeList255(TypeDecorator):
	"""Custom JSON type."""
	impl = String(255)

	def process_bind_param(self, value, dialect):
		return json.dumps(value)

	def process_result_value(self, value, dialect):
		return json.loads(value) if value else []

class Browser(Base):
    """Configured virtual browsers to be used as guests."""
    __tablename__ = "browsers"

    id = Column(Integer(), primary_key=True)
    name = Column(String(255), nullable=False)
    label = Column(String(255), nullable=False)
    user_agent = Column(String(255), nullable=False)
    tags = relationship("Tag", secondary=browsers_tags, single_parent=True,
                        backref="browser")
    options = Column(JsonTypeList255(), nullable=True)
    status = Column(String(255), nullable=True)
    status_changed_on = Column(DateTime(timezone=False), nullable=True)

    def __repr__(self):
        return "<Browser('{0}','{1}')>".format(self.id, self.name)

    def to_dict(self):
        """Converts object to dict.
        @return: dict
        """
        d = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime.datetime):
                d[column.name] = value.strftime("%Y-%m-%d %H:%M:%S")
            else:
                d[column.name] = value

        # Tags are a relation so no column to iterate.
        d["tags"] = [tag.name for tag in self.tags]
        return d

    def to_json(self):
        """Converts object to JSON.
        @return: JSON data
        """
        return json.dumps(self.to_dict())

    def is_analysis(self):
        """Is this an analysis browser? Generally speaking all browsers are
        analysis browsers, however, this is not the case for service VMs.
        Please refer to the services auxiliary module."""
        for tag in self.tags:
            if tag.name == "service":
                return
        return True

    def __init__(self, name, label, ip, user_agent, options):
        self.name = name
        self.label = label
        self.ip = ip
        self.user_agent = user_agent
        self.options = options

class Crawler(Base):
	""" Tracks a browser in flight """
	__tablename__="crawlers"
	
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
	target = Column(Text(), nullable=False) 
	package = Column(String(255), nullable=True)
	_options = Column("options", Text(), nullable=True)
	owner = Column(String(64), nullable=True)
	tags = relationship("Tag", secondary=tasks_tags, single_parent=True, backref="task", lazy="subquery")
	added_on = Column(DateTime(timezone=False),default=datetime.datetime.now, nullable=False)
	started_on = Column(DateTime(timezone=False), nullable=True)
	completed_on = Column(DateTime(timezone=False), nullable=True)
	status = Column(status_type, server_default=PENDING, nullable=False)
	sample_id = Column(Integer, ForeignKey("samples.id"), nullable=True)
	submit_id = Column(Integer,ForeignKey("submit.id"), nullable=True, index=True)
	domain = relationship("Domain", backref="tasks")
	submit = relationship("Submit", backref="tasks")
	crawler = relationship("Crawler", backref="tasks")
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
		d = Dictionary()
		for column in self.__table__.columns:
			value = getattr(self, column.name)
			if dt and isinstance(value, datetime.datetime):
				d[column.name] = value.strftime("%Y-%m-%d %H:%M:%S")
			else:
				d[column.name] = value

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
	def fetch(self, browser=None, service=True):
		"""
			go and fetch a domain for testing
		"""
		session = self.Session()
		try:
			q=session.query(Task).filter_by(status=PENDING)
		
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

	@classlock
	def crawler_start(self, task_id, name, label, user_agent):
		""" Logs crawler start
		@param task_id
		@param name of the browser	
		@param label of the browser
		@param user_agent
		@return: return row id of the crawler
		"""
		session.self.Session()
		crawler = Crawler(name, label, user_agent)
		try:
			crawler.status = "init"
			session.query(Task).get(task_id).crawler = crawler
			session.commit()
			session.refresh(crawler)
			return crawler.id
		except SQLAlchemyError as e:
			log.debug("Database error logging guest start: {0}".format(e))
			session.rollback()
			return None
		finally:
			session.close()

	@classlock
	def crawler_set_status(self, task_id, status):
		session = self.Session()
		try:
			crawler = session.query(crawler).filter_by(task_id=task_id).first()
			crawler.status = status
			session.commit()
			session.refresh(crawler)
		except SQLAlchemyError as e:
			log.debug("Database error logging crawler start: {0}".format(e))
			session.rollback()
			return None
		finally:
			session.close()

	@classlock
	def crawler_remove(self, crawler_id):
		session = self.Session()
		try:
			crawler = session.query(crawler).get(crawler_id)
			session.delete(crawler)
			session.commit()
		except SQLAlchemyError as e:
			log.debug("Database error logging crawler remove: {0}".format(e))
			session.rollback()
			return None
		finally:
			session.close()

	@classlock
	def crawler_stop(self, crawler_id):
		"""Logs crawler stop.
		@param crawler_id: crawler log entry id
		"""
		session = self.Session()
		try:
			crawler = session.query(crawler).get(crawler_id)
			crawler.status = "stopped"
			crawler.shutdown_on = datetime.datetime.now()
			session.commit()
		except SQLAlchemyError as e:
			log.debug("Database error logging crawler stop: {0}".format(e))
			session.rollback()
		except TypeError:
			log.warning("Data inconsistency in crawlers table detected, it might be a crash leftover. Continue")
			session.rollback()
		finally:
			session.close()

	@classlock
	def list_browsers(self):
		"""Lists virtual browsers.
		@return: list of virtual browsers
		"""
		session = self.Session()
		try:
			if locked:
				browsers = session.query(browser).options(joinedload("tags")).all()
			else:
				browsers = session.query(browser).options(joinedload("tags")).all()
			return browsers
		except SQLAlchemyError as e:
			log.debug("Database error listing browsers: {0}".format(e))
			return []
		finally:
			session.close()

	@classlock
	def count_browsers_available(self):
		"""How many virtual browsers are ready for analysis.
		@return: free virtual browsers count
		"""
		session = self.Session()
		try:
			browsers_count = session.query(browser).count()
			return browsers_count
		except SQLAlchemyError as e:
			log.debug("Database error counting browsers: {0}".format(e))
			return 0
		finally:
			session.close()

	@classlock
	def	add_error(self,	message,	task_id,	action=None):
		"""Add	an	error	related	to	a	task.
		@param	message:	error	message
		@param	task_id:	ID	of	the	related	task
		"""
		session	=	self.Session()
		error	=	Error(message=message,	task_id=task_id,	action=action)
		session.add(error)
		try:
			session.commit()
		except	SQLAlchemyError	as	e:
			log.debug("Database	error	adding	error	log:	{0}".format(e))
			session.rollback()
		finally:
			session.close()

	@classlock
	def add(self, target, package, options, tags,submit_id=None):
		"""Add a task to database.
		@param options: analysis options.
		@param owner: task owner.
		@param browser: selected browser.
		@param tags: optional tags that must be set for browser selection
		@param package: what packages for a broswer do we want to execute
		@param clock: virtual browser clock time
		@return: cursor or None.
		"""
		session = self.Session()

		# Convert empty strings and None values to a valid int
		task = Task(obj.url)
		
		task.target = target
		task.package = package
		task._options = options
		task.owner = owner
		task.browser = browser
		task.submit_id = submit_id

		if tags:
			if isinstance(tags, basestring):
				for tag in tags.split(","):
					if tag.strip():
						task.tags.append(self._get_or_create(
							session, Tag, name=tag.strip()
						))

			if isinstance(tags, (tuple, list)):
				for tag in tags:
					if isinstance(tag, basestring) and tag.strip():
						task.tags.append(self._get_or_create(
							session, Tag, name=tag.strip()
						))

		session.add(task)

		try:
			session.commit()
			task_id = task.id
		except SQLAlchemyError as e:
			log.debug("Database error adding task: {0}".format(e))
			session.rollback()
			return None
		finally:
			session.close()

		return task_id


	#TODO Below this mark we need to clean up these methods, get them
	#in line with the params in the class

	def add_url(self, url, timeout=0, package="", options="", priority=1, custom="", owner="", machine="", platform="", tags=None, memory=False, enforce_timeout=False, clock=None, submit_id=None):
		"""Add a task to database from url.
		@param url: url.
		@param timeout: selected timeout.
		@param options: analysis options.
		@param priority: analysis priority.
		@param custom: custom options.
		@param owner: task owner.
		@param machine: selected machine.
		@param platform: platform.
		@param tags: tags for machine selection
		@param memory: toggle full memory dump.
		@param enforce_timeout: toggle full timeout execution.
		@param clock: virtual machine clock time
		@return: cursor or None.
		"""

		# Convert empty strings and None values to a valid int
		if not timeout:
			timeout = 0
		if not priority:
			priority = 1

		return self.add(URL(url), timeout, package, options, priority, custom, owner, machine, platform, tags, memory, enforce_timeout, clock, "url", submit_id)

	@classlock
	def add_submit(self, tmp_path, submit_type, data):
		session = self.Session()

		submit = Submit(
			tmp_path=tmp_path, submit_type=submit_type, data=data or {}
		)
		session.add(submit)
		try:
			session.commit()
			session.refresh(submit)
			submit_id = submit.id
		except SQLAlchemyError as e:
			log.debug("Database error adding submit entry: %s", e)
			session.rollback()
		finally:
			session.close()
		return submit_id

	@classlock
	def view_submit(self, submit_id, tasks=False):
		session = self.Session()
		try:
			q = session.query(Submit)
			if tasks:
				q = q.options(joinedload("tasks"))
			submit = q.get(submit_id)
		except SQLAlchemyError as e:
			log.debug("Database error viewing submit: %s", e)
			return
		finally:
			session.close()
		return submit


	def list_tasks(self, limit=None, details=True, category=None, owner=None,
				   offset=None, status=None, sample_id=None, not_status=None,
				   completed_after=None, order_by=None):
		"""Retrieve list of task.
		@param limit: specify a limit of entries.
		@param details: if details about must be included
		@param category: filter by category
		@param owner: task owner
		@param offset: list offset
		@param status: filter by task status
		@param sample_id: filter tasks for a sample
		@param not_status: exclude this task status from filter
		@param completed_after: only list tasks completed after this timestamp
		@param order_by: definition which field to sort by
		@return: list of tasks.
		"""
		session = self.Session()
		try:
			search = session.query(Task)

			if status:
				search = search.filter_by(status=status)
			if not_status:
				search = search.filter(Task.status != not_status)
			if category:
				search = search.filter_by(category=category)
			if owner:
				search = search.filter_by(owner=owner)
			if details:
				search = search.options(joinedload("guest"), joinedload("errors"), joinedload("tags"))
			if sample_id is not None:
				search = search.filter_by(sample_id=sample_id)
			if completed_after:
				search = search.filter(Task.completed_on > completed_after)

			if order_by is not None:
				search = search.order_by(order_by)
			else:
				search = search.order_by(Task.added_on.desc())

			tasks = search.limit(limit).offset(offset).all()
			return tasks
		except SQLAlchemyError as e:
			log.debug("Database error listing tasks: {0}".format(e))
			return []
		finally:
			session.close()

	def minmax_tasks(self):
		"""Find tasks minimum and maximum
		@return: unix timestamps of minimum and maximum
		"""
		session = self.Session()
		try:
			_min = session.query(func.min(Task.started_on).label("min")).first()
			_max = session.query(func.max(Task.completed_on).label("max")).first()

			if not isinstance(_min, DateTime) or not isinstance(_max, DateTime):
				return

			return int(_min[0].strftime("%s")), int(_max[0].strftime("%s"))
		except SQLAlchemyError as e:
			log.debug("Database error counting tasks: {0}".format(e))
			return
		finally:
			session.close()

	@classlock
	def count_tasks(self, status=None):
		"""Count tasks in the database
		@param status: apply a filter according to the task status
		@return: number of tasks found
		"""
		session = self.Session()
		try:
			if status:
				tasks_count = session.query(Task).filter_by(status=status).count()
			else:
				tasks_count = session.query(Task).count()
			return tasks_count
		except SQLAlchemyError as e:
			log.debug("Database error counting tasks: {0}".format(e))
			return 0
		finally:
			session.close()

	@classlock
	def view_task(self, task_id, details=True):
		"""Retrieve information on a task.
		@param task_id: ID of the task to query.
		@return: details on the task.
		"""
		session = self.Session()
		try:
			if details:
				task = session.query(Task).options(
					joinedload("guest"),
					joinedload("errors"),
					joinedload("tags")
				).get(task_id)
			else:
				task = session.query(Task).get(task_id)
		except SQLAlchemyError as e:
			log.debug("Database error viewing task: {0}".format(e))
			return None
		else:
			if task:
				session.expunge(task)
			return task
		finally:
			session.close()

	@classlock
	def view_tasks(self, task_ids):
		"""Retrieve information on a task.
		@param task_id: ID of the task to query.
		@return: details on the task.
		"""
		session = self.Session()
		try:
			tasks = session.query(Task).options(
				joinedload("guest"),
				joinedload("errors"),
				joinedload("tags")
			).filter(Task.id.in_(task_ids)).order_by(Task.id).all()
		except SQLAlchemyError as e:
			log.debug("Database error viewing tasks: {0}".format(e))
			return []
		else:
			for task in tasks:
				session.expunge(task)
			return tasks
		finally:
			session.close()

	@classlock
	def delete_task(self, task_id):
		"""Delete information on a task.
		@param task_id: ID of the task to query.
		@return: operation status.
		"""
		session = self.Session()
		try:
			task = session.query(Task).get(task_id)
			session.delete(task)
			session.commit()
		except SQLAlchemyError as e:
			log.debug("Database error deleting task: {0}".format(e))
			session.rollback()
			return False
		finally:
			session.close()
		return True

	@classlock
	def view_sample(self, sample_id):
		"""Retrieve information on a sample given a sample id.
		@param sample_id: ID of the sample to query.
		@return: details on the sample used in sample: sample_id.
		"""
		session = self.Session()
		try:
			sample = session.query(Sample).get(sample_id)
		except AttributeError:
			return None
		except SQLAlchemyError as e:
			log.debug("Database error viewing task: {0}".format(e))
			return None
		else:
			if sample:
				session.expunge(sample)
		finally:
			session.close()

		return sample

	@classlock
	def find_sample(self, md5=None, sha256=None):
		"""Search samples by MD5.
		@param md5: md5 string
		@return: matches list
		"""
		session = self.Session()
		try:
			if md5:
				sample = session.query(Sample).filter_by(md5=md5).first()
			elif sha256:
				sample = session.query(Sample).filter_by(sha256=sha256).first()
		except SQLAlchemyError as e:
			log.debug("Database error searching sample: {0}".format(e))
			return None
		else:
			if sample:
				session.expunge(sample)
		finally:
			session.close()
		return sample

	@classlock
	def count_samples(self):
		"""Counts the amount of samples in the database."""
		session = self.Session()
		try:
			sample_count = session.query(Sample).count()
		except SQLAlchemyError as e:
			log.debug("Database error counting samples: {0}".format(e))
			return 0
		finally:
			session.close()
		return sample_count

	@classlock
	def view_machine(self, name):
		"""Show virtual machine.
		@params name: virtual machine name
		@return: virtual machine's details
		"""
		session = self.Session()
		try:
			machine = session.query(Machine).options(joinedload("tags")).filter_by(name=name).first()
		except SQLAlchemyError as e:
			log.debug("Database error viewing machine: {0}".format(e))
			return None
		else:
			if machine:
				session.expunge(machine)
		finally:
			session.close()
		return machine

	@classlock
	def view_machine_by_label(self, label):
		"""Show virtual machine.
		@params label: virtual machine label
		@return: virtual machine's details
		"""
		session = self.Session()
		try:
			machine = session.query(Machine).options(joinedload("tags")).filter_by(label=label).first()
		except SQLAlchemyError as e:
			log.debug("Database error viewing machine by label: {0}".format(e))
			return None
		else:
			if machine:
				session.expunge(machine)
		finally:
			session.close()
		return machine

	@classlock
	def view_errors(self, task_id):
		"""Get all errors related to a task.
		@param task_id: ID of task associated to the errors
		@return: list of errors.
		"""
		session = self.Session()
		try:
			q = session.query(Error).filter_by(task_id=task_id)
			errors = q.order_by(Error.id).all()
		except SQLAlchemyError as e:
			log.debug("Database error viewing errors: {0}".format(e))
			return []
		finally:
			session.close()
		return errors

	def processing_get_task(self, instance):
		"""Get an available task for processing."""
		session = self.Session()

		# TODO We can get rid of the `processing` column once again by
		# introducing a "reporting" status, but this requires annoying
		# database migrations, so leaving that for another day.

		try:
			# Fetch a task that has yet to be processed and make sure no other
			# threads are allowed to access it through "for update".
			q = session.query(Task).filter_by(status=TASK_COMPLETED)
			q = q.filter_by(processing=None)
			q = q.order_by(Task.priority.desc(), Task.id)
			task = q.with_for_update().first()

			# There's nothing to process in the first place.
			if not task:
				return

			# Update the task so that it is processed by this instance.
			session.query(Task).filter_by(id=task.id).update({
				"processing": instance,
			})

			session.commit()
			session.refresh(task)

			# Only return the task if it was really assigned to this node. It
			# could be, e.g., in sqlite3, that the locking is misbehaving.
			if task.processing == instance:
				return task.id
		except SQLAlchemyError as e:
			log.debug("Database error getting new processing tasks: %s", e)
		finally:
			session.close()
