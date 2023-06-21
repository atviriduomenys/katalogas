pamac search github
#| github-cli  2.23.0-1  community 
#|     The GitHub CLI

pamac search hub
#| hub  2.14.2-3  community 
#|     cli interface for Github

sudo pacman -S hub github-cli

# https://github.com/settings/tokens
gh auth login
gh auth status
gh issue list
gh api graphql --paginate -f query='
query($endCursor: String) {
  repository(owner: "atviriduomenys", name: "spinta") {
    issues(first: 100, after: $endCursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        state
        title
        labels(first: 10) {
          nodes {
            name
            color
          }
        }
        milestone {
          number
          state
          title
        }
        projectItems (first: 5) {
          nodes {
            project {
              number
              title
            }
            fieldValues(first: 10) {
              nodes {
                ... on ProjectV2ItemFieldIterationValue {
                  title
                  startDate
                  duration
                  field {
                    ... on ProjectV2IterationField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldNumberValue {
                  number
                  field {
                    ... on ProjectV2Field {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2SingleSelectField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldTextValue {
                  text
                  field {
                    ... on ProjectV2Field {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
      totalCount
    }
  }
}
' > var/issues-spinta.json

gh api graphql --paginate -f query='
query($endCursor: String) {
  repository(owner: "atviriduomenys", name: "katalogas") {
    issues(first: 100, after: $endCursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        state
        title
        labels(first: 10) {
          nodes {
            name
            color
          }
        }
        milestone {
          number
          state
          title
        }
        projectItems (first: 5) {
          nodes {
            project {
              number
              title
            }
            fieldValues(first: 10) {
              nodes {
                ... on ProjectV2ItemFieldIterationValue {
                  title
                  startDate
                  duration
                  field {
                    ... on ProjectV2IterationField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldNumberValue {
                  number
                  field {
                    ... on ProjectV2Field {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldSingleSelectValue {
                  name
                  field {
                    ... on ProjectV2SingleSelectField {
                      name
                    }
                  }
                }
                ... on ProjectV2ItemFieldTextValue {
                  text
                  field {
                    ... on ProjectV2Field {
                      name
                    }
                  }
                }
              }
            }
          }
        }
      }
      totalCount
    }
  }
}
' > var/issues-katalogas.json


cat  var/issues-spinta.json | jq '.data.repository.issues.nodes[0]'

cat var/issues-spinta.json | jq -c '
.data.repository.issues.nodes[] |
    select(.projectItems.nodes[] | any(.project.title == "Portalo plėtra")) | [
    .number,
    .state,
    .title,
    (.projectItems.nodes[] | select(.project.title == "Portalo plėtra") | [
        .project.title
    ])
]
' | head -n 100

    .projectItems.nodes[] | select(.project.title == "Portalo plėtra") | [
        .project.title
    ]

jq var/issues-katalogas.json .
