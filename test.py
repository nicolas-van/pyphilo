
import pyphilo as db
from sqlalchemy import Column, Integer, String, Sequence, Boolean

db.engine.init_sqlite("test.db")

class Article(db.Base):
    name = Column(String(50), nullable=False)
    content  = Column(String(1000), default="This is content", nullable=False)
    published = Column(Boolean(), default=False, nullable=False)

@db.transactionnal
def default_data():
    for i in range(17):
        article = Article(name="Something %d" % i, content="Hello world %d!" % i, published=True)
        db.session.add(article)

created = db.init_db()

if created:
    default_data()

