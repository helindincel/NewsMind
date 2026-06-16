class HubbException(Exception):
    """Base exception for all HUBB domain errors."""


class ArticleNotFoundException(HubbException):
    pass


class SummaryNotFoundException(HubbException):
    pass


class InvalidKeywordException(HubbException):
    pass


class NewsProviderException(HubbException):
    pass


class SummarizationException(HubbException):
    pass


class ContentTooShortException(HubbException):
    pass


class CacheException(HubbException):
    pass


class RateLimitExceededException(HubbException):
    pass
