# Memory Leaking

Memory leaking is one of the major issues when creating a service infra-structure. A correct detection of tese
type of problems is important to provide a stable production environment.

## Status

The current Python 2.7 implementation leaks memory under normal usage of the netius HTTP client so using a
Python 3.4+ version is recommended for a deployment/production environment to avoid memory leaking.
The leaking of memory under such environments occurs on the native (Python C) codebase so its leaking is
not traceable by tools like guppy.

> In 3.x range doesn't create a list, so the test above won't create 10 million int objects. Even if it did, the int type in 3.x is basically a 2.x long, which doesn't implement a freelist.

## Notes

> Long running Python jobs that consume a lot of memory while running may not
> return that memory to the operating system until the process actually
> terminates, even if everything is garbage collected properly. That was news
> to me, but it's true. What this means is that processes that do need to use
> a lot of memory will exhibit a "high water" behavior, where they remain
> forever at the level of memory usage that they required at their peak.

> Note: this behavior may be Linux specific; there are anecdotal reports that
> Python on Windows does not have this problem.

> This problem arises from the fact that the Python VM does its own internal
> memory management. It's commonly know as memory fragmentation.
> Unfortunately, there doesn't seem to be any fool-proof method of avoiding
> it.

## Utilities

### Heapy

A simple yet powerfull utility that provides a mechanism to detect "pending" object between two pre-defined
snapshot positions (time values) and that allows a powerful memory leak detection mechanism.

#### Example

```python
import guppy
heap = guppy.hpy()
heap.setrelheap()

...

state = heap.heap()
print(state)
```

### References

* [Heapy Tutorial](http://smira.ru/wp-content/uploads/2011/08/heapy.html)
* [Muppy Website](http://pythonhosted.org/Pympler/muppy.html)
* [Diagnosing Memory "Leaks" in Python](http://python.dzone.com/articles/diagnosing-memory-leaks-python)
* [Circular References in Python](http://engineering.hearsaysocial.com/2013/06/16/circular-references-in-python)
* [Memory Usage Presentation (PDF)](https://dmalcolm.fedorapeople.org/presentations/MemoryUsage.pdf)
* [Which Python memory profiler is recommended?](http://stackoverflow.com/questions/110259/which-python-memory-profiler-is-recommended)
