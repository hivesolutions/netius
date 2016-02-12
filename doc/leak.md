# Memory Leaking

Memory leaking is one of the major issues when creating a service infra-structure. A correct detection of tese
type of problems is important to provide a stable production environment.

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

#### References

* [Tutorial](http://smira.ru/wp-content/uploads/2011/08/heapy.html)
* [Diagnosing Memory "Leaks" in Python](http://python.dzone.com/articles/diagnosing-memory-leaks-python)
* [Circular References in Python](http://engineering.hearsaysocial.com/2013/06/16/circular-references-in-python)
