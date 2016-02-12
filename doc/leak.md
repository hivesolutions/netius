# Memory Leaking

Memory leaking is one of the major issues when creating a service infra-structure. A correct detection of tese
type of problems is important to provide a stable production environment.

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

* [Hapy Tutorial](http://smira.ru/wp-content/uploads/2011/08/heapy.html)
* [Diagnosing Memory "Leaks" in Python](http://python.dzone.com/articles/diagnosing-memory-leaks-python)
* [Circular References in Python](http://engineering.hearsaysocial.com/2013/06/16/circular-references-in-python)
