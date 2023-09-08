import resource
import os
import json
import urllib.parse

from pathlib import Path
from datetime import datetime

import user_agents
import requests as req

from typer import run, Option
from typer import Argument

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
    name: str = Argument(help="stats source name, i.e. get.data.gov.lt"),
    logfile: str = Argument(help=(
        "log file to read stats from, i.e. accesslog.json"
    )),
    target: str = Option("http://localhost:8000", help=(
        "target server url"
    )),
    config_dir: str = Option('~/.local/share/vitrina'),
    data_dir: str = Option('~/.config/vitrina'),
    config_file: str = Option(),
):
    config_file = os.path.expanduser('~') + '/.config/vitrina/downloadstats.json'
    state_file = os.path.expanduser('~') + '/.local/share/vitrina/state.json'
    bot_status_file = os.path.expanduser('~') + '/.local/share/vitrina/downloadstats.json'
    current_state = {}

    bots_found = {'agents': {}}
    final_stats = {}
    file_size = os.path.getsize(logfile)
    existing_size = 0
    existing_offset = 0

    if not os.path.exists(os.path.dirname(state_file)):
        os.makedirs(os.path.dirname(state_file))
    else:
        with open(state_file, 'r') as f:
            current_state = json.load(f)
        state = current_state.get('files').get(logfile)
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
    session = req.Sesssion()

    with open(logfile) as f:
        bytesread = 0
        if existing_offset > 0:
            f.seek(existing_offset)
        while True:
            line1 = f.readline()
            line2 = f.readline()
            bytesread += len((line1 + line2).encode('utf-8'))
            if 'txn' in line1 and 'txn' in line2:
                entry1 = json.loads(line1)
                entry2 = json.loads(line2)
                entry = entry1 | entry2
                txn1 = entry1['txn']
                txn2 = entry2['txn']
                if txn1 == txn2:
                    timestamp = entry['time']
                    dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
                if (
                    'time' in entry and
                    'model' in entry and
                    'objects' in entry
                ):
                    model = entry.get('model')
                    objects = entry.get('objects')
                    date = dt.date()
                    hour = dt.hour
                    agent = ''
                    requests = 0

                    frmt = entry.get('format', '')
                    if entry.get('type') == 'request':
                        requests = 1
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
                        r = session.post(endpoint_url, data=data)
                        print(f"Status Code: {r.status_code}, Response: {r.json()}")

            with open(bot_status_file, "w+") as bot_file:
                bot_file.write(json.dumps(bots_found, indent=4))

            if not line1 or not line2:
                break

        state_entry = {
            logfile: {
                'size': file_size,
                'offset': bytesread
            }
        }

    current_state.get('files', {}).update(state_entry)

    with open(state_file, "w") as outfile:
        outfile.write(json.dumps(current_state, indent=4))

    with open(bot_status_file, "w+") as bot_file:
        bot_file.write(json.dumps(bots_found, indent=4))

    print(f'Total model entries found: {len(final_stats.keys())}')
    # print(f'Total transaction entries in file: {len(transactions)}')
    print(f'Peak Memory Usage = {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}')


def parse_user_agent(agent):
    if isinstance(agent, str):
        return user_agents.parse(agent).browser.family


if __name__ == '__main__':
    run(main)
