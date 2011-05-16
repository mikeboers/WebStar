from . import *

@as_request
def __app__(req):
    return Response('I am a leaf')