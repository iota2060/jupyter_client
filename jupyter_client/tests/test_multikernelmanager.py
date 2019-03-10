"""Tests for the notebook kernel and session manager."""

import os
import time
import threading
import multiprocessing as mp

from subprocess import PIPE
from unittest import TestCase
from tornado.testing import AsyncTestCase, gen_test, gen

from traitlets.config.loader import Config
from ..localinterfaces import localhost
from jupyter_client import KernelManager, AsyncKernelManager
from jupyter_client.multikernelmanager import MultiKernelManager, AsyncMultiKernelManager
from .utils import skip_win32
from ..localinterfaces import localhost

TIMEOUT = 30


class TestKernelManager(TestCase):

    def _get_tcp_km(self):
        c = Config()
        km = MultiKernelManager(config=c)
        return km

    def _get_ipc_km(self):
        c = Config()
        c.KernelManager.transport = 'ipc'
        c.KernelManager.ip = 'test'
        km = MultiKernelManager(config=c)
        return km

    def _run_lifecycle(self, km):
        kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
        self.assertTrue(km.is_alive(kid))
        self.assertTrue(kid in km)
        self.assertTrue(kid in km.list_kernel_ids())
        self.assertEqual(len(km),1)
        km.restart_kernel(kid, now=True)
        self.assertTrue(km.is_alive(kid))
        self.assertTrue(kid in km.list_kernel_ids())
        km.interrupt_kernel(kid)
        k = km.get_kernel(kid)
        self.assertTrue(isinstance(k, KernelManager))
        km.shutdown_kernel(kid, now=True)
        self.assertTrue(not kid in km)

    def _run_cinfo(self, km, transport, ip):
        kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
        k = km.get_kernel(kid)
        cinfo = km.get_connection_info(kid)
        self.assertEqual(transport, cinfo['transport'])
        self.assertEqual(ip, cinfo['ip'])
        self.assertTrue('stdin_port' in cinfo)
        self.assertTrue('iopub_port' in cinfo)
        stream = km.connect_iopub(kid)
        stream.close()
        self.assertTrue('shell_port' in cinfo)
        stream = km.connect_shell(kid)
        stream.close()
        self.assertTrue('hb_port' in cinfo)
        stream = km.connect_hb(kid)
        stream.close()
        km.shutdown_kernel(kid, now=True)

    def test_tcp_lifecycle(self):
        km = self._get_tcp_km()
        self._run_lifecycle(km)

    def test_shutdown_all(self):
        km = self._get_tcp_km()
        kid = km.start_kernel(stdout=PIPE, stderr=PIPE)
        self.assertIn(kid, km)
        km.shutdown_all()
        self.assertNotIn(kid, km)
        # shutdown again is okay, because we have no kernels
        km.shutdown_all()

    def test_tcp_cinfo(self):
        km = self._get_tcp_km()
        self._run_cinfo(km, 'tcp', localhost())

    @skip_win32
    def test_ipc_lifecycle(self):
        km = self._get_ipc_km()
        self._run_lifecycle(km)

    @skip_win32
    def test_ipc_cinfo(self):
        km = self._get_ipc_km()
        self._run_cinfo(km, 'ipc', 'test')

    def test_start_sequence_tcp_kernels(self):
        """Ensure that a sequence of kernel startups doesn't break anything."""
        self._run_lifecycle(self._get_tcp_km())
        self._run_lifecycle(self._get_tcp_km())
        self._run_lifecycle(self._get_tcp_km())


    def test_start_sequence_tcp_kernels(self):
        """Ensure that a sequence of kernel startups doesn't break anything."""
        self._run_lifecycle(self._get_ipc_km())
        self._run_lifecycle(self._get_ipc_km())
        self._run_lifecycle(self._get_ipc_km())

    def test_start_parallel_thread_kernels(self):
        self.test_tcp_lifecycle()

        thread = threading.Thread(target=self.test_tcp_lifecycle)
        thread2 = threading.Thread(target=self.test_tcp_lifecycle)
        try:
            thread.start()
            thread2.start()
        finally:
            thread.join()
            thread2.join()

    def test_start_parallel_process_kernels(self):
        self.test_tcp_lifecycle()

        thread = threading.Thread(target=self.test_tcp_lifecycle)
        proc = mp.Process(target=self.test_tcp_lifecycle)

        try:
            thread.start()
            proc.start()
        finally:
            thread.join()
            proc.join()

        assert proc.exitcode == 0


class TestAsyncKernelManager(AsyncTestCase):

    def _get_tcp_km(self):
        c = Config()
        km = AsyncMultiKernelManager(config=c)
        return km

    def _get_ipc_km(self):
        c = Config()
        c.KernelManager.transport = 'ipc'
        c.KernelManager.ip = 'test'
        km = AsyncMultiKernelManager(config=c)
        return km

    @gen.coroutine
    def _run_lifecycle(self, km):
        kid = yield km.start_kernel(stdout=PIPE, stderr=PIPE)
        is_alive = yield km.is_alive(kid)
        self.assertTrue(is_alive)
        self.assertTrue(kid in km)
        self.assertTrue(kid in km.list_kernel_ids())
        self.assertEqual(len(km),1)
        yield km.restart_kernel(kid, now=True)
        is_alive = yield km.is_alive(kid)
        self.assertTrue(is_alive)
        self.assertTrue(kid in km.list_kernel_ids())
        yield km.interrupt_kernel(kid)
        k = km.get_kernel(kid)
        self.assertTrue(isinstance(k, KernelManager))
        yield km.shutdown_kernel(kid, now=True)
        self.assertNotIn(kid, km)

    @gen.coroutine
    def _run_cinfo(self, km, transport, ip):
        kid = yield km.start_kernel(stdout=PIPE, stderr=PIPE)
        k = km.get_kernel(kid)
        cinfo = km.get_connection_info(kid)
        self.assertEqual(transport, cinfo['transport'])
        self.assertEqual(ip, cinfo['ip'])
        self.assertTrue('stdin_port' in cinfo)
        self.assertTrue('iopub_port' in cinfo)
        stream = km.connect_iopub(kid)
        stream.close()
        self.assertTrue('shell_port' in cinfo)
        stream = km.connect_shell(kid)
        stream.close()
        self.assertTrue('hb_port' in cinfo)
        stream = km.connect_hb(kid)
        stream.close()
        yield km.shutdown_kernel(kid, now=True)
        self.assertNotIn(kid, km)

    @gen_test
    def test_tcp_lifecycle(self):
        km = self._get_tcp_km()
        yield self._run_lifecycle(km)

    @gen_test
    def test_shutdown_all(self):
        km = self._get_tcp_km()
        kid = yield km.start_kernel(stdout=PIPE, stderr=PIPE)
        self.assertIn(kid, km)
        yield km.shutdown_all()
        self.assertNotIn(kid, km)
        # shutdown again is okay, because we have no kernels
        yield km.shutdown_all()

    @gen_test
    def test_tcp_cinfo(self):
        km = self._get_tcp_km()
        yield self._run_cinfo(km, 'tcp', localhost())

    @skip_win32
    @gen_test
    def test_ipc_lifecycle(self):
        km = self._get_ipc_km()
        yield self._run_lifecycle(km)

    @skip_win32
    @gen_test
    def test_ipc_cinfo(self):
        km = self._get_ipc_km()
        yield self._run_cinfo(km, 'ipc', 'test')
