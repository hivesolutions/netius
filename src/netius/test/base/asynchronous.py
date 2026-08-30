#!/usr/bin/python
# -*- coding: utf-8 -*-

# Hive Netius System
# Copyright (c) 2008-2024 Hive Solutions Lda.
#
# This file is part of Hive Netius System.
#
# Hive Netius System is free software: you can redistribute it and/or modify
# it under the terms of the Apache License as published by the Apache
# Foundation, either version 2.0 of the License, or (at your option) any
# later version.
#
# Hive Netius System is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# Apache License for more details.
#
# You should have received a copy of the Apache License along with
# Hive Netius System. If not, see <http://www.apache.org/licenses/>.

__author__ = "João Magalhães <joamag@hive.pt>"
""" The author(s) of the module """

__copyright__ = "Copyright (c) 2008-2024 Hive Solutions Lda."
""" The copyright for the module """

__license__ = "Apache License, Version 2.0"
""" The license for the module """

import unittest

import netius

from netius.base import async_old


class AsynchronousTest(unittest.TestCase):

    def test_basic(self):
        loop = netius.get_loop(asyncio=False)

        self.assertNotEqual(loop, None)
        self.assertEqual(isinstance(loop, netius.Base), True)

        future = netius.build_future(compat=False, asyncio=False)

        self.assertNotEqual(future, None)
        self.assertEqual(isinstance(future, netius.Future), True)
        self.assertNotEqual(future._loop, None)
        self.assertEqual(isinstance(future._loop, netius.Base), True)

        previous = loop
        loop = netius.get_loop(_compat=True)

        self.assertNotEqual(loop, None)

        self.assertEqual(isinstance(loop, netius.BaseLoop), True)
        self.assertEqual(isinstance(loop, netius.CompatLoop), True)
        self.assertEqual(loop, previous._compat)
        self.assertEqual(loop._loop_ref(), previous)

        loop = netius.get_loop(asyncio=True)

        self.assertNotEqual(loop, None)

        if netius.is_asynclib():
            self.assertEqual(isinstance(loop, netius.BaseLoop), True)
            self.assertEqual(isinstance(loop, netius.CompatLoop), True)
        else:
            self.assertEqual(isinstance(loop, netius.Base), True)

    @netius.async_test
    def test_sleep(self):
        for value in netius.sleep(1.0):
            yield value
            future = value
        timeout = future.result()

        self.assertEqual(timeout, 1.0)
        self.assertEqual(isinstance(future, netius.Future), True)
        self.assertEqual(future.done(), True)


class FutureTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.callbacks = []
        self.partials = []

    def test_init(self):
        future = netius.Future()

        # a future starts its life running, with neither a result nor an
        # exception and with no callback of any of the kinds
        self.assertEqual(future.status, 0)
        self.assertEqual(future.running(), True)
        self.assertEqual(future.done(), False)
        self.assertEqual(future.cancelled(), False)
        self.assertEqual(future.finished(), False)
        self.assertEqual(future.result(), None)
        self.assertEqual(future.exception(), None)
        self.assertEqual(future.done_callbacks, [])
        self.assertEqual(future.partial_callbacks, [])
        self.assertEqual(future.ready_callbacks, [])
        self.assertEqual(future.closed_callbacks, [])

    def test_iter(self):
        future = async_old.Future()
        future.set_result("result")

        # a future that is already done is never waited for, so the
        # iteration of it gives no value at all
        self.assertEqual(list(future), [])

        future = async_old.Future()
        future.cancel()

        # neither a future that was canceled nor one that carries an
        # exception is able to give a value back to the caller
        self.assertRaises(netius.RuntimeError, lambda: list(future))

        future = async_old.Future()
        future.set_exception(netius.NetiusError("Invalid"))

        self.assertRaises(netius.NetiusError, lambda: list(future))

    def test_cleanup(self):
        future = netius.Future()
        future.add_done_callback(self._callback)
        future.add_partial_callback(self._callback_partial)
        future.add_ready_callback(self._callback_true)
        future.add_closed_callback(self._callback_true)

        future.cleanup()

        # the clean up drops every one of the callbacks, so that nothing
        # of the future is kept referenced after it
        self.assertEqual(future.done_callbacks, [])
        self.assertEqual(future.partial_callbacks, [])
        self.assertEqual(future.ready_callbacks, [])
        self.assertEqual(future.closed_callbacks, [])

    def test_result(self):
        future = netius.Future()
        future.set_result("result")

        self.assertEqual(future.result(), "result")
        self.assertEqual(future.running(), False)
        self.assertEqual(future.done(), True)
        self.assertEqual(future.finished(), True)

        future = netius.Future()
        future.cancel()

        # a future that was canceled has no result to give back, the
        # asking for one being an error of its own
        self.assertRaises(netius.RuntimeError, future.result)

    def test_exception(self):
        future = netius.Future()
        exception = netius.NetiusError("Invalid")
        future.set_exception(exception)

        self.assertEqual(future.exception(), exception)
        self.assertEqual(future.exception(timeout=1.0), exception)
        self.assertEqual(future.done(), True)

    def test_partial(self):
        future = netius.Future()
        future.add_partial_callback(self._callback_partial)

        future.partial("first")
        future.partial("second")

        # the partial callbacks are kept in place once called, so that
        # every one of the parts is able to reach them
        self.assertEqual(self.partials, [(future, "first"), (future, "second")])

    def test_done_callbacks(self):
        future = netius.Future()
        future.add_done_callback(self._callback)

        # a future that is still running does not reach the callback,
        # which only happens once the result is there
        self.assertEqual(self.callbacks, [])

        future.set_result("result")

        self.assertEqual(self.callbacks, [future])

        # the callbacks are dropped after being called, so that none of
        # them is ever called twice for the same future
        self.assertEqual(future.done_callbacks, [])

        del self.callbacks[:]
        future.add_done_callback(self._callback)

        # one that is added to a future that is already done is called
        # right away, instead of never being reached at all
        self.assertEqual(self.callbacks, [future])

        del self.callbacks[:]
        future = netius.Future()
        future.add_done_callback(self._callback)
        future.remove_done_callback(self._callback)
        future.set_result("result")

        # the one that was removed is no longer called, the future
        # having nothing left to notify
        self.assertEqual(self.callbacks, [])

    def test_partial_callbacks(self):
        future = netius.Future()
        future.add_partial_callback(self._callback_partial)
        future.remove_partial_callback(self._callback_partial)

        future.partial("first")

        self.assertEqual(self.partials, [])

    def test_approve(self):
        future = netius.Future()
        future.approve()

        # the approval of a future is the setting of an empty result on
        # it, so that it is done with no value of its own
        self.assertEqual(future.done(), True)
        self.assertEqual(future.result(), None)

    def test_cancel(self):
        future = netius.Future()

        self.assertEqual(future.cancel(), True)
        self.assertEqual(future.cancelled(), True)
        self.assertEqual(future.done(), True)

        # a future that is no longer running is not canceled a second
        # time, unless the cancel is forced upon it
        self.assertEqual(future.cancel(), False)
        self.assertEqual(future.cancel(force=True), True)

    def test_set_result(self):
        future = netius.Future()
        future.set_result("result")

        # the value of a future that is settled is not replaced, as that
        # would break the promise that was already answered
        self.assertRaises(netius.AssertionError, lambda: future.set_result("other"))

        future.set_result("other", force=True)

        self.assertEqual(future.result(), "other")

    def test_set_exception(self):
        future = netius.Future()
        exception = netius.NetiusError("Invalid")
        future.set_exception(exception)

        self.assertRaises(
            netius.AssertionError, lambda: future.set_exception(exception)
        )

        future.set_exception(exception, force=True)

        self.assertEqual(future.exception(), exception)

    def test_ready(self):
        future = netius.Future()

        # with no callback to say otherwise the future is taken as being
        # ready, as there's nothing holding it back
        self.assertEqual(future.ready, True)

        future.add_ready_callback(self._callback_true)

        self.assertEqual(future.ready, True)

        future.add_ready_callback(self._callback_false)

        # every one of the callbacks has to agree for the future to be
        # ready, a single one of them being enough to hold it
        self.assertEqual(future.ready, False)

        future.remove_ready_callback(self._callback_false)

        self.assertEqual(future.ready, True)

    def test_closed(self):
        future = netius.Future()

        self.assertEqual(future.closed, False)

        future.add_closed_callback(self._callback_false)

        self.assertEqual(future.closed, False)

        future.add_closed_callback(self._callback_true)

        # a single callback that reports the future as closed is enough
        # for it to be considered as such
        self.assertEqual(future.closed, True)

        future.remove_closed_callback(self._callback_true)

        self.assertEqual(future.closed, False)

    def test__wrap(self):
        source = netius.Future()
        source.add_partial_callback(self._callback_partial)
        source.set_result("result")

        target = netius.Future()
        target._wrap(source)

        # the wrapping takes the complete state of the other future, so
        # that the two of them become indistinguishable
        self.assertEqual(target.status, source.status)
        self.assertEqual(target.result(), "result")
        self.assertEqual(target.partial_callbacks, source.partial_callbacks)
        self.assertEqual(target._loop, source._loop)
        self.assertEqual(target._blocking, source._blocking)

    def test__delay(self):
        loop = DelayLoop()
        future = netius.Future(loop=loop)
        future.add_done_callback(self._callback)
        future.set_result("result")

        # with a loop in place the callbacks are not called in line but
        # delayed into it, so that the caller is not held by them
        self.assertEqual(len(loop.delayed), 1)
        self.assertEqual(self.callbacks, [])

        loop.delayed[0][0]()

        self.assertEqual(self.callbacks, [future])

        loop = SoonLoop()
        future = netius.Future(loop=loop)
        future.add_partial_callback(self._callback_partial)
        future.partial("value")

        # a loop that carries no delay of its own is driven through the
        # call soon of the asyncio interface instead
        self.assertEqual(len(loop.soon), 1)
        self.assertEqual(self.partials, [])

        loop.soon[0]()

        self.assertEqual(self.partials, [(future, "value")])

    def test_is_future(self):
        future = netius.Future()

        result = netius.is_future(future)
        self.assertEqual(result, True)

    def test_is_future_native(self):
        try:
            import asyncio
        except:
            asyncio = None

        if not asyncio or not hasattr(asyncio, "isfuture"):
            self.skipTest("No asyncio or asyncio.isfuture() available")

        future = netius.Future()

        result = asyncio.isfuture(future)
        self.assertEqual(result, True)

    def _callback(self, future):
        self.callbacks.append(future)

    def _callback_partial(self, future, value):
        self.partials.append((future, value))

    def _callback_true(self):
        return True

    def _callback_false(self):
        return False


