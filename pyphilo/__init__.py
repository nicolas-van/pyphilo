
import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative
import threading
import re

class _Engine:
    def __init__(self):
        self.engine = None
    def __getattr__(self, name):
        if self.engine is None:
            raise Exception("Global engine was not inited")
        return getattr(self.engine, name)
    def init_global_engine(self, *args, **kwargs):
        self.engine = sa.create_engine(*args, **kwargs)
    def init_sqlite(self, file_name, *args, **kwargs):
        self.init_global_engine("sqlite:///" + file_name, *args, **kwargs)

_table_name_re = re.compile("[A-Z]")

def to_table_name(name):
    """
        Transforms a table name into a dabase name.
    """
    name = name[0].lower() + name[1:]
    nname = ""
    last = 0
    for r in _table_name_re.finditer(name):
        nname += name[last:r.start()] + "_" + name[r.start()].lower()
        last = r.start() + 1
    nname += name[last:]
    return nname



"""
A global engine that can be setted at the start of the application
"""
engine = _Engine()

class _Base(object):
    
    @sa.ext.declarative.declared_attr
    def __tablename__(cls):
        return to_table_name(cls.__name__)

    @sa.ext.declarative.declared_attr
    def id(cls):
        return sa.Column(sa.Integer, sa.Sequence(to_table_name(cls.__name__) + "_id_seq"), primary_key=True)

"""
    A default Base class for all entities. Automatically set the name of the database table
    and configure a default auto-incremented id.
"""
Base = sa.ext.declarative.declarative_base(cls=_Base)

def Many2One(class_name, **kwargs):
    """
        A helper to be used with the Base class, useful to specify many2one without having
        to specify the key table.
    """
    return sa.Column(sa.Integer, sa.ForeignKey(to_table_name(class_name) + ".id"), **kwargs)

_local_test = threading.local()

class _ThreadSession:
    def __init__(self, session_class):
        self._session_class = sa.orm.scoped_session(session_class)
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
session = _ThreadSession(sa.orm.sessionmaker(bind=engine))

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
    """
        Drop all the tables of the databe.
    """
    Base.metadata.drop_all(engine)

