#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
	HTTP/Web class.

	Holds commonly-used HTTP/web request/post methods.

	Compatible with Python 2.5, 2.6, 2.7
"""

import time

import urllib2, cookielib, urllib, httplib
from sys import stderr

class Httpy:
	"""
		Class used for communicating with web servers.
	"""
	
	def __init__(self, user_agent=None, debugging=False):
		"""
			Sets this class's user agent.
		"""
		self.debugging = debugging
		self.cj      = cookielib.CookieJar()
		self.opener  = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cj))
		self.Request = urllib2.Request
		self.urlopen = self.opener.open
		self.timeout = 20
		
		if user_agent != None:
			self.user_agent = user_agent
		else:
			self.user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.7; rv:19.0) Gecko/20100101 Firefox/19.0'
	
	def raise_timeout(self, signum, frame):
		raise Exception("Timeout")
	
	def get_meta(self, url):
		""" Reads file info (content type, length, etc) without downloading
		    Times out after 10 seconds (5 to unshorten, 5 to get meta) """
		url = self.unshorten(url)
		try:
			headers = {'User-agent' : self.user_agent}
			req = urllib2.Request(url, headers=headers)
			site = self.urlopen(req, timeout=self.timeout)
			#site = self.urlopen(url)
		except Exception:
			return {'content-type': 'unknown', 'content-length': '0'}
		return site.info()
	
	def unshorten(self, url):
		""" Unshortens URL. Follows until no more redirects. Times out after 5 seconds """
		try:
			headers = {'User-agent' : self.user_agent}
			req = urllib2.Request(url, headers=headers)
			site = self.urlopen(req, timeout=self.timeout)
		except urllib2.HTTPError:
			return url
		except Exception:
			return url
		return site.url

	def check(self, url):
		""" Check if a URL is valid """
		try:
			self.urlopen(url, timeout=self.timeout)
		except:
			return False
		return True
	
	def get(self, url, headers={}):
		"""
			Attempts GET request with web server.
			
			Returns html source of a webpage (string).
			Returns '' if unable to retrieve webpage for any reason.
			
			Will attempt to repeatedly post if '504' response error is received
			or 'getaddrinfo' fails.
		"""
		if not 'User-agent' in headers:
			headers['User-agent'] = self.user_agent
		
		try:
			req = urllib2.Request(url, headers=headers)
			handle = self.urlopen(req, timeout=self.timeout)
			
		except Exception, e:
			if self.debugging: stderr.write('Httpy: Exception while creating request: %s\n' % str(e))
			raise e

		try:
			result = handle.read()
		except Exception, e:
			if self.debugging: stderr.write('Httpy: Exception while reading response: %s\n' % str(e))
			raise e
		
		return result

	def getter(self, url, headers={}, retry=1):
		"""
			Attempts GET request with extended options.
			
			Returns html source of a webpage (string).
			Returns '' if unable to retrieve webpage for any reason.
			
			Will retry attempts that fail.

			Does *NOT* utilize cookie jar!
		"""
		if not 'User-agent' in headers:
			headers['User-agent'] = self.user_agent
		
		(https, host, path) = self.get_https_host_path(url)
		if self.debugging: stderr.write('Httpy.py: GET http%s://%s%s\n' % ('s' if https else '', host, path))
		try:
			if https:
				req = httplib.HTTPSConnection(host)
			else:
				req = httplib.HTTPConnection(host)
			req.putrequest('GET', path)
			if self.debugging: stderr.write('Httpy.py: headers:\n')
			for hkey in headers.keys():
				if self.debugging: stderr.write('        %s:\t%s\n' % (hkey, headers[hkey]))
				req.putheader(hkey, headers[hkey])
			req.endheaders()
			resp = req.getresponse()
			if self.debugging: stderr.write('Httpy.py: response headers:')
			for h,v in resp.getheaders():
				if self.debugging: stderr.write('        %s: "%s"\n' % (h, v))
			if resp.status == 200:
				return resp.read()
			elif resp.status in [301, 302] and resp.getheader('Location') != None:
				if self.debugging: stderr.write('Httpy.py: Got %d to %s' % (resp.status, resp.getheader('Location')))
				return self.getter(resp.getheader('Location'), headers=headers, retry=retry-1)
			else:
				result = ''
				try: result = resp.read()
				except: pass
				if self.debugging: stderr.write('Httpy.py: HTTP status %s: %s\n' % (resp.status, resp.reason))
				return result
		except Exception, e:
			if self.debugging: stderr.write('Httpy.py: Exception: %s: %s\n' % (url, str(e)))
			if retry > 0:
				return self.getter(url, headers=headers, retry=retry-1)
		return ''
	
	def get_https_host_path(self, url):
		https  = url.startswith('https')
		path   = ''
		host   = url[url.find('//')+2:]
		if '/' in host:
			host = host[:host.find('/')]
			path = url[url.find(host)+len(host):]
		return (https, host, path)
	
	def fix_string(self, s):
		r = ''
		for c in s:
			c2 = ''
			try:
				c2 = str(c)
			except UnicodeEncodeError:
				c2 = ''
			r += c2
		return r
	
	def fix_dict(self, dict):
		d = {}
		
		for key in dict:
			value = dict[key]
			d[key] = self.fix_string(value)
		return d
		
	def oldpost(self, url, postdict=None, headers={}):
		""" 
			Submits a POST request to URL. Posts 'postdict' if
			not None. URL-encodes postdata (if dict) 
			and strips Unicode chars.
		"""
		result = ''
		if not 'User-agent' in headers:
			headers['User-agent'] = self.user_agent
		if postdict == None:
			encoded_data = ''
		elif type(postdict) == dict:
			encoded_data = urllib.urlencode(postdict)
		elif type(postdict) == str:
			encoded_data = postdict
		try:
			req = self.Request(url, encoded_data, headers)
			handle = self.urlopen(req, timeout=self.timeout)
			result = handle.read()
		except Exception, e:
			if self.debugging: stderr.write('Httpy.py: Exception: %s: %s\n' % (url, str(e)))
		return result
		
	def post(self, url, postdict=None, headers={}):
		"""
			Attempts POST request with web server.
			
			Returns response of a POST request to a web server.
			'postdict' must be a dictionary of keys/values to post to the server.
			Returns '' if unable to post/retrieve response.
			
			Will attempt to repeatedly post if '504' response error is received
			or 'getaddrinfo' fails.
		"""
		if not 'User-agent' in headers:
			headers['User-agent'] = self.user_agent
		data = ''
		if postdict != None and type(postdict) == dict:
			fixed_dict = self.fix_dict(postdict)
			data = urllib.urlencode(fixed_dict)
		elif postdict != None and type(postdict) == str:
			data = postdict
		headers['Content-Length'] = len(data)
		
		host = url[url.find('//')+2:]
		host = host[:host.find('/')]
		if self.debugging: stderr.write('Httpy.py: host: "%s"\n' % host)
		path = url[url.find(host)+len(host):]
		if self.debugging: stderr.write('Httpy.py: path: "%s"\n' % path)
		if self.debugging: stderr.write('Httpy.py: headers: %s\n' % str(headers))
		if self.debugging: stderr.write('Httpy.py: postdata: "%s"\n' % data)
		try:
			if url.startswith('https'):
				req = httplib.HTTPSConnection(host)
			else:
				req = httplib.HTTPConnection(host)
			req.putrequest('POST', path)
			for hkey in headers.keys():
				req.putheader(hkey, headers[hkey])
			req.endheaders()
			req.send(data)
			resp = req.getresponse()
			if resp.status == 200:
				return resp.read()
			else:
				if self.debugging: stderr.write('Httpy.py: HTTP status %s: %s: %s\n' % (resp.status, resp.reason, resp.read()))
				if self.debugging: stderr.write('Httpy.py: Response headers:\n')
				for name, value in resp.getheaders():
					if self.debugging: stderr.write('Httpy.py: \t"%s"="%s"\n' % (name, value))
				return ''
		except Exception, e:
			if self.debugging: stderr.write('Httpy.py: Exception: %s: %s\n' % (url, str(e)))
			return ''
	
	def download(self, url, save_as):
		"""
			Downloads a file from 'url' and saves the file locally as 'save_as'.
			Throws exceptions if errors occur
		"""
		output = open(save_as, 'wb')
		
		headers = {'User-agent' : self.user_agent}
		req = urllib2.Request(url, headers=headers)
		file_on_web = self.urlopen(req, timeout=self.timeout)
		while True:
			buf = file_on_web.read(65536)
			if len(buf) == 0:
				break
			output.write(buf)
		output.close()
	
	
	def clear_cookies(self):
		"""
			Clears cookies in cookie jar.
		"""
		self.cj.clear()
	
	
	def set_user_agent(user_agent):
		"""
			Changes the user-agent used when connecting.
		"""
		self.user_agent = user_agent
	
	
	def between(self, source, start, finish):
		"""
			Helper method. Useful when parsing responses from web servers.
			
			Looks through a given source string for all items between two other strings, 
			returns the list of items (or empty list if none are found).
			
			Example:
				test = 'hello >30< test >20< asdf >>10<< sadf>'
				print between(test, '>', '<')
				
			would print the list:
				['30', '20', '>10']
		"""
		result = []
		i = source.find(start)
		j = source.find(finish, i + len(start))
		
		while i >= 0 and j >= 0:
			i = i + len(start)
			result.append(source[i:j])
			i = source.find(start, j + len(finish))
			j = source.find(finish, i + len(start))
		
		return result

