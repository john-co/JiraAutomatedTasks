#!/usr/bin/env python
import getopt
import sys

from liferay.utils.sheets.sheets_helpers import set_update_time_in_cell, create_collapse_group_body
from liferay.utils.jira.jira_constants import Instance
from liferay.utils.jira.jira_liferay import get_jira_connection
from liferay.utils.sheets.sheets_liferay import get_testmap_connection

SUB_COMPONENTS_URL = Instance.Jira_URL + '/rest/net.brokenbuild.subcomponents/1.0/subcomponents'
SUB_COMPONENTS_COMMERCE_JSON_URL = SUB_COMPONENTS_URL + '/COMMERCE.json'
SUB_COMPONENTS_LPS_JSON_URL = SUB_COMPONENTS_URL + '/LPS.json'
SUB_COMPONENTS_LRAC_JSON_URL = SUB_COMPONENTS_URL + '/LRAC.json'

EPM_SPREADSHEET_ID = '1azJIucqKawYB7TMCnUIfmNac9iQEfkPDR5JKM6Nzia0'
EPM_TAB_BY_LEVEL_NAME = 'By Top Level Grouping'
EPM_TAB_BY_LEVEL_ID = '1959442404'
EPM_BY_LEVEL_TABLE_START_INDEX = '4'
EPM_BY_LEVEL_SPREADSHEET_RANGE = EPM_TAB_BY_LEVEL_NAME + '!B' + EPM_BY_LEVEL_TABLE_START_INDEX + ':M'
EPM_BY_LEVEL_FIRST_LEVEL_RANGE = EPM_TAB_BY_LEVEL_NAME + '!B' + EPM_BY_LEVEL_TABLE_START_INDEX + ':B'
EPM_BY_LEVEL_SECOND_LEVEL_RANGE = EPM_TAB_BY_LEVEL_NAME + '!E' + EPM_BY_LEVEL_TABLE_START_INDEX + ':E'

COLUMN_CONTENT_GIT_HUB_REPO = '=if(INDIRECT(ADDRESS(ROW(),COLUMN()-2))="","",if(INDIRECT(ADDRESS(ROW(),' \
                              'COLUMN()-2))<>"Product Team Business Process Management",VLOOKUP(INDIRECT(ADDRESS(' \
                              'ROW(),COLUMN()-2)),\'Team Information\'!C:F,3,false),VLOOKUP(concatenate(INDIRECT(' \
                              'ADDRESS(ROW(),COLUMN()-9)):INDIRECT(ADDRESS(ROW(),COLUMN()-6))),' \
                              '\'Team Information\'!H:K,4,false)))'

COLUMN_CONTENT_SLACK_CHANNEL = '=if(INDIRECT(ADDRESS(ROW(),COLUMN()-1))="","",if(INDIRECT(ADDRESS(ROW(),' \
                               'COLUMN()-1))<>"Product Team Business Process Management",VLOOKUP(INDIRECT(ADDRESS(' \
                               'ROW(),COLUMN()-1)),\'Team Information\'!C:F,2,false),VLOOKUP(concatenate(INDIRECT(' \
                               'ADDRESS(ROW(),COLUMN()-8)):INDIRECT(ADDRESS(ROW(),COLUMN()-5))),' \
                               '\'Team Information\'!H:K,3,false)))'


def _add_project_components_to_body_values(jira, body_values, json_url, component_name):
    components = jira._get_json("", None, json_url)['subcomponents']
    components_full_info = jira.project_components(component_name)
    for component in components:
        _process_line(body_values, component, components_full_info, 0, component_name)


def _create_group(sheet, spreadsheet_id, group_range, l1_list=None):
    l2_list = sheet.values().get(spreadsheetId=spreadsheet_id, range=group_range).execute().get('values', [])
    start = -1
    local_requests = []
    for i, level2 in enumerate(l2_list):
        element = level2
        if len(element) == 0 or element[0] == '':
            if l1_list:
                element = l1_list[i]
        if len(element) != 0:
            if element[0] != '':
                if start >= 0:
                    if i - start > 1:
                        local_requests.append(
                            create_collapse_group_body(EPM_TAB_BY_LEVEL_ID,
                                                       start + int(EPM_BY_LEVEL_TABLE_START_INDEX),
                                                       i + int(EPM_BY_LEVEL_TABLE_START_INDEX) - 1))

                start = i
    if not l1_list:
        local_requests.append(
            create_collapse_group_body(EPM_TAB_BY_LEVEL_ID,
                                       start + int(EPM_BY_LEVEL_TABLE_START_INDEX),
                                       len(l2_list) + int(EPM_BY_LEVEL_TABLE_START_INDEX)))
    body = {
        'requests': local_requests
    }
    sheet.batchUpdate(
        spreadsheetId=spreadsheet_id,
        body=body).execute()
    
    return l2_list


