import os
import textwrap

import jira

# import jinja2


class Issue(object):
    def __init__(self, client, raw_issue):
        self.client = client

        self.key = raw_issue.key
        self.summary = raw_issue.summary
        self.rank = raw_issue.rank
        self.children = []

        client.cache[self.key] = self

        self.epic = None
        self.feature = None

        if raw_issue.epic:
            self.epic = Issue.from_raw(client, client.get(raw_issue.epic))
            self.epic.children.append(self)
            self.feature = self.epic.feature

        elif raw_issue.feature:
            self.feature = Issue.from_raw(client, client.get(raw_issue.feature))
            self.feature.children.append(self)

    @staticmethod
    def from_raw(client, raw_issue):
        if raw_issue.key in client.cache:
            return client.cache[raw_issue.key]
        return Issue(client, raw_issue)

    def __repr__(self):
        return f"<{self.key}: {self.summary}>"


class JiraClient(object):
    def __init__(self):
        self._client = self._construct_client()
        self.cache = {}

    @staticmethod
    def _construct_client():
        url = os.environ.get("JIRA_URL", "https://issues.redhat.com")
        token = os.environ.get("JIRA_TOKEN")
        if not token:
            raise KeyError(
                "Set JIRA_TOKEN environment variable to your JIRA personal access token"
            )

        return jira.client.JIRA(server=url, token_auth=token)

    def _search(self, query):
        return self._client.search_issues(query)

    def search(self, query):
        issues = self._search(query)
        return [Issue.from_raw(self, issue) for issue in issues]

    def get(self, key):
        query = f"key={key}"
        results = self.search(query)
        if len(results) == 0:
            raise ValueError(f"Could not find issue {key}")
        if len(results) > 1:
            raise ValueError(f"Impossible! Found more than one issue {key}")
        return results[0]

    def gather_issues(self, jql, sprint_start):
        issue_query = trim(
            f"""
            {jql} and
            type not in (Feature, Epic) and
            (statusCategory != Done or resolutionDate > {sprint_start})
        """
        )
        issues = self.search(issue_query)

        orphan_issues, orphan_epics, features = [], [], []

        for issue in issues:
            if issue.feature:
                features.append(issue.feature)
            elif issue.epic:
                orphan_epics.append(issue.epic)
            else:
                orphan_issues.append(issue)

        return orphan_issues, orphan_epics, features


def trim(jql):
    return textwrap.dedent(jql).replace("\n", " ").strip()


def render(issues, epics, features, incoming, outgoing):
    return "TODO"
