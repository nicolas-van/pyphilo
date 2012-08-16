
import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.ext.declarative 
from sqlalchemy import Column, Integer, String, Sequence, Boolean
from sqlalchemy.orm import relationship
import threading

class Engine:
    def __init__(self):
        self.engine = None
    def __getattr__(self, name):
        if self.engine is None:
            raise Exception("Global engine was not inited")
        return getattr(self.engine, name)
    def init_global_engine(self, *args, **kwargs):
        self.engine = sqlalchemy.create_engine(*args, **kwargs)
    def init_sqlite(self, file_name, *args, **kwargs):
        self.init_global_engine("sqlite:///" + file_name, *args, **kwargs)


"""
A global engine that can be setted at the start of the application
"""
engine = Engine()

class Base(object):
    
    @sqlalchemy.ext.declarative.declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @sqlalchemy.ext.declarative.declared_attr
    def id(cls):
        return Column(Integer, Sequence(cls.__name__.lower() + "_id_seq"), primary_key=True)

"""
    A default Base class for all entities. Automatically set the name of the database table
    and configure a default auto-incremented id.
"""
Base = sqlalchemy.ext.declarative.declarative_base(cls=Base)

def Many2One(class_name, **kwargs):
    """
        A helper to be used with the Base class, useful to specify many2one without having
        to specify the key table.
    """
    return Column(Integer, sqlalchemy.ForeignKey(class_name.lower() + ".id"), **kwargs)

_local_test = threading.local()

class ThreadSession:
    def __init__(self, session_class):
        self._session_class = sqlalchemy.orm.scoped_session(session_class)
    def __getattr__(self, name):
        if getattr(_local_test, "test", 0) == 0:
            raise Exception("Trying to use the database session outside of a transactionnal context")
        return getattr(self._session_class(), name)
    def ensure_inited(self):
        return self._session_class()
    def remove(self):
        return self._session_class.remove()


"""
    A thread-binded session. Uses the global engine. Designed to be used
    with the @transactionnal decorator.
"""
session = ThreadSession(sqlalchemy.orm.sessionmaker(bind=engine))

def transactionnal(fct):
    """
        A function decorator that provides a simple way to manage sessions.
        When the function is called, a thread-binded session is automatically created.
        At the end of the function execution, the transaction is commited. If 
        and exception is thrown, the transaction is rollbacked.
    """
    def wrapping(*args, **kwargs):
        if getattr(_local_test, "test", 0) != 0:
            raise Exception("Multiple usages of @transactionnal")
        _local_test.test = 1
        session.ensure_inited()
        try:
            val = fct(*args, **kwargs)
            session.commit()
            return val
        finally:
            _local_test.test = 0
            session.remove()
    return wrapping

# database initialisation

def init_db():
    """
        Check that the database tables were created and create them if necessary.

        Returns true if the tables were created.
    """
    if len(Base.metadata.tables.keys()) == 0:
        return False
    tname = Base.metadata.tables.keys()[0]
    if not engine.dialect.has_table(engine, tname):
        Base.metadata.create_all(engine) 
        return True
    return False

def drop_db():
    Base.metadata.drop_all(engine)

