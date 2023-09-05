import resource
import os
import json
from pathlib import Path
from datetime import datetime
import requests as req
from typer import run, Option
import user_agents

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

config_file = os.path.expanduser('~') + '/.config/vitrina/downloadstats.json'
state_file = os.path.expanduser('~') + '/.local/share/vitrina/state.json'
bot_status_file = os.path.expanduser('~') + '/.local/share/vitrina/downloadstats.json'
current_state = {}

entries = []
lines = []
transactions = {}


def main(
        s: str = Option("get.data.gov.lt accesslog.dev-1.json", help=(
                "source url and log file absolute path"
        )),
        endpoint: str = Option("http://localhost:8000/partner/api/1/downloads", help=(
            "api endpoint for posting data"
        ))
):
    bots_found = {'agents': {}}
    final_stats = {}
    source = s.split(' ')[0]
    target = s.split(' ')[1]
    file_size = os.path.getsize(target)
    existing_size = 0
    existing_offset = 0
    existing_bytes = 0

    if not os.path.exists(os.path.dirname(state_file)):
        os.makedirs(os.path.dirname(state_file))
    else:
        with open(state_file, 'r') as state:
            current_state = json.load(state)
            for val in current_state.get('files'):
                if target == val:
                    existing_size = current_state.get('files').get(target).get('size')
                    existing_offset = current_state.get('files').get(target).get('lines')
                    existing_bytes = current_state.get('files').get(target).get('offset')

    if not os.path.exists(os.path.dirname(bot_status_file)):
        os.makedirs(os.path.dirname(bot_status_file))
    if not os.path.exists(bot_status_file):
        file = Path(bot_status_file)
        file.touch(exist_ok=True)
    else:
        with open(bot_status_file, 'r') as state:
            if os.path.getsize(bot_status_file) > 0:
                bots_found = json.load(state)

    if os.path.exists(config_file):
        with open(config_file, 'r') as config:
            bot_list = json.load(config).get('bots')
            bots.update(bot_list)

    if not os.path.exists(target):
        print(f'File {target} not found. Aborting.')
    else:
        if file_size != existing_size:
            with open(target) as f:
                bytesread = 0
                lines = 0
                if existing_offset > 0:
                    f.seek(existing_offset)
                while True:
                    line1 = f.readline()
                    line2 = f.readline()
                    bytesread += len(line1)
                    bytesread += len(line2)
                    lines += 2
                    if 'txn' in line1 and 'txn' in line2:
                        entry1 = json.loads(line1)
                        entry2 = json.loads(line2)
                        entry = entry1 | entry2
                        txn1 = entry1['txn']
                        txn2 = entry2['txn']
                        if txn1 == txn2:
                            timestamp = entry['time']
                            dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
                        if 'time' in entry.keys() and 'model' in entry.keys() and 'objects' in entry.keys():
                            model = entry.get('model')
                            objects = entry.get('objects')
                            date = dt.date()
                            hour = dt.hour
                            frmt = ''
                            agent = ''
                            requests = 0

                            if 'format' in entry.keys():
                                frmt = entry.get('format')
                            if 'type' in entry.keys():
                                if entry.get('type') == 'request':
                                    requests = 1
                            if 'agent' in entry.keys():
                                agent = entry.get('agent')
                            obj = [{'date': date, 'hour': hour, 'format': frmt, 'reqs': requests, 'count': objects,
                                   'agent': agent}]
                            if model not in final_stats:
                                final_stats[model] = obj
                            if agent in bots:
                                bots_found['agents'] = bots_found.get('agents').get(agent, 0) + 1
                            else:
                                format_string = '%Y-%m-%d %H:%M:%S'
                                date_string = dt.strftime(format_string)
                                data = {
                                    "source": source,
                                    "model": model,
                                    "format": frmt,
                                    "time": date_string,
                                    "requests": requests,
                                    "objects": objects
                                }
                                r = req.post(url=endpoint, data=data)
                                print(f"Status Code: {r.status_code}, Response: {r.json()}")

                    with open(bot_status_file, "w+") as bot_file:
                        bot_file.write(json.dumps(bots_found, indent=4))

                    if not line1 or not line2:
                        break

                state_entry = {
                    target: {
                        'size': file_size,
                        'lines': lines,
                        'offset': bytesread
                    }}

            f.close()

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
