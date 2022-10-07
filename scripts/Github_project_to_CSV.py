"""
poetry init -n
poetry add requests
poetry add pprintpp
poetry run python
"""

import json
import csv

import requests
from pprintpp import pprint as pp

# https://github.com/settings/tokens/819269469
token = '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'
session = requests.Session()
session.headers['Authorization'] = f'Bearer {token}'

pp(session.post('https://api.github.com/graphql', json={'query': '''\
query{
    organization(login: "atviriduomenys"){
      projectsNext(first: 10) {
        nodes {
          id
          title
        }
      }
    }
}
'''}).json())
#| {'id': 'PN_kwDOAKaBNM4AA9o2', 'title': 'Portalo plėtra'},

with open('/tmp/Github_project_to_csv_file.csv', 'w') as f_csv:
    writer = csv.writer(f_csv)

    loop = True
    cursor = None
    while loop:
        resp = session.post('https://api.github.com/graphql', json={
            'query': '''\
             query cards($project: ID!, $cursor: String) {
              node(id: $project) {
                id
                ... on ProjectNext {
                  id
                  title
                  items(first: 10, after: $cursor) {
                    nodes {
                      content {
                        ... on Issue {
                          id
                          title
                          number
                          state
                          repository {
                            name
                          }
                        }
                      }
                      title
                      fieldValues(first: 10) {
                        nodes {
                          value
                          projectField {
                            name
                            settings
                          }
                        }
                      }
                    }
                    edges {
                      cursor
                    }
                    pageInfo {
                      hasNextPage
                    }
                  }
                }
              }
            }
            ''',
            'variables': {
                'project': 'PN_kwDOAKaBNM4AGx3p',
                'cursor': cursor,
            }
        })

        resp.raise_for_status()
        project = resp.json()

        with open('/tmp/data.json', 'a') as f:
            json.dump(project, f, indent=2)

        if project['data']['node']['items']['edges']:
            cursor = project['data']['node']['items']['edges'][-1]['cursor']
        else:
            cursor = None
        loop = project['data']['node']['items']['pageInfo']['hasNextPage']

        for card in project['data']['node']['items']['nodes']:
            if card['content']:
                data = card['content'].copy()
                data['repository'] = card['content']['repository']['name']
            else:
                data = {}

            for field in card['fieldValues']['nodes']:
                name = field['projectField']['name']
                value = field['value']
                if 'sttings' in field['projectField']:
                    settings = json.loads(field['projectField']['settings'])
                    if 'options' in settings:
                        options = {
                            opt['id']: opt['name']
                            for opt in settings['options']
                        }
                        if value in options:
                            value = options[value]
                data[name] = value
            pp(data)

            for key in data.keys():
                f_csv.write(f'{key}, {data[key]}\n')

