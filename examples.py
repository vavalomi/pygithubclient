from datetime import datetime
from requests import Session
from sgqlc.endpoint.requests import RequestsEndpoint
from sgqlc.operation import Operation

from github_schema import (
    AddProjectV2ItemByIdInput,
    CreateIssueInput,
    Mutation,
    ProjectV2,
    ProjectV2IterationField,
    ProjectV2Field,
    ProjectV2FieldValue,
    ProjectV2SingleSelectField,
    Query,
    UpdateProjectV2ItemFieldValueInput, 
)
  

class GHClient():
    def __init__(self, access_token):
        self.url = "https://api.github.com/graphql"
        self.s = Session()
        self.s.headers.update({"Authorization": f"Bearer {access_token}"})

    def execute(self, op):
        endpoint = RequestsEndpoint(self.url, session=self.s)
        cont = endpoint(op)

        errors = cont.get("errors")
        if not errors:
            return (op + cont)
        else:
            print(errors)
            raise RuntimeError(errors[0]["message"])


# GraphQL operations use global node IDs so we have calls to get those

def get_repo_id(client, owner, repo_name):
    op = Operation(Query)
    q = op.repository(owner=owner, name=repo_name)
    q.__fields__("id")
    r = client.execute(op)
    return r.repository.id


def get_project_id(client, owner, project_number):
    op = Operation(Query)
    q = op.organization(login=owner).project_v2(number=project_number)
    q.__fields__("id")

    r = client.execute(op)
    return r.organization.project_v2.id


def get_issue_id(client, owner, repo_name, issue_number):
    op = Operation(Query)
    q = op.repository(owner=owner, name=repo_name).issue(number=issue_number)
    q.__fields__("id")

    r = client.execute(op)
    return r.repository.issue.id


# Mutations can return the full object but we're only requesting id to be returned below

def create_issue(client, repo_id, issue_title, issue_body=""):
    op = Operation(Mutation)
    input = CreateIssueInput(title=issue_title, body=issue_body, repository_id=repo_id)
    q = op.create_issue(input=input).issue()
    q.__fields__("id")

    r = client.execute(op)
    return r.create_issue.issue.id


def add_issue_to_project(client, project_id, issue_id):
    op = Operation(Mutation)
    input = AddProjectV2ItemByIdInput(project_id=project_id, content_id=issue_id)
    q = op.add_project_v2_item_by_id(input=input).item()
    q.__fields__("id")

    r = client.execute(op)
    return r.add_project_v2_item_by_id.item.id


def collect_field_info(client, project_id):
    """This is perhaps not so elegant solution of having all in a large dict, but as an example should work.
    returns dict of three dicts
        result["fields"] would contain a dict of field_name: node_id for all editable fields (assignees, labels, repository are not)
        result["single_select_options"] a dict of field_name: { option_name: option_id }
        result["iterations"] a dict of field_name: {iteration_title: id }
    """
    op = Operation(Query)

    nodes = op.node(id=project_id).__as__(ProjectV2).fields(first=20).nodes()
    nodes.__as__(ProjectV2SingleSelectField).__fields__("id", "name", "data_type")
    nodes.__as__(ProjectV2SingleSelectField).options().__fields__("id", "name")
    nodes.__as__(ProjectV2IterationField).__fields__("id", "name", "data_type")
    nodes.__as__(ProjectV2IterationField).configuration().iterations().__fields__("id", "title")
    nodes.__as__(ProjectV2Field).__fields__("id", "name", "data_type")

    r = client.execute(op)
    return {
                "fields": {
                    node.name: node.id
                    for node in r.node.fields.nodes
                    if node.data_type in ["DATE", "ITERATION", "NUMBER", "SINGLE_SELECT", "TEXT", "TITLE",]
                },
                "single_select_options": {
                    node.name: {opt.name: opt.id for opt in node.options}
                    for node in r.node.fields.nodes
                    if node.data_type == "SINGLE_SELECT"        
                },
                "iterations" : {
                    node.name: {opt.title: opt.id for opt in node.configuration.iterations}
                    for node in r.node.fields.nodes
                    if node.data_type == "ITERATION"        
                },
            }


def set_project_card_value(client, project_id, item_id, field_id, value):

    input = UpdateProjectV2ItemFieldValueInput(
        project_id=project_id, item_id=item_id,
        field_id=field_id, value=value)

    op = Operation(Mutation)
    q = op.update_project_v2_item_field_value(input=input).project_v2_item()
    q.__fields__("id")

    r = client.execute(op)

    return r.update_project_v2_item_field_value.project_v2_item.id



client = GHClient(access_token="your super secret token which you would not store in the code")

project_id = get_project_id(client, "organization_or_user", 2)
repo_id = get_repo_id(client, "organization_or_user", "repo")
issue_id = get_issue_id(client, "organization_or_user", "repo", 56)

issue_id = create_issue(client,repo_id,"test issue", "this is an issue")
node_id = add_issue_to_project(client, project_id, issue_id)


# In order to update project card fields we need to get information about element IDs
field_info = collect_field_info(client, project_id)

set_project_card_value(client, project_id, node_id,
                        field_id=field_info["fields"]["textf"],
                        value=ProjectV2FieldValue(text="aaa"))

set_project_card_value(client, project_id, node_id, 
                       field_id=field_info["fields"]["Status"], 
                       value=ProjectV2FieldValue(single_select_option_id=field_info["single_select_options"]["Status"]["Todo"]))

set_project_card_value(client, project_id, node_id,
                       field_id = field_info["fields"]["datef"],
                       value=ProjectV2FieldValue(date=datetime(2023, 4, 12).date()))

set_project_card_value(client, project_id, node_id,
                       field_id = field_info["fields"]["numf"],
                       value=ProjectV2FieldValue(number=34))

set_project_card_value(client, project_id, node_id,
                       field_id = field_info["fields"]["iterf"],
                       value=ProjectV2FieldValue(iteration_id=field_info["iterations"]["iterf"]["iterf 1"]))
