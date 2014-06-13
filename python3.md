# Python 3

The migration to Python 3 is not easy and as such a compatability layer was created under the name of
[legacy.py](src/netius/base/legacy.py). This file should be the primary source of functionality related
with the compatability between Python 2 and Python 3 and all the code regarding the transition should
be store there and used from there.

## WSGI

WSGI specification is specialy problematic regarding the Python 3 unicode vs bytes problem and a common
specification for how to solve this is still pending, please refer to the links section for more information
regarding problems and solutions for Python 3 and WSGI.

## Links

* [Python3/WSGI](http://wsgi.readthedocs.org/en/latest/python3.html)
* [WSGI 2.0](http://wsgi.readthedocs.org/en/latest/proposals-2.0.html)