class AsyncOldTest(unittest.TestCase):

    def test_executor(self):
        executor = async_old.Executor()

        # the base executor provides no way of running a callable, the
        # implementation of it being left to the concrete ones
        self.assertRaises(
            netius.NotImplemented, lambda: executor.submit(self._callable)
        )

    def test_thread_pool_executor(self):
        owner = ExecutorOwner()
        executor = async_old.ThreadPoolExecutor(owner)

        future = executor.submit(self._callable, 1, name="value")

        # the callable reaches the owner together with the arguments that
        # it was given, the future being the promise of the result
        self.assertEqual(netius.is_future(future), True)
        self.assertEqual(owner.executed[0][0], self._callable)
        self.assertEqual(owner.executed[0][1], (1,))
        self.assertEqual(owner.executed[0][2], dict(name="value"))

        owner.executed[0][3]("result")
        owner.delayed[0]()

        # the result travels back through the callback, which delays the
        # setting of it into the loop of the owner
        self.assertEqual(future.result(), "result")

    def test_coroutine(self):
        @async_old.coroutine
        def generator():
            yield 1
            yield 2

        # a function that is already a generator one is used as it is,
        # being only marked as a coroutine
        self.assertEqual(async_old.is_coroutine(generator), True)
        self.assertEqual(list(generator()), [1, 2])

        @async_old.coroutine
        def simple():
            return "result"

        # a plain function is wrapped into a generator that yields the
        # single value that it gives back
        self.assertEqual(list(simple()), ["result"])

        @async_old.coroutine
        def with_generator():
            return self._values()

        # a generator that is given back is iterated instead of being
        # yielded, so that its values reach the caller
        self.assertEqual(list(with_generator()), [1, 2])

        future = netius.Future()
        future.set_result("result")

        @async_old.coroutine
        def with_future():
            return future

        # a future that is already done carries no value to be yielded,
        # the iteration of it giving nothing back
        self.assertEqual(list(with_future()), [])

    def test_ensure_generator(self):
        generator = self._values()

        self.assertEqual(async_old.ensure_generator(generator), (True, generator))

        # a value that is not a generator is given back untouched, so
        # that the caller is able to tell the two apart
        self.assertEqual(async_old.ensure_generator("value"), (False, "value"))

    def test_get_asyncio(self):
        # the old implementation targets the interpreters that carry no
        # asyncio, so there's never a module to be given back
        self.assertEqual(async_old.get_asyncio(), None)

    def test_is_coroutine(self):
        self.assertEqual(async_old.is_coroutine(self._callable), False)

        @async_old.coroutine
        def simple():
            return "result"

        # the decoration is what marks a callable as a coroutine, there
        # being no other way of telling one under this implementation
        self.assertEqual(async_old.is_coroutine(simple), True)

    def test_is_coroutine_object(self):
        self.assertEqual(async_old.is_coroutine_object(self._values()), True)
        self.assertEqual(async_old.is_coroutine_object("value"), False)

    def test_is_coroutine_native(self):
        # the old implementation knows nothing about the native
        # coroutines, so no value is ever taken as one of them
        self.assertEqual(async_old.is_coroutine_native(self._values()), False)

    def test_is_future(self):
        self.assertEqual(async_old.is_future(netius.Future()), True)
        self.assertEqual(async_old.is_future(async_old.Future()), True)
        self.assertEqual(async_old.is_future("value"), False)

    def test_is_await(self):
        try:
            compile("async def routine():\n    yield 1", "<test>", "exec")
            supported = True
        except SyntaxError:
            supported = False

        # the asynchronous generator is what the release that the flag
        # stands for adds over the one that introduced the syntax, so the
        # interpreter is asked for it instead of the flag being trusted
        self.assertEqual(async_old.is_await(), supported)

        # the three flags are thresholds of the very same interpreter and
        # follow one another, so the newest of them is never the one that
        # is set while one that came before it is not
        self.assertEqual(async_old.is_await() and not async_old.is_asynclib(), False)
        self.assertEqual(async_old.is_asynclib() and not async_old.is_neo(), False)

    @netius.async_test
    def test_sleep(self):
        for value in async_old.sleep(1.0):
            yield value
            future = value
        timeout = future.result()

        self.assertEqual(timeout, 1.0)
        self.assertEqual(isinstance(future, netius.Future), True)
        self.assertEqual(future.done(), True)

    def test_coroutine_return(self):
        def values():
            yield None
            yield "first"
            yield None
            yield "second"

        # the values that carry nothing are skipped, only the ones that
        # hold something reaching the caller
        self.assertEqual(
            list(async_old.coroutine_return(values())), ["first", "second"]
        )

    def _callable(self, *args, **kwargs):
        return "result"

    def _values(self):
        yield 1
        yield 2


