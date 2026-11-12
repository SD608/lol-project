#!/usr/bin/env python3
"""Start PICKOU's local API and web UI together; open both in the browser."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
STATE = ROOT / '.pickou'


def available(port):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def prepare(skip=False):
    node = shutil.which('node')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not node or not npm:
        raise RuntimeError('Install Node.js LTS (including npm), then double-click the launcher again.')
    environment = ROOT / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if skip:
        python = Path(os.environ.get('PICKOU_PYTHON', str(python)))
        if not python.is_file():
            raise RuntimeError('Python environment missing; run again without --no-setup.')
        if not (ROOT / 'frontend/node_modules/next/dist/bin/next').is_file():
            raise RuntimeError('Frontend dependencies missing; run again without --no-setup.')
        return str(python), node
    if not python.is_file():
        print('Creating local Python environment...', flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    for name, path, command in (
        ('backend', ROOT / 'backend/requirements.txt', [str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'backend/requirements.txt')]),
        ('frontend', ROOT / 'frontend/package-lock.json', [npm, 'ci', '--no-audit', '--no-fund']),
    ):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        stamp = STATE / (name + '.sha256')
        installed = (environment / 'pyvenv.cfg').exists() if name == 'backend' else (ROOT / 'frontend/node_modules/next/dist/bin/next').exists()
        if not installed or not stamp.exists() or stamp.read_text() != digest:
            print(f'Installing {name} dependencies (first launch or dependency change)...', flush=True)
            subprocess.run(command, cwd=ROOT / 'frontend' if name == 'frontend' else ROOT, check=True, shell=os.name == 'nt')
            stamp.write_text(digest)
    return str(python), node


def wait_ready(url, processes, timeout=120):
    # Local readiness requests must never send data through an outbound proxy.
    opener = build_opener(ProxyHandler({}))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(process.poll() is not None for process in processes):
            raise RuntimeError('A server exited. See .pickou/logs for details.')
        try:
            with opener.open(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            pass
        time.sleep(.4)
    raise RuntimeError('Server startup timed out. See .pickou/logs for details.')


def stop(processes):
    for process in reversed(processes):
        if os.name == 'nt':
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
    for process in processes:
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            if os.name != 'nt':
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.wait(timeout=5)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-open', action='store_true')
    parser.add_argument('--no-setup', action='store_true', help='Use already installed dependencies')
    parser.add_argument('--backend-port', type=int, default=8000)
    parser.add_argument('--frontend-port', type=int, default=3000)
    args = parser.parse_args()
    processes = []; logs = []
    try:
        ports = (args.backend_port, args.frontend_port)
        if len(set(ports)) != 2 or any(not 1024 <= p <= 65535 for p in ports):
            raise RuntimeError('Choose two different ports between 1024 and 65535.')
        for port in ports:
            if not available(port):
                raise RuntimeError(f'Port {port} is already in use. Close the existing server, or choose another port. No existing process was stopped.')
        STATE.mkdir(exist_ok=True)
        python, node = prepare(args.no_setup)
        api = f'http://127.0.0.1:{args.backend_port}'
        web = f'http://127.0.0.1:{args.frontend_port}'
        commands = [
            [python, '-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', str(args.backend_port)],
            [node, str(ROOT / 'frontend/node_modules/next/dist/bin/next'), 'dev', str(ROOT / 'frontend'), '--hostname', '127.0.0.1', '--port', str(args.frontend_port)],
        ]
        directory = STATE / 'logs'; directory.mkdir(exist_ok=True)
        env = {**os.environ, 'PICKOU_API_ORIGIN': api, 'NEXT_TELEMETRY_DISABLED': '1'}
        for name, command in zip(('backend', 'frontend'), commands):
            log = (directory / (name + '.log')).open('w', encoding='utf-8'); logs.append(log)
            options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
            processes.append(subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, **options))
        # Next must run from its app directory; passing it explicitly avoids cwd assumptions.
        wait_ready(api + '/api/counter-guide/metadata', processes)
        wait_ready(web, processes)
        print(f'PICKOU: {web}\nBackend API: {api}/docs\nPress Ctrl+C here to stop both servers. Logs: {directory}', flush=True)
        if not args.no_open:
            webbrowser.open(api + '/docs')
            webbrowser.open(web)
        while all(process.poll() is None for process in processes):
            time.sleep(.5)
        raise RuntimeError('A server stopped. See .pickou/logs for details.')
    except KeyboardInterrupt:
        print('\nStopping PICKOU...', flush=True)
        return 0
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f'PICKOU could not start: {error}', file=sys.stderr)
        return 1
    finally:
        stop(processes)
        for log in logs:
            log.close()


if __name__ == '__main__':
    sys.exit(main())
