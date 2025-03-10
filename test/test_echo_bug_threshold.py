import unittest

from liferay.teams.echo.echo_bugs_dashboard import update_echo_bug_threshold
from liferay.utils.jira.jira_liferay import get_jira_connection
from liferay.utils.sheets.sheets_liferay import get_testmap_connection


class EchoTestMapTests(unittest.TestCase):

    def test_update_echo_bug_threshold(self):
        try:
            info_test = ''
            jira_connection_test = get_jira_connection()
            sheet_connection_test = get_testmap_connection()
            info_test = update_echo_bug_threshold(sheet_connection_test, jira_connection_test, info_test)
        except Exception:
            self.fail("Test failed unexpectedly!")


if __name__ == '__main__':
    unittest.main()
