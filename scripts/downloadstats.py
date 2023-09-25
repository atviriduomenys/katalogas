import resource
import os
import json
import urllib.parse

from tqdm import tqdm

from pathlib import Path
from datetime import datetime

import user_agents
import requests as req

from typer import run, Option
from typer import Argument
from collections import deque

bots = {
    'SemrushBot',
    'BLEXBot',
    'Googlebot',
    'PetalBot',
    'crawler',
    'Googlebot-Image',
    'BingPreview',
    'bingbot',
    'archive.org_bot',
    'DataForSeoBot',
    'Adsbot'
}

transactions = {}
bots_found = {'agents': {}}

def main(
    name: str = Argument(..., help="stats source name, i.e. get.data.gov.lt"),
    logfile: str = Argument(..., help=(
        "log file to read stats from, i.e. accesslog.json"
    )),
    target: str = Option("http://localhost:8000", help=(
        "target server url"
    )),
    config_file: str = Option('/.config/vitrina/downloadstats.json'),
    state_file: str = Option('/.local/share/vitrina/state.json'),
    bot_status_file: str = Option('/.local/share/vitrina/downloadstats.json'),
):
    config_file = os.path.expanduser('~') + config_file
    state_file = os.path.expanduser('~') + state_file
    bot_status_file = os.path.expanduser('~') + bot_status_file
    current_state = {'files': {}}

    limit = 1000
    total_lines_read = 0
    lines_read = 0
    final_stats = {}
    file_size = os.path.getsize(logfile)
    existing_size = 0
    existing_offset = 0

    if not os.path.exists(os.path.dirname(state_file)):
        os.makedirs(os.path.dirname(state_file))
    if not os.path.exists(state_file):
        file = Path(state_file)
        file.touch(exist_ok=True)
        with open(state_file, "w") as outfile:
            outfile.write(json.dumps(current_state, indent=4))
    else:
        with open(state_file, 'r') as f:
            current_state = json.load(f)
        state = current_state.get('files').get(logfile)
        if state is not None:
            existing_size = state.get('size')
            existing_offset = state.get('offset')

    if not os.path.exists(os.path.dirname(bot_status_file)):
        os.makedirs(os.path.dirname(bot_status_file))
    if not os.path.exists(bot_status_file):
        file = Path(bot_status_file)
        file.touch(exist_ok=True)
    else:
        with open(bot_status_file, 'r') as f:
            if os.path.getsize(bot_status_file) > 0:
                bots_found = json.load(f)

    if os.path.exists(config_file):
        with open(config_file, 'r') as config:
            bot_list = json.load(config).get('bots')
            bots.update(bot_list)

    if not os.path.exists(logfile):
        print(f'File {logfile} not found. Aborting.')
        return

    if file_size == existing_size:
        # File did not change?
        return

    endpoint_url = urllib.parse.urljoin(target, 'partner/api/1/downloads')
    session = req.Session()

    total_lines_in_file = 0
    d = deque([], maxlen=limit)

    with open(logfile) as ff:
        total_lines_in_file = sum(bl.count('\n') for bl in blocks(ff))

    pbar = tqdm("Parsing download stats", total=total_lines_in_file)

    with open(logfile) as f:
        bytesread = 0
        if existing_offset > 0:
            f.seek(existing_offset)
        for line in f:
            bytesread += len(str.encode(line))
            d.append(line)
            total_lines_read += 1
            lines_read += 1
            if lines_read == limit:
                find_transactions(name, d, endpoint_url, session, final_stats, bot_status_file)
                lines_read = 0
            state_entry = {
                logfile: {
                    'size': file_size,
                    'offset': bytesread
                }
            }
            pbar.update(1)
        find_transactions(name, d, endpoint_url, session, final_stats, bot_status_file)

    current_state.get('files', {}).update(state_entry)

    with open(state_file, "w") as outfile:
        outfile.write(json.dumps(current_state, indent=4))

    with open(bot_status_file, "w+") as bot_file:
        bot_file.write(json.dumps(bots_found, indent=4))

    print(f'Total lines read: {total_lines_read}')
    print(f'Total model entries found: {len(final_stats.keys())}')
    print(f'Total transaction entries in file: {len(transactions)}')
    print(f'Peak Memory Usage = {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}')


def parse_user_agent(agent):
    if isinstance(agent, str):
        return user_agents.parse(agent).browser.family


def find_transactions(name, d, endpoint_url, session, final_stats, bot_status_file):
    for i in d:
        if 'txn' in i:
            entry = json.loads(i)
            txn = entry['txn']
            timestamp = entry['time']
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
            except:
                print('Wrong timestamp format')
            requests = 1
            if txn not in transactions:
                transactions[txn] = {'time': dt}
            if 'model' in entry:
                model = entry.get('model')
                transactions[txn]['model'] = model
            if 'objects' in entry:
                objects = entry.get('objects')
                transactions[txn]['objects'] = objects
            if 'format' in entry:
                frmt = entry.get('format')
                transactions[txn]['format'] = frmt
            else:
                frmt = 'unknown'
            if 'type' in entry:
                transactions[txn]['type'] = entry.get('type')
                transactions[txn]['requests'] = requests
            if 'agent' in entry:
                transactions[txn]['agent'] = entry.get('agent')
            if txn in transactions:
                if (transactions[txn].get('objects') is not None
                        and transactions[txn].get('model') is not None
                        and transactions[txn].get('time') is not None):
                    model = transactions[txn].get('model')
                    dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
                    date = dt.date()
                    hour = dt.hour
                    agent = entry.get('agent', '')
                    obj = [
                        {
                            'date': date,
                            'hour': hour,
                            'format': frmt,
                            'reqs': requests,
                            'count': objects,
                            'agent': agent,
                        }
                    ]
                    if len(model) > 0:
                        if model not in final_stats:
                            final_stats[model] = obj
                    if agent in bots:
                        bots_found['agents'] = bots_found.get('agents').get(agent, 0) + 1
                    else:
                        format_string = '%Y-%m-%d %H:%M:%S'
                        date_string = dt.strftime(format_string)
                        data = {
                            "source": name,
                            "model": model,
                            "format": frmt,
                            "time": date_string,
                            "requests": requests,
                            "objects": objects
                        }
                        transactions.pop(txn)
                        session.post(endpoint_url, data=data)
                        # print(f"Status Code: {r.status_code}, Response: {r.json()}")

            with open(bot_status_file, "w+") as bot_file:
                bot_file.write(json.dumps(bots_found, indent=4))


def blocks(files, size=65536):
    while True:
        b = files.read(size)
        if not b:
            break
        yield b


if __name__ == '__main__':
    run(main)
