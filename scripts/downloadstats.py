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


def main(
        name: str = Argument(..., help="stats source name, i.e. get.data.gov.lt"),
        logfile: str = Argument(..., help=(
                "log file to read stats from, i.e. accesslog.json"
        )),
        target: str = Option("http://localhost:8000", help=(
                "target server url"
        )),
        config_file: str = Option(os.path.expanduser('~/.config/vitrina/downloadstats.json')),
        state_file: str = Option(os.path.expanduser('~/.local/share/vitrina/state.json')),
        bot_status_file: str = Option(os.path.expanduser('~/.local/share/vitrina/downloadstats.json')),
):
    transactions = {}
    current_state = {'files': {}}

    bots_found = {'agents': {}}
    apikey = ""

    limit = 1000
    total_lines_read = 0
    lines_read = 0
    final_stats = {}
    file_size = os.path.getsize(logfile)
    existing_size = 0
    existing_offset = 0
    temp = {}

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
            data = json.load(config)
            bot_list = data.get('bots')
            bots.update(bot_list)
            apikey = data.get('apikey')

    if not os.path.exists(logfile):
        print(f'File {logfile} not found. Aborting.')
        return

    if file_size == existing_size:
        # File did not change?
        return

    endpoint_url = urllib.parse.urljoin(target, 'partner/api/1/downloads')
    session = req.Session()
    session.headers.update({'Authorization': 'ApiKey {}'.format(apikey)})

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
                find_transactions(name, d, final_stats, bot_status_file, bots_found, temp, transactions)
                lines_read = 0
            state_entry = {
                logfile: {
                    'size': file_size,
                    'offset': bytesread
                }
            }
            pbar.update(1)
        find_transactions(name, d, final_stats, bot_status_file, bots_found, temp, transactions)

    post_data(temp, name, session, endpoint_url)

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


def find_transactions(name, d, final_stats, bot_status_file, bots_found, temp, transactions):
    for i in d:
        if '"txn"' in i:
            entry = json.loads(i)
            txn = entry['txn']
            timestamp = entry['time']
            dt = None
            try:
                dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
            except ValueError as ve:
                print(f'Wrong timestamp format {timestamp}')
            requests = 1
            if txn not in transactions:
                transactions[txn] = {'time': dt}
            else:
                transactions[txn]['time'] = dt
            if 'model' in entry:
                transactions[txn]['model'] = entry.get('model')
            if 'format' in entry:
                transactions[txn]['format'] = entry.get('format')
            if 'type' in entry:
                transactions[txn]['type'] = entry.get('type')
                transactions[txn]['requests'] = requests
            if 'agent' in entry:
                transactions[txn]['agent'] = entry.get('agent')
            if entry.get('type') == 'response':
                objects = entry.get('objects', 0)
                transactions[txn]['objects'] = objects
                model = transactions[txn].get('model')
                if 'time' in entry:
                    dt = datetime.strptime(entry.get('time'), '%Y-%m-%dT%H:%M:%S.%f%z')
                else:
                    dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
                date = dt.date()
                hour = dt.hour
                minute = dt.minute
                agent = transactions[txn].get('agent')
                frmt = transactions[txn].get('format')
                obj = [
                    {
                        'date': date,
                        'hour': hour,
                        'minute': minute,
                        'format': frmt,
                        'reqs': requests,
                        'count': objects,
                        'agent': agent,
                    }
                ]
                if model is not None and len(model) > 0:
                    if model not in final_stats:
                        final_stats[model] = obj
                bot_in_list = False
                if agent:
                    for bt in bots:
                        if bt in agent:
                            bot_in_list = True
                            bots_found['agents'][bt] = bots_found.get('agents').get(bt, 0) + 1
                            break
                if not bot_in_list:
                    if agent:
                        bots_found['agents'][agent] = bots_found.get('agents').get(agent, 0) + 1
                    data = [{
                        "source": name,
                        "model": model,
                        "time": dt,
                        "date": date,
                        "hour": hour,
                        'minute': minute,
                        "format": frmt,
                        "requests": requests,
                        "objects": objects
                    }]
                    transactions.pop(txn)
                    if model:
                        if model not in temp:
                            temp[model] = data
                        else:
                            if any(d['date'] == date for d in temp[model]):
                                hour_found = False
                                for index, dictionary in enumerate(temp[model]):
                                    if (
                                            dictionary.get('hour') == hour
                                            and dictionary.get('source') == name
                                            and dictionary.get('format') == frmt
                                    ) or (
                                            dictionary.get('hour') == hour + 1
                                            and dictionary.get('minute') == 1
                                            and dictionary.get('source') == name
                                            and dictionary.get('format') == frmt
                                    ):
                                        hour_found = True
                                        obj_count = temp[model][index]['objects']
                                        requests = temp[model][index]['requests']
                                        temp[model][index] = {'source': name, 'model': model, 'time': dt, 'date': date,
                                                              'hour': hour, 'format': frmt, 'requests': requests + 1,
                                                              'objects': obj_count + objects}
                                if not hour_found:
                                    temp[model].append(
                                        {'source': name, 'model': model, 'time': dt, 'date': date, 'hour': hour,
                                         'format': frmt, 'requests': requests, 'objects': objects})
                            else:
                                temp[model].append(
                                    {'source': name, 'model': model, 'time': dt, 'date': date, 'hour': hour,
                                     'format': frmt, 'requests': requests, 'objects': objects})

            with open(bot_status_file, "w+") as bot_file:
                bot_file.write(json.dumps(bots_found, indent=4))


def post_data(data, name, session, endpoint):
    pbar = tqdm("Posting download stats", total=sum([len(stats) for stats in data.values()]))
    for model, stats in data.items():
        for st in stats:
            info = {
                "source": name,
                "model": model,
                "time": st.get('time'),
                "format": st.get('format'),
                "requests": st.get('requests'),
                "objects": st.get('objects')
            }
            req = session.post(endpoint, data=info)
            req.raise_for_status()
            pbar.update(1)
        data[model] = []


def blocks(files, size=65536):
    while True:
        b = files.read(size)
        if not b:
            break
        yield b


if __name__ == '__main__':
    run(main)
