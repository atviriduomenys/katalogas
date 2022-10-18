import json
import csv
import sys

from typing import Optional

from typer import Argument
from typer import run

import requests
from pprintpp import pprint as pp


def main(
        token: str = Argument(..., help='https://github.com/settings/tokens'),
        project_id: Optional[str] = Argument(None, help='Argument to specify a project id.\n'
                                                        'Project id can be found in the printed output data by node id.')
):
    session = requests.Session()
    session.headers['Authorization'] = f'Bearer {token}'

    if project_id is None:
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
        exit()

    writer = csv.writer(sys.stdout)

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
                'project': project_id,
                'cursor': cursor,
            }
        })

        resp.raise_for_status()
        project = resp.json()

        with open('/tmp/data.json', 'a') as f:
            json.dump(project, f, indent=2)
        
        if project['data']['node'] is None:
            pp(project['errors'])
            exit()

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

            for key in data.keys():
                writer.writerow([key, data[key]])
            writer.writerow([''])


if __name__ == '__main__':
    run(main)

