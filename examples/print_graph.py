
from webstar import Router

class LEAF(object):
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return '<%s>' % self.name


root = Router()

blog = root.register('/blog', Router())
blog.register('/archive/{year:\d+}/{month:\d+}', LEAF('archive for month'), year=None)
blog.register('/archive', LEAF('archive root'), name='archive root')


root.print_graph()
print root.url_for(name='archive root')
print root.url_for(year='2010', month='04')