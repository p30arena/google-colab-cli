"""Native Windows SSH regression tests; no Colab allocation."""
import ctypes
import os
import signal
import sys
from unittest.mock import MagicMock

import pytest

from colab_cli.commands import ssh


@pytest.mark.skipif(os.name != 'nt', reason='Windows command-line parser')
@pytest.mark.parametrize('name', ['gpu session', '$(touch /tmp/pwned)', 'a"b', 'a&b'])
def test_native_proxy_arguments(name, monkeypatch):
    monkeypatch.setattr(sys, 'executable', r'C:\Program Files\Python312\python.exe')
    session = MagicMock(name='session')
    session.name = name
    command = ssh._proxy_command(session, r'C:\keys with spaces\id_ed25519')
    parser = ctypes.windll.shell32.CommandLineToArgvW
    parser.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    parser.restype = ctypes.POINTER(ctypes.c_wchar_p)
    count = ctypes.c_int()
    args = parser(command, ctypes.byref(count))
    try:
        parsed = [args[i] for i in range(count.value)]
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(args, ctypes.c_void_p))
    assert parsed == [sys.executable, '-m', 'colab_cli.cli', 'ssh', '--proxy-mode', '-s', name, '--identity', r'C:\keys with spaces\id_ed25519']


def test_cleanup_without_sighup(monkeypatch):
    monkeypatch.delattr(signal, 'SIGHUP', raising=False)
    installed = []
    monkeypatch.setattr(signal, 'signal', lambda sig, callback: installed.append(sig))
    ssh._install_rm_signal_handlers(lambda: None)
    assert signal.SIGTERM in installed
    assert signal.SIGINT in installed


def test_platform_null_device():
    assert f'UserKnownHostsFile={os.devnull}' in ssh._ssh_base_args('proxy', None)

@pytest.mark.skipif(os.name != 'nt', reason='Windows CRT stream modes')
def test_binary_stdio(monkeypatch):
    import msvcrt
    calls = []
    monkeypatch.setattr(msvcrt, 'setmode', lambda fd, mode: calls.append((fd, mode)))
    stdin = MagicMock()
    stdout = MagicMock()
    stdin.buffer.fileno.return_value = 10
    stdout.buffer.fileno.return_value = 11
    monkeypatch.setattr(sys, 'stdin', stdin)
    monkeypatch.setattr(sys, 'stdout', stdout)
    ssh._set_binary_stdio()
    assert calls == [(10, os.O_BINARY), (11, os.O_BINARY)]

@pytest.mark.skipif(os.name != 'nt', reason='Windows CRT stream modes')
def test_binary_stdio_preserves_real_pipe_bytes():
    import subprocess
    payload = bytes(range(256)) * 8
    code = '''
import msvcrt, os, sys
from colab_cli.commands.ssh import _set_binary_stdio
msvcrt.setmode(sys.stdin.fileno(), os.O_TEXT)
msvcrt.setmode(sys.stdout.fileno(), os.O_TEXT)
_set_binary_stdio()
while True:
    data = os.read(sys.stdin.fileno(), 8192)
    if not data:
        break
    sys.stdout.buffer.write(data)
sys.stdout.buffer.flush()
'''
    result = subprocess.run([sys.executable, '-c', code], input=payload, capture_output=True, timeout=30, check=True)
    assert result.stdout == payload
