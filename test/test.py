import unittest
import sys
sys.path.append('..')
from datetime import datetime
from bin.changelog import Release
from bin.changelog import ReleaseClass
from bin.changelog import Change
from bin.changelog import ChangeGroup
from bin.changelog import ChangeLog
from bin.changelog import ChangeClass
from bin.changelog import SemanticVersion
from bin.changelog import InvalidJsonFormatError
from bin.changelog import InvalidChangeClassError
from bin.changelog import InvalidChangeTypeError
from bin.changelog import InvalidReleaseClassError
from bin.changelog import InvalidDatetimeError
from bin.changelog import MissingKeyFormatError

class TestChangeLog(unittest.TestCase):
    def test_changelog_minimum_valid_format(self):
        try:
            ChangeLog.parse_changelog('''{
                "changes": {},
                "change types": { "major": [], "minor": [], "patch": [], "internal": [] },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except:
            self.fail('format is invalid.')


    def test_changelog_invalid_change_class(self):
        try:
            ChangeLog.parse_changelog('''{
                "changes": {},
                "change types": { "major": [], "minor": [], "subminor": [], "internal": [] },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except Exception as e:
            self.assertIsInstance(e, InvalidChangeClassError)
        else:
            self.fail('should raise.')


    def test_changelog_invalid_datetime(self):
        try:
            ChangeLog.parse_changelog('''{
                "changes": {
                    "2023-08-30 0:00:00": [
                        { "valid": "but datetime is not valid" }
                    ]
                },
                "change types": { "major": [ "valid" ], "minor": [], "patch": [], "internal": [] },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except Exception as e:
            self.assertIsInstance(e, InvalidDatetimeError)
        else:
            self.fail('should raise.')


    def test_changelog_invalid_release_class(self):
        try:
            ChangeLog.parse_changelog('''{
                "releases": {
                    "2023-08-31 0:00": { "external": "invalid release class" }
                },
                "changes": {
                    "2023-08-30 0:00": [ { "valid": "" } ]
                },
                "change types": { "major": [ "valid" ], "minor": [], "patch": [], "internal": [] },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except Exception as e:
            self.assertIsInstance(e, InvalidReleaseClassError)
        else:
            self.fail('should raise.')


    def test_changelog_duplicated_change_type(self):
        try:
            ChangeLog.parse_changelog('''{
                "changes": {},
                "change types": { "major": [ "duplicated" ], "minor": [ "duplicated" ], "patch": [], "internal": [] },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except Exception as e:
            self.assertIsInstance(e, InvalidChangeTypeError)
        else:
            self.fail('should raise.')


    def test_changelog_invalid_change_type(self):
        try:
            ChangeLog.parse_changelog('''{
                "changes": {
                    "2023-08-30 00:00": [
                        { "invalid": "this is invalid." }
                    ]
                },
                "change types": { "major": [ "valid" ], "minor": [], "patch": [], "internal": [] },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except Exception as e:
            self.assertIsInstance(e, InvalidChangeTypeError)
        else:
            self.fail('should raise.')


    def test_changelog_invalid_json_format(self):
        try:
            # , after last element
            ChangeLog.parse_changelog('''{
                "changes": {},
                "change types": { "major": [], "minor": [], "patch": [], "internal": [], },
                "utc offset hours": 9,
                "datetime format": "%Y-%m-%d %H:%M",
            }''')
        except Exception as e:
            self.assertIsInstance(e, InvalidJsonFormatError)
        else:
            self.fail('should raise.')


    def test_changelog_missing_key(self):
        try:
            # , after last element
            ChangeLog.parse_changelog('''{
                "changes": {},
                "change types": { "major": [], "minor": [], "patch": [], "internal": [] },
                "datetime format": "%Y-%m-%d %H:%M"
            }''')
        except Exception as e:
            self.assertIsInstance(e, MissingKeyFormatError)
        else:
            self.fail('should raise.')


    def test_changelog_version_1(self):
        release = Release(datetime.now(), ReleaseClass.PRIVATE)
        internal_change = Change(datetime.now(), ChangeClass.INTERNAL, '', '')
        semantic_version = ChangeGroup(release, [ internal_change ], SemanticVersion(0, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 0)
        self.assertEqual(semantic_version.minor, 0)
        self.assertEqual(semantic_version.patch, 0)


    def test_changelog_version_2(self):
        release = Release(datetime.now(), ReleaseClass.PRIVATE)
        patch_change    = Change(datetime.now(), ChangeClass.PATCH, '', '')
        semantic_version = ChangeGroup(release, [ patch_change ], SemanticVersion(0, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 0)
        self.assertEqual(semantic_version.minor, 0)
        self.assertEqual(semantic_version.patch, 1)


    def test_changelog_version_3(self):
        release = Release(datetime.now(), ReleaseClass.PRIVATE)
        minor_change    = Change(datetime.now(), ChangeClass.MINOR, '', '')
        semantic_version = ChangeGroup(release, [ minor_change ], SemanticVersion(0, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 0)
        self.assertEqual(semantic_version.minor, 1)
        self.assertEqual(semantic_version.patch, 0)


    def test_changelog_version_4(self):
        release = Release(datetime.now(), ReleaseClass.PRIVATE)
        major_change    = Change(datetime.now(), ChangeClass.MAJOR, '', '')
        semantic_version = ChangeGroup(release, [ major_change ], SemanticVersion(0, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 0)
        self.assertEqual(semantic_version.minor, 1)
        self.assertEqual(semantic_version.patch, 0)


    def test_changelog_version_5(self):
        release = Release(datetime.now(), ReleaseClass.PUBLIC)
        major_change    = Change(datetime.now(), ChangeClass.MAJOR, '', '')
        semantic_version = ChangeGroup(release, [ major_change ], SemanticVersion(0, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 1)
        self.assertEqual(semantic_version.minor, 0)
        self.assertEqual(semantic_version.patch, 0)


    def test_changelog_version_6(self):
        release = Release(datetime.now(), ReleaseClass.PRIVATE)
        major_change    = Change(datetime.now(), ChangeClass.MAJOR, '', '')
        semantic_version = ChangeGroup(release, [ major_change ], SemanticVersion(1, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 2)
        self.assertEqual(semantic_version.minor, 0)
        self.assertEqual(semantic_version.patch, 0)


    def test_changelog_version_7(self):
        release = Release(datetime.now(), ReleaseClass.PUBLIC)
        major_change    = Change(datetime.now(), ChangeClass.MAJOR, '', '')
        semantic_version = ChangeGroup(release, [ major_change ], SemanticVersion(1, 0, 0)).semantic_version
        self.assertEqual(semantic_version.major, 2)
        self.assertEqual(semantic_version.minor, 0)
        self.assertEqual(semantic_version.patch, 0)



if __name__ == '__main__':
    unittest.main()