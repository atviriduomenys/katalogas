import os
import json
from datetime import datetime
import requests as req
from typer import run, Option

# import user_agents

# bots = {
#     'SemrushBot',
#     'BLEXBot',
#     'Googlebot',
#     'PetalBot',
#     'crawler',
#     'Googlebot-Image',
#     'BingPreview',
#     'bingbot',
#     'archive.org_bot',
#     'DataForSeoBot',
#     'Adsbot',
# }

api_endpoint = 'http://localhost:8000/partner/api/1/downloads'

state_filename = 'state.json'
current_state = {"files": {}}

entries = []
lines = []
transactions = {}

def main(
        s: str = Option("get.data.gov.lt accesslog.dev-1.json", help=(
                "source url and log file absolute path"
        )),
):
    source = s.split(' ')[0]
    target = s.split(' ')[1]
    if not os.path.exists(target):
        print(f'File {target} not found. Aborting.')
    else:
        file_size = os.path.getsize(target)

        current_state['files'].setdefault(target, {'size': file_size})
        current_state['files'][target]['size'] = file_size
        with open(target) as f:
            for i in f:
                if 'txn' in i:
                    entry = json.loads(i)
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

        f.close()

        final_stats = {}

        for v in transactions.values():
            if 'time' in v and 'model' in v and 'objects' in v:
                model = v['model']
                objects = v['objects']
                exact = v['time']
                date = exact.date()
                hour = exact.hour
                frmt = ''
                requests = 0
                if 'format' in v:
                    frmt = v['format']
                if 'type' in v:
                    if v['type'] == 'request':
                        requests = 1
                dt = [{'date': date, 'hour': hour, 'format': frmt, 'reqs': requests, 'count': objects}]
                if model not in final_stats:
                    final_stats[model] = dt
                else:
                    if any(d['date'] == date for d in final_stats[model]):
                        for index, dictionary in enumerate(final_stats[model]):
                            if dictionary.get('hour') == hour:
                                count = final_stats[model][index]['count']
                                reqs = final_stats[model][index]['reqs']
                                final_stats[model][index] = {'date': date, 'hour': hour, 'format': frmt, 'reqs': reqs + 1,
                                                             'count': count + objects}
                                break
                    else:
                        final_stats[model].append(
                            {'date': date, 'hour': hour, 'format': frmt, 'reqs': requests, 'count': objects})

        for model, v in final_stats.items():
            for val in v:
                format_string = '%Y-%m-%d %H:%M:%S'
                date = val.get('date')
                time = datetime.min.time()
                hour = val.get('hour')
                full_date = datetime.combine(date, time).replace(hour=hour)
                date_string = full_date.strftime(format_string)
                print(date_string)
                r = req.post(url=api_endpoint, data={
                    "source": source,
                    "model": model,
                    "format": val.get('format'),
                    "time": date_string,
                    "requests": val.get('reqs'),
                    "objects": val.get('count')
                })
                print(f"Status Code: {r.status_code}, Response: {r.json()}")

        print(f'Total model entries found: {len(final_stats.keys())}')
        print(f'Total transaction entries in file: {len(transactions)}')

# def parse_user_agent(agent):
#     if isinstance(agent, str):
#         return user_agents.parse(agent).browser.family

if __name__ == '__main__':
    run(main)
