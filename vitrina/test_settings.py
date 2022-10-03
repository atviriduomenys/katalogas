from vitrina.settings import *

HAYSTACK_CONNECTIONS = {
    'default': env.search_url(var="SEARCH_URL_TEST"),
}
