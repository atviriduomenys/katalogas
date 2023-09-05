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
            for val in current_state.values():
                if target in val:
                    for i in val.values():
                        existing_size = i.get('size')
                        existing_offset = i.get('lines')
                        existing_bytes = i.get('offset')

    if not os.path.exists(os.path.dirname(bot_status_file)):
        os.makedirs(os.path.dirname(bot_status_file))
    if not os.path.exists(bot_status_file):
        file = Path(bot_status_file)
        file.touch(exist_ok=True)
    else:
        with open(bot_status_file, 'r') as state:
            if os.path.getsize(bot_status_file) > 0:
                bots_found = json.load(state).get('agents')

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
                for index, line in enumerate(f):
                    if index > existing_offset:
                        bytesread += len(line)
                        if 'txn' in line:
                            entry = json.loads(line)
                            txn = entry['txn']
                            timestamp = entry['time']
                            dt = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f%z')
                            if txn not in transactions:
                                transactions[txn] = {'time': dt}
                            if 'model' in entry:
                                model = entry['model']
                                transactions[txn]['model'] = model
                            if 'objects' in entry:
                                objects = entry['objects']
                                transactions[txn]['objects'] = objects
                            if 'format' in entry:
                                frmt = entry['format']
                                transactions[txn]['format'] = frmt
                            if 'type' in entry:
                                transactions[txn]['type'] = entry['type']
                            if 'agent' in entry:
                                transactions[txn]['agent'] = entry['agent']

                state_entry = {
                    target: {
                        'size': file_size,
                        'line': index,
                        'offset': bytesread
                    }}

            f.close()

            current_state.get('files', {}).update(state_entry)

            with open(state_file, "w") as outfile:
                outfile.write(json.dumps(current_state, indent=4))

            for v in transactions.values():
                if 'time' in v and 'model' in v and 'objects' in v:
                    model = v['model']
                    objects = v['objects']
                    exact = v['time']
                    date = exact.date()
                    hour = exact.hour
                    frmt = ''
                    agent = ''
                    requests = 0
                    if 'format' in v:
                        frmt = v['format']
                    if 'type' in v:
                        if v['type'] == 'request':
                            requests = 1
                    if 'agent' in v:
                        agent = v['agent']
                    dt = [{'date': date, 'hour': hour, 'format': frmt, 'reqs': requests, 'count': objects,
                           'agent': agent}]
                    if model not in final_stats:
                        final_stats[model] = dt
                    else:
                        if any(d['date'] == date for d in final_stats[model]):
                            for index, dictionary in enumerate(final_stats[model]):
                                if dictionary.get('hour') == hour:
                                    count = final_stats[model][index]['count']
                                    reqs = final_stats[model][index]['reqs']
                                    final_stats[model][index] = {'date': date, 'hour': hour, 'format': frmt,
                                                                 'reqs': reqs + 1,
                                                                 'count': count + objects,
                                                                 'agent': agent}
                                    break
                        else:
                            final_stats[model].append(
                                {'date': date, 'hour': hour, 'format': frmt, 'reqs': requests, 'count': objects,
                                 'agent': agent})

            for model, v in final_stats.items():
                for val in v:
                    agent = val.get('agent')
                    if agent in bots:
                        bots_found['agents'] = bots_found.get('agents').get(agent, 0) + 1
                    else:
                        format_string = '%Y-%m-%d %H:%M:%S'
                        date = val.get('date')
                        time = datetime.min.time()
                        hour = val.get('hour')
                        full_date = datetime.combine(date, time).replace(hour=hour)
                        date_string = full_date.strftime(format_string)
                        data = {
                            "source": source,
                            "model": model,
                            "format": val.get('format'),
                            "time": date_string,
                            "requests": val.get('reqs'),
                            "objects": val.get('count')
                        }
                        r = req.post(url=endpoint, data=data)
                        print(f"Status Code: {r.status_code}, Response: {r.json()}")

            with open(bot_status_file, "w+") as bot_file:
                bot_file.write(json.dumps(bots_found, indent=4))

            print(f'Total model entries found: {len(final_stats.keys())}')
            print(f'Total transaction entries in file: {len(transactions)}')
            print(f'Peak Memory Usage = {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}')

def parse_user_agent(agent):
    if isinstance(agent, str):
        return user_agents.parse(agent).browser.family


if __name__ == '__main__':
    run(main)
