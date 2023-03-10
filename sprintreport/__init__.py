import operator as op
import os
import textwrap

import jinja2
import jira

from jinja2 import select_autoescape


class Issue(object):
    def __init__(self, client, raw_issue):
        self.client = client

        # TODO - these uses of customfield_... aren't portable.
        # Look them up using the meta API.
        self.key = raw_issue.key
        base_url = os.environ.get("JIRA_URL", "https://issues.redhat.com")
        self.url = base_url + "/browse/" + self.key
        self.summary = raw_issue.fields.summary
        self.rank = raw_issue.fields.customfield_12311940
        self.assignee = getattr(raw_issue.fields.assignee, 'raw', None)
        self.status = raw_issue.fields.status.raw['statusCategory']['name']
        self.children = []

        client.cache[self.key] = self

        self.epic = None
        self.feature = None

        epic_key = getattr(raw_issue.fields, 'customfield_12311140', None)
        feature_key = getattr(raw_issue.fields, 'customfield_12313140', None)
        if epic_key:
            self.epic = Issue.from_raw(client, client.get(epic_key))
            if self not in self.epic.children:
                self.epic.children.append(self)
            self.feature = self.epic.feature
        elif feature_key:
            self.feature = Issue.from_raw(client, client.get(feature_key))
            if self not in self.feature.children:
                self.feature.children.append(self)

    @staticmethod
    def from_raw(client, raw_issue):
        if raw_issue.key in client.cache:
            return client.cache[raw_issue.key]
        return Issue(client, raw_issue)

    def __repr__(self):
        return f"<{self.key}: {self.summary}>"

    def has_work_in_status(self, status):
        if self.status == status:
            return True
        for child in self.children:
            if child.has_work_in_status(status):
                return True
        return False


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
        def _paginate():
            i = 0
            page_size = 50
            results = self._client.search_issues(query, maxResults=page_size, startAt=i)
            while results:
                for result in results:
                    yield result
                i = i + page_size
                results = self._client.search_issues(
                    query, maxResults=page_size, startAt=i
                )

        return _paginate()

    def search(self, query):
        issues = self._search(query)
        return [Issue.from_raw(self, issue) for issue in issues]

    def get(self, key):
        if key not in self.cache:
            query = f"key={key}"
            results = self.search(query)
            if len(results) == 0:
                raise ValueError(f"Could not find issue {key}")
            if len(results) > 1:
                raise ValueError(f"Impossible! Found more than one issue {key}")
            self.cache[key] = results[0]
        return self.cache[key]

    def gather_issues(self, jql, sprint_start):
        issue_query = trim(
            f"""
            {jql} and
            type not in (Feature, Epic) and
            (statusCategory != Done or resolutionDate > {sprint_start})
        """
        )
        issues = self.search(issue_query)

        orphan_issues, orphan_epics, features = set(), set(), set()

        for issue in issues:
            if issue.feature:
                features.add(issue.feature)
            elif issue.epic:
                orphan_epics.add(issue.epic)
            else:
                orphan_issues.add(issue)

        orphan_issues = sorted(orphan_issues, key=op.attrgetter('rank'))
        orphan_epics = sorted(orphan_epics, key=op.attrgetter('rank'))
        features = sorted(features, key=op.attrgetter('rank'))

        return orphan_issues, orphan_epics, features

    def gather_dependencies(self, jql):
        not_done = "statusCategory != Done"
        jql = f"{jql} and {not_done}"
        incoming_query = (
            f"issueFunction in linkedIssuesOf('{jql}', 'is blocked by') and {not_done}"
        )
        incoming = sorted(self.search(incoming_query), key=op.attrgetter('rank'))
        outgoing_query = (
            f"issueFunction in linkedIssuesOf('{jql}', 'blocks') and {not_done}"
        )
        outgoing = sorted(self.search(outgoing_query), key=op.attrgetter('rank'))
        return incoming, outgoing


def trim(jql):
    return textwrap.dedent(jql).replace("\n", " ").strip()


def _truncate_filter(text, length):
    if len(text) > length:
        text = text[: length - 3] + '...'
    return text


def render(issues, epics, features, incoming, outgoing, template, start, end, title):
    basedir = os.path.dirname(os.path.dirname(__file__))
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(f'{basedir}/templates/'),
        autoescape=select_autoescape(),
    )
    env.filters['truncate'] = _truncate_filter
    return env.get_template(template).render(
        issues=issues,
        epics=epics,
        features=features,
        incoming=incoming,
        outgoing=outgoing,
        start=start,
        end=end,
        title=title,
    )
