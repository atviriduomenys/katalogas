pamac search github
#| github-cli  2.23.0-1  community 
#|     The GitHub CLI

pamac search hub
#| hub  2.14.2-3  community 
#|     cli interface for Github

sudo pacman -S hub github-cli

# https://github.com/settings/tokens
gh auth login -h github.com
gh auth status
gh issue list

query=$(poetry run python scripts/github-export.py -q spinta)
gh api graphql --paginate -f query=$query | jq . > var/issues-spinta-pretty.json
cat var/issues-spinta-pretty.json | jq -c '.data.repository.issues.nodes[]' > var/issues.json

query=$(poetry run python scripts/github-export.py -q katalogas)
gh api graphql --paginate -f query=$query | jq . > var/issues-katalogas-pretty.json
cat var/issues-katalogas-pretty.json | jq -c '.data.repository.issues.nodes[]' >> var/issues.json

poetry run python scripts/github-export.py var/issues.json  --project="Portalo plėtra" --export=var/tasks.csv --simple
poetry run python scripts/github-export.py var/issues.json  --project="Portalo plėtra" --export=var/tasks.csv
