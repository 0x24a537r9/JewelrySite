import webapp2

from handlers import *

app = webapp2.WSGIApplication([
    # AJAX handlers.
    (r'^/x/send-mail/$', AjaxSendMailHandler),
    # AppEngine handlers.
    (r'^/_ah/warmup$', WarmupHandler),
])
