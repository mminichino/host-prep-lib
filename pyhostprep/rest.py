##
##

import requests
from requests.adapters import HTTPAdapter, Retry
import json
import logging
import base64
import os
import warnings
import inspect
from requests.auth import AuthBase


class APIException(Exception):

    def __init__(self, message, response, code):
        self.code = code
        try:
            self.body = json.loads(response)
        except json.decoder.JSONDecodeError:
            self.body = {'message': response}
        logger = logging.getLogger(self.__class__.__name__)
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        self.message = f"{message} [{function}]({filename}:{line})"
        logger.debug(self.message)
        super().__init__(self.message)


class BasicAuth(AuthBase):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def __call__(self, r):
        auth_hash = f"{self.username}:{self.password}"
        auth_bytes = auth_hash.encode('ascii')
        auth_encoded = base64.b64encode(auth_bytes)
        request_headers = {
            "Authorization": f"Basic {auth_encoded.decode('ascii')}",
        }
        r.headers.update(request_headers)
        return r


class APISession(object):
    HTTP = 0
    HTTPS = 1

    def __init__(self, hostname, username=None, password=None, ssl=0, port=80):
        warnings.filterwarnings("ignore")
        self.username = username
        self.password = password
        self.timeout = 30
        self.logger = logging.getLogger(self.__class__.__name__)
        self.url_prefix = "http://127.0.0.1"
        self.session = requests.Session()
        retries = Retry(total=60,
                        backoff_factor=0.2)
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self._response = None
        self.auth_class = BasicAuth(self.username, self.password)

        if "HTTP_DEBUG_LEVEL" in os.environ:
            import http.client as http_client
            http_client.HTTPConnection.debuglevel = 1
            logging.basicConfig()
            self.debug_level = int(os.environ['HTTP_DEBUG_LEVEL'])
            requests_log = logging.getLogger("requests.packages.urllib3")
            if self.debug_level == 0:
                self.logger.setLevel(logging.DEBUG)
                requests_log.setLevel(logging.DEBUG)
            elif self.debug_level == 1:
                self.logger.setLevel(logging.INFO)
                requests_log.setLevel(logging.INFO)
            elif self.debug_level == 2:
                self.logger.setLevel(logging.ERROR)
                requests_log.setLevel(logging.ERROR)
            else:
                self.logger.setLevel(logging.CRITICAL)
                requests_log.setLevel(logging.CRITICAL)
            requests_log.propagate = True

        if ssl == APISession.HTTP:
            port_num = port if port else 80
            self.url_prefix = f"http://{hostname}:{port_num}"
        else:
            port_num = port if port else 443
            self.url_prefix = f"https://{hostname}:{port_num}"

    def check_status_code(self, code):
        self.logger.debug("API status code {}".format(code))
        if code == 200 or code == 201 or code == 202 or code == 204:
            return True
        elif code == 400:
            raise Exception("Bad Request")
        elif code == 401:
            raise Exception("API: Unauthorized")
        elif code == 403:
            raise Exception("API: Forbidden: Insufficient privileges")
        elif code == 404:
            raise Exception("API: Not Found")
        elif code == 409:
            raise Exception("Conflict")
        elif code == 412:
            raise Exception("Precondition Failed")
        elif code == 415:
            raise Exception("API: invalid body contents")
        elif code == 422:
            raise Exception("API: Request Validation Error")
        elif code == 500:
            raise Exception("API: Server Error")
        elif code == 503:
            raise Exception("API: Operation error code")
        else:
            raise Exception("Unknown API status code {}".format(code))

    def set_timeout(self, timeout: int):
        self.timeout = timeout

    def get_endpoint(self, path):
        return ':'.join(self.url_prefix.split(':')[:-1]) + path

    @property
    def response(self):
        return self._response

    def json(self):
        return json.loads(self._response)

    def dump_json(self, indent=2):
        return json.dumps(self.json(), indent=indent)

    def http_get(self, endpoint, headers=None, verify=False):
        response = self.session.get(self.url_prefix + endpoint, headers=headers, verify=verify)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self

    def http_post(self, endpoint, data=None, headers=None, verify=False):
        response = self.session.post(self.url_prefix + endpoint, data=data, headers=headers, verify=verify)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self

    def api_get(self, endpoint):
        response = self.session.get(self.url_prefix + endpoint, auth=self.auth_class, verify=False, timeout=self.timeout)

        try:
            self.check_status_code(response.status_code)
        except Exception as err:
            raise APIException(err, response.text, response.status_code) from err

        self._response = response.text
        return self

    def api_post(self, endpoint, body):
        response = self.session.post(self.url_prefix + endpoint,
                                     auth=self.auth_class,
                                     json=body,
                                     verify=False,
                                     timeout=self.timeout)

        try:
            self.check_status_code(response.status_code)
        except Exception as err:
            raise APIException(err, response.text, response.status_code) from err

        self._response = response.text
        return self

    def api_put(self, endpoint, body):
        response = self.session.put(self.url_prefix + endpoint,
                                    auth=self.auth_class,
                                    json=body,
                                    verify=False,
                                    timeout=self.timeout)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self

    def api_put_data(self, endpoint, body, content_type):
        headers = {'Content-Type': content_type}

        response = self.session.put(self.url_prefix + endpoint,
                                    auth=self.auth_class,
                                    data=body,
                                    verify=False,
                                    timeout=self.timeout,
                                    headers=headers)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self

    def api_delete(self, endpoint):
        response = self.session.delete(self.url_prefix + endpoint, auth=self.auth_class, verify=False, timeout=self.timeout)

        try:
            self.check_status_code(response.status_code)
        except Exception:
            raise

        self._response = response.text
        return self
