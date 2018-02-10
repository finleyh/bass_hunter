import datetime
import os
import sys

from sqlalchemy import Table, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = declarative_base()

class Domain(Base):
	__tablename__='domains'
	id = Column(Integer, primary_key=True)
	
class Images(Base):
	__tablename__='images'

class API_Users(Base):
	__tablename__='api_users'

#helper tables

class MSE_latest_vs_recent(Base):
	__tablename__='MSE_latest_vs_recent'

class MSE_recent_vs_base(Base):
	__tablename__='MSE_recent_vs_base'
