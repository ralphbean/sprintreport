layout: false
.left-column[
## Completed
]
.right-column[
{% for feature in features -%}
{% if feature.has_work_in_status("Done") %}
[{{feature.key}}]({{feature.url}}) {{feature.summary}}
{%- for epic in feature.children %}{% if epic.has_work_in_status("Done") %}
* [{{epic.key}}]({{epic.url}}) {{epic.summary}}
{%- for issue in epic.children %}{% if issue.has_work_in_status("Done") %}
    - [{{issue.key}}]({{issue.url}}) {{issue.summary}}
{%- endif -%}
{% endfor -%}
{% endif -%}
{% endfor %}
{% endif -%}
{% endfor %}
]
