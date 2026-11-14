"""Local test protocol peer. No model/account/network/scientific authority."""
import argparse
import json
import os
from pathlib import Path
import signal
import sys


def write(path, value):
    temporary = path.with_name(path.name + '.tmp-' + str(os.getpid()))
    temporary.write_text(json.dumps(value), encoding='utf-8')
    os.replace(temporary, path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--control', type=Path, required=True)
    options = parser.parse_args()
    directory = options.control.resolve()
    settings = json.loads((directory / 'settings.json').read_text())
    child = None
    descendant = False

    def stopping(signum, frame):
        write(directory / ('signal-' + str(os.getpid()) + '.json'),
              {'pid': os.getpid(), 'signal': signum})
        if settings.get('ignore_term') and signum == signal.SIGTERM:
            return
        if child is not None:
            reaped, status = os.waitpid(child, 0)
            write(directory / 'reaped.json', {'pid': reaped, 'exitcode': os.waitstatus_to_exitcode(status)})
        if descendant:
            os._exit(0)
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, stopping)
    if settings.get('descendant'):
        read_ready, write_ready = os.pipe()
        child = os.fork()
        if child == 0:
            os.close(read_ready)
            child = None
            descendant = True
            # Descendant closes inherited protocol pipes, not control evidence.
            os.close(0)
            os.close(1)
            os.write(write_ready, b'R')
            os.close(write_ready)
            while True:
                signal.pause()
        os.close(write_ready)
        assert os.read(read_ready, 1) == b'R'
        os.close(read_ready)
    write(directory / 'ready.json', {'pid': os.getpid(), 'pgid': os.getpgrp(),
                                    'child_pid': child})

    def send(value):
        sys.stdout.write(json.dumps(value, allow_nan=False) + '\n')
        sys.stdout.flush()

    thread, turn = 'controlled-thread', 'controlled-turn'
    for line in sys.stdin:
        request = json.loads(line)
        with (directory / 'received.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(request) + '\n')
        method, params = request.get('method'), request.get('params', {})
        if method == 'initialized':
            write(directory / 'initialized.json', {'received': True})
            continue
        if method == 'initialize':
            write(directory / 'initialize.json', {'received': True})
            if settings.get('hold_initialize'):
                while True:
                    signal.pause()
            result = {}
        elif method == 'thread/start':
            result = {'thread': {'id': thread}, 'model': params['model'],
                      'reasoningEffort': params['config']['model_reasoning_effort']}
        elif method == 'turn/start':
            send({'id': request['id'], 'result': {'turn': {'id': turn}}})
            write(directory / 'turn-started.json', {'received': True})
            if settings.get('hold_turn'):
                while True:
                    signal.pause()
            if settings.get('undeclared_tool'):
                send({'method': 'item/started', 'params': {'threadId': thread,
                    'turnId': turn, 'item': {'id': 'tool', 'type': 'commandExecution'}}})
                continue
            if settings.get('whitespace_delta') is not None:
                send({'method': 'item/started', 'params': {'threadId': thread,
                    'turnId': turn, 'item': {'id': 'answer', 'type': 'agentMessage', 'phase': 'final_answer'}}})
                send({'method': 'item/agentMessage/delta', 'params': {'threadId': thread,
                    'turnId': turn, 'itemId': 'answer', 'delta': settings['whitespace_delta']}})
            send({'method': 'item/completed', 'params': {'threadId': thread,
                'turnId': turn, 'item': {'id': 'answer', 'type': 'agentMessage',
                'phase': 'final_answer', 'text': settings.get('text', '{"controlled":true}')}}})
            status = settings.get('turn_status', 'completed')
            send({'method': 'turn/completed', 'params': {'threadId': thread,
                'turnId': turn, 'turn': {'id': turn, 'status': status,
                'error': None if status == 'completed' else {'message': 'controlled provider failure'}}}})
            continue
        elif method == 'turn/interrupt':
            result = {}
        else:
            raise AssertionError('Unexpected controlled protocol request: ' + str(method))
        send({'id': request['id'], 'result': result})
    # EOF is a real transport shutdown. Normal candidate cleanup uses SIGTERM.
    if child is not None:
        os.kill(child, signal.SIGTERM)
        os.waitpid(child, 0)


if __name__ == '__main__':
    main()