class AsyncNeoTest(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        if not netius.is_neo():
            self.skipTest("Skipping test: async/await unavailable")

        from netius.base import async_neo

        self.async_neo = async_neo

    def test_future_iter(self):
        future = netius.Future()
        future.set_result("result")

        # the neo future carries the result through the return of the
        # iteration, which is what the await syntax reads from it
        self.assertEqual(self._exhaust(iter(future)), "result")

        future = netius.Future()
        future.cancel()

        self.assertRaises(netius.RuntimeError, lambda: list(future))

        future = netius.Future()
        future.set_exception(netius.NetiusError("Invalid"))

        self.assertRaises(netius.NetiusError, lambda: list(future))

    def test_future_await(self):
        future = netius.Future()
        future.set_result("result")

        self.assertEqual(self._exhaust(future.__await__()), "result")

        future = netius.Future()
        future.cancel()

        self.assertRaises(
            netius.RuntimeError, lambda: self._exhaust(future.__await__())
        )

    def test_await_wrapper(self):
        wrapper = self.async_neo.AwaitWrapper(self._values())

        # a wrapper over a generator is an iterator of its own, giving
        # back the values of the generator that it carries
        self.assertEqual(wrapper.is_generator, True)
        self.assertEqual(next(wrapper), 1)
        self.assertEqual(wrapper.next(), 2)

        wrapper = self.async_neo.AwaitWrapper("value", generate=True)

        # a plain value is turned into a generator of a single element,
        # so that it may be awaited the very same way
        self.assertEqual(wrapper.is_generator, True)
        self.assertEqual(list(wrapper), ["value"])

        wrapper = self.async_neo.AwaitWrapper("value")

        # a value that is not a generator becomes the result of the
        # await, with nothing being yielded on the way to it
        self.assertEqual(wrapper.is_generator, False)
        self.assertEqual(self._exhaust(wrapper.__await__()), "value")

        wrapper = self.async_neo.AwaitWrapper(self._values())

        self.assertEqual(self._exhaust(wrapper.__await__()), None)

    def test_coroutine_wrapper(self):
        wrapper = self.async_neo.CoroutineWrapper(self._values())

        self.assertEqual(next(wrapper), 1)

        wrapper.restore("restored")

        # a value that is restored is the next one to be given back,
        # coming before the ones that the coroutine still holds
        self.assertEqual(wrapper.next(), "restored")
        self.assertEqual(next(wrapper), 2)

    def test_coroutine(self):
        @self.async_neo.coroutine
        def generator():
            yield 1
            yield 2

        # a function that is already a generator one keeps its values,
        # the wrapper only making it awaitable
        self.assertEqual(self.async_neo.is_coroutine(generator), True)
        self.assertEqual(list(generator()), [1, 2])

        @self.async_neo.coroutine
        def simple():
            return "result"

        wrapper = simple()

        # a plain function has its value turned into the result of the
        # await, instead of being yielded as an element
        self.assertEqual(isinstance(wrapper, self.async_neo.AwaitWrapper), True)
        self.assertEqual(self._exhaust(wrapper.__await__()), "result")

        future = netius.Future()
        future.set_result("result")

        @self.async_neo.coroutine
        def with_future():
            return future

        # a future that is given back is awaited, so that the result of
        # it becomes the result of the coroutine
        self.assertEqual(self._exhaust(with_future().__await__()), "result")

    def test_ensure_generator(self):
        generator = self._values()

        self.assertEqual(self.async_neo.ensure_generator(generator), (True, generator))
        self.assertEqual(self.async_neo.ensure_generator("value"), (False, "value"))

        coroutine = self._native()

        try:
            is_generator, value = self.async_neo.ensure_generator(coroutine)

            # a native coroutine is wrapped so that it complies with the
            # iterator interface that the infra-structure expects
            self.assertEqual(is_generator, True)
            self.assertEqual(isinstance(value, self.async_neo.CoroutineWrapper), True)
        finally:
            coroutine.close()

    def test_get_asyncio(self):
        import asyncio

        # the neo implementation targets the interpreters that carry
        # asyncio, so the module is the one that is given back
        self.assertEqual(self.async_neo.get_asyncio(), asyncio)

    def test_is_coroutine(self):
        self.assertEqual(self.async_neo.is_coroutine(self._values), False)

        # a function that is declared with the native syntax is a
        # coroutine one, with no decoration being needed for it
        self.assertEqual(self.async_neo.is_coroutine(self._native_function()), True)

    def test_is_coroutine_object(self):
        self.assertEqual(self.async_neo.is_coroutine_object(self._values()), True)
        self.assertEqual(self.async_neo.is_coroutine_object("value"), False)

        coroutine = self._native()

        try:
            self.assertEqual(self.async_neo.is_coroutine_object(coroutine), True)
        finally:
            coroutine.close()

    def test_is_coroutine_native(self):
        # a generator is a coroutine object but not a native one, which
        # is what tells the two kinds apart
        self.assertEqual(self.async_neo.is_coroutine_native(self._values()), False)

        coroutine = self._native()

        try:
            self.assertEqual(self.async_neo.is_coroutine_native(coroutine), True)
        finally:
            coroutine.close()

    def test_is_future(self):
        import asyncio

        self.assertEqual(self.async_neo.is_future(netius.Future()), True)
        self.assertEqual(self.async_neo.is_future("value"), False)

        loop = asyncio.new_event_loop()

        try:
            # a future of asyncio is one as well, so that the two
            # infra-structures are able to share them
            self.assertEqual(self.async_neo.is_future(loop.create_future()), True)
        finally:
            loop.close()

    def test_coroutine_return(self):
        future = netius.Future()
        future.set_result("result")

        wrapper = self.async_neo.coroutine_return(iter([None, future]))

        # the result of the last future that was yielded is the value
        # that the coroutine gives back, the empty ones being skipped
        self.assertEqual(self._exhaust(wrapper.__await__()), "result")

        wrapper = self.async_neo.coroutine_return(iter([]))

        # a coroutine that yields nothing has no future to take the
        # result from, so an invalid value is the one given back
        self.assertEqual(self._exhaust(wrapper.__await__()), None)

    def _exhaust(self, generator):
        # runs the generator until it is exhausted, giving back the value
        # that comes with the stop, which is the result of the await
        try:
            while True:
                next(generator)
        except StopIteration as exception:
            return exception.value

    def _native(self):
        return self._native_function()()

    def _native_function(self):
        # builds the coroutine function through a compilation, so that
        # the syntax of it does not reach the oldest of the interpreters
        namespace = dict()
        code = compile("async def routine():\n    return 'result'\n", "<test>", "exec")
        exec(code, namespace)
        return namespace["routine"]

    def _values(self):
        yield 1
        yield 2


class ExecutorOwner(object):
    """
    Stand in for the owner of an executor, keeping both the
    callables that are executed and the ones that are delayed.
    """

    def __init__(self):
        self.executed = []
        self.delayed = []

    def build_future(self):
        return netius.Future()

    def delay_s(self, callable):
        self.delayed.append(callable)

    def texecute(self, callable, args=(), kwargs={}, callback=None):
        self.executed.append((callable, args, kwargs, callback))


class DelayLoop(object):
    """
    Stand in for a loop that carries a delay operation of
    its own, keeping the callables that reach it.
    """

    def __init__(self):
        self.delayed = []

    def delay(self, callable, immediately=False):
        self.delayed.append((callable, immediately))


class SoonLoop(object):
    """
    Stand in for a loop that provides only the call soon
    operation of the asyncio interface.
    """

    def __init__(self):
        self.soon = []

    def call_soon(self, callable):
        self.soon.append(callable)
