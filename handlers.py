import datetime
import json
import logging
import time
import traceback
import webapp2

from functools import wraps
from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import ndb


ERRORS_KEY = 'errors'


def rate_limit(seconds_per_request=1):
    def rate_limiter(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            added = memcache.add(
                '%s:%s' % (self.__class__.__name__, self.request.remote_addr or ''), 1,
                time=seconds_per_request, namespace='rate_limiting')
            if not added:
                self.response.write('Rate limit exceeded.')
                self.response.set_status(403)
                return
            return function(self, *args, **kwargs)
        return wrapper
    return rate_limiter


def json_handler(obj):
    if isinstance(obj, datetime.datetime):
        return to_timestamp(obj)
    elif isinstance(obj, ndb.Model):
        return obj.to_dict()
    else:
        raise TypeError("%r is not JSON serializable" % obj)


def to_timestamp(dt):
    return int(time.mktime(dt.timetuple()))


def to_json(value):
    return json.dumps(value, default=json_handler)


def ajax_request(function):
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        try:
            output = function(self, *args, **kwargs)
        except Exception as e:
            logging.error(traceback.format_exc())
            output = {ERRORS_KEY: 'Unexpected exception! %s: %s' % (e.__class__.__name__, e)}
        data = to_json(output)
        self.response.content_type = 'application/json'
        self.response.write(data)
    return wrapper


class WarmupHandler(webapp2.RequestHandler):
    @rate_limit(seconds_per_request=10)
    def get(self):
        self.response.write('Warmed up!')


class AjaxSendMailHandler(webapp2.RequestHandler):
    @rate_limit(seconds_per_request=5)
    @ajax_request
    def post(self):
        name = self.request.POST.get('name', '').strip()
        if not name:
            return {ERRORS_KEY: 'What\'s your name...'}

        email = self.request.POST.get('email', '').strip()
        if not email:
            return {ERRORS_KEY: 'What\'s your email address...'}
        elif not mail.is_email_valid(email):
            return {ERRORS_KEY: 'Hmmm. That doesn\'t look like a valid email address...'}

        body = self.request.POST.get('body', '').strip()
        if not body:
            return {ERRORS_KEY: 'What\'s your message...'}

        spacer = '*' * 75
        subject = 'A message from your %s' % name
        body = ('Hi Sophia!\n\nYou\'ve received the following message:\n\n%s\n\n%s\n\n%s' +
                '\n\nReply to %s via %s') % (spacer, body, spacer, name, email)

        try:
            mail.send_mail('Your Jewelry Site <0x24a537r9@gmail.com>', '0x24a537r9@gmail.com',
                           subject, body)
        except:
            return {ERRORS_KEY: 'Oops! I didn\'t get your message. Please contact me directly at ' +
                                'sophiahasegawa@gmail.com.'}

        return {}