def _delete_all_raw_groups(sheet, spreadsheet_id, sheet_id):
    row_groups = _get_all_row_groups(sheet, spreadsheet_id, sheet_id)
    local_requests = []
    if row_groups is not None:
        for raw_group in row_groups:
            local_requests.append([{
                "deleteDimensionGroup": {
                    "range": {
                        'sheetId': raw_group.get('range').get('sheetId'),
                        'dimension': raw_group.get('range').get('dimension'),
                        'startIndex': raw_group.get('range').get('startIndex'),
                        'endIndex': raw_group.get('range').get('endIndex')
                    }
                }
            }])
        body = {
            'requests': local_requests
        }
        sheet.batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body).execute()


def _get_all_row_groups(sheet, spreadsheet_id, range_metadata):
    metadata = sheet.get(spreadsheetId=spreadsheet_id, ranges=range_metadata).execute()
    return metadata.get('sheets')[0].get('rowGroups')


def _line_data(line, components_full_info, deep, children, component_name):
    lead = ''
    archived = False
    for component in components_full_info:
        if component.name == line.get('name'):
            if hasattr(component, 'lead'):
                lead = component.lead.displayName
            archived = component.archived
            break
    if lead == '':
        lead = line.get('lead')
    if archived:
        status = 'Deprecated'
    else:
        status = 'Active'
    match deep:
        case 0:
            return [line.get('id'), component_name, line.get('name'), '', '', '', len(children), line.get('type')
                    .capitalize(), status, lead, COLUMN_CONTENT_SLACK_CHANNEL, COLUMN_CONTENT_GIT_HUB_REPO,
                    line.get('description')]
        case 1:
            return ['', '', '', line.get('name'), '', '', len(children), line.get('type').capitalize(), status,
                    lead, COLUMN_CONTENT_SLACK_CHANNEL, COLUMN_CONTENT_GIT_HUB_REPO, line.get('description')]
        case 2:
            return ['', '', '', '', line.get('name'), '', len(children), line.get('type').capitalize(), status,
                    lead, COLUMN_CONTENT_SLACK_CHANNEL, COLUMN_CONTENT_GIT_HUB_REPO, line.get('description')]
        case _:
            return ['', '', '', '', '', line.get('name'), len(children), line.get('type').capitalize(), status,
                    lead, COLUMN_CONTENT_SLACK_CHANNEL, COLUMN_CONTENT_GIT_HUB_REPO, line.get('description')]


def _process_line(body_values, line, components_full_info, deep, component_name):
    children = line.get('children', {})
    body_values.append(_line_data(line, components_full_info, deep, children, component_name))

    for child in children:
        _process_line(body_values, child, components_full_info, deep + 1, component_name)


def update_components_sheet(jira, spreadsheet_id):
    if spreadsheet_id == '':
        spreadsheet_id = EPM_SPREADSHEET_ID

    body_values = []

    _add_project_components_to_body_values(jira, body_values, SUB_COMPONENTS_COMMERCE_JSON_URL, "COMMERCE")

    _add_project_components_to_body_values(jira, body_values, SUB_COMPONENTS_LPS_JSON_URL, "LPS")

    _add_project_components_to_body_values(jira, body_values, SUB_COMPONENTS_LRAC_JSON_URL, "LRAC")

    sheet = get_testmap_connection()
    sheet.values().clear(
        spreadsheetId=spreadsheet_id, range=EPM_BY_LEVEL_SPREADSHEET_RANGE).execute()
    _delete_all_raw_groups(sheet, spreadsheet_id, EPM_BY_LEVEL_SPREADSHEET_RANGE)

    body = {
        'values': body_values
    }
    sheet.values().append(
        spreadsheetId=spreadsheet_id, range=EPM_BY_LEVEL_SPREADSHEET_RANGE, valueInputOption='USER_ENTERED',
        body=body).execute()

    l1_list = _create_group(sheet, spreadsheet_id, EPM_BY_LEVEL_FIRST_LEVEL_RANGE)

    _create_group(sheet, spreadsheet_id, EPM_BY_LEVEL_SECOND_LEVEL_RANGE, l1_list)

    set_update_time_in_cell(sheet, spreadsheet_id, 'B1')


def main(argv):
    spreadsheet_id = ''
    opts, args = getopt.getopt(argv, "hs:", ["sheet_id="])
    for opt, arg in opts:
        if opt == '-h':
            print('epm_automations.py -s <sheet_id>')
            sys.exit()
        elif opt in ("-s", "--sheet_id"):
            spreadsheet_id = arg
    jira_connection = get_jira_connection()
    update_components_sheet(jira_connection, spreadsheet_id)


if __name__ == "__main__":
    main(sys.argv[1:])
