##
##

import sys
import os
import inspect
import logging
import json

logger = logging.getLogger('hostprep.exception')
logger.addHandler(logging.NullHandler())


class FatalError(Exception):

    def __init__(self, message):
        import traceback
        logging.debug(traceback.print_exc())
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        logger.debug("Error: {} in {} {} at line {}: {}".format(type(self).__name__, filename, function, line, message))
        logger.error(f"{message} [{filename}:{line}]")
        sys.exit(1)


class NonFatalError(Exception):

    def __init__(self, message):
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        self.message = "Error: {} in {} {} at line {}: {}".format(type(self).__name__, filename, function, line, message)
        logger.debug(f"Exception: {self.message}")
        super().__init__(self.message)


class APIException(Exception):

    def __init__(self, message, response, code):
        self.code = code
        try:
            self.body = json.loads(response)
        except json.decoder.JSONDecodeError:
            self.body = {'message': response}
        frame = inspect.currentframe().f_back
        (filename, line, function, lines, index) = inspect.getframeinfo(frame)
        filename = os.path.basename(filename)
        self.message = f"{message} [{function}]({filename}:{line})"
        logger.debug(self.message)
        super().__init__(self.message)


class APIError(APIException):
    pass


class BadRequest(NonFatalError):
    pass


class NotAuthorized(NonFatalError):
    pass


class HTTPForbidden(NonFatalError):
    pass


class HTTPNotImplemented(NonFatalError):
    pass


class RequestValidationError(NonFatalError):
    pass


class InternalServerError(NonFatalError):
    pass


class PaginationDataNotFound(NonFatalError):
    pass


class SyncGatewayOperationException(NonFatalError):
    pass


class PreconditionFailed(NonFatalError):
    pass


class ConflictException(NonFatalError):
    pass
