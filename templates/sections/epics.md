.left-column[
## Completed
## In Progress
## Next
## Dependencies
## Other Epics
]
.right-column[

## Work completed on epics with no feature
{%- for epic in epics %}{% if epic.has_work_in_status("Done") %}
* [{{epic.key}}]({{epic.url}}) {{epic.summary}}
{%- for issue in epic.children %}{% if issue.has_work_in_status("Done") %}
    - [{{issue.key}}]({{issue.url}}) {{issue.summary}}
{%- endif -%}
{% endfor %}
{% endif -%}
{% endfor %}
]
