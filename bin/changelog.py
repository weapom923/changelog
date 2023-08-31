import sys

EXIT_STATUS_UNSUPPORTED_PYTHON_VERSION_ERROR = 1
MIN_PYTHON_VERSION_MAJOR = 3
MIN_PYTHON_VERSION_MINOR = 5

if not ((sys.version_info.major >= MIN_PYTHON_VERSION_MAJOR) and (sys.version_info.minor >= MIN_PYTHON_VERSION_MINOR)):
    sys.stderr.write('Python {}.{} or above is required.\n'.format(MIN_PYTHON_VERSION_MAJOR, MIN_PYTHON_VERSION_MINOR))
    exit(EXIT_STATUS_UNSUPPORTED_PYTHON_VERSION_ERROR)

import argparse
import json
from os import path
from enum import Enum, IntEnum
from itertools import chain
from datetime import datetime, timezone, timedelta
from operator import attrgetter
from copy import copy

CMD_INIT = 'init'
CMD_CALC = 'calc'
CMD_PRINT = 'print'

CHANGELOG_KEY_RELEASES = 'releases'
CHANGELOG_KEY_CHANGES = 'changes'
CHANGELOG_KEY_UTC_OFFSET_HOURS = 'utc offset hours'
CHANGELOG_KEY_CHANGE_TYPES = 'change types'
CHANGELOG_KEY_DATETIME_FORMAT = 'datetime format'

DEFAULT_DATETIME_FORMAT = '%Y-%m-%d %H:%M'
DEFAULT_UTC_OFFSET_HOURS = 0

class ArgumentError(Exception): pass
class FormatError(Exception): pass
class MissingKeyFormatError(FormatError): pass
class InvalidDatetimeError(FormatError): pass
class InvalidChangeClassError(FormatError): pass
class InvalidChangeTypeError(FormatError): pass
class InvalidReleaseClassError(FormatError): pass
class InvalidJsonFormatError(FormatError): pass

class ChangeLogAlreadyExistsError(Exception): pass


class Release:
    def __init__(self, release_datetime, release_class, release_comment = None):
        self.datetime = release_datetime
        self.release_class = release_class
        self.comment = release_comment


class ReleaseClass(Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'

    @classmethod
    def get_from_value(klass, value):
        for release_class in klass:
            if value == release_class.value:
                return release_class
        raise InvalidReleaseClassError('unexpected release class {}'.format(value))


class Change:
    def __init__(self, change_datetime, change_class, change_type, change_comment):
        self.datetime = change_datetime
        self.change_class = change_class
        self.change_type = change_type
        self.comment = change_comment


class ChangeGroup:
    def __init__(self, release, changes, previous_semantic_version):
        self.release = release
        self.changes = changes
        self.semantic_version = copy(previous_semantic_version)
        is_major_update_found = False
        is_minor_update_found = False
        is_patch_update_found = False
        for change in changes:
            if change.change_class == ChangeClass.MAJOR:
                is_major_update_found = True
            elif change.change_class == ChangeClass.MINOR:
                is_minor_update_found = True
            elif change.change_class == ChangeClass.PATCH:
                is_patch_update_found = True
        if is_major_update_found:
            if (previous_semantic_version.major == 0) and (release.release_class == ReleaseClass.PRIVATE):
                self.semantic_version.increment_minor()
            else:
                self.semantic_version.increment_major()
        elif is_minor_update_found:
            self.semantic_version.increment_minor()
        elif is_patch_update_found:
            self.semantic_version.increment_patch()


class ChangeClass(Enum):
    MAJOR = 'major'
    MINOR = 'minor'
    PATCH = 'patch'
    INTERNAL = 'internal'

    @classmethod
    def get_from_value(klass, value):
        for change_class in klass:
            if value == change_class.value:
                return change_class
        raise InvalidChangeClassError('unexpected change class {}'.format(value))


class SemanticVersion:
    def __init__(self, major = 0, minor = 0, patch = 0):
        self.major = major
        self.minor = minor
        self.patch = patch
    
    def increment_major(self):
        self.major += 1
        self.minor = 0
        self.patch = 0

    def increment_minor(self):
        self.minor += 1
        self.patch = 0

    def increment_patch(self):
        self.patch += 1

    def __str__(self):
        return '{}.{}.{}'.format(self.major, self.minor, self.patch)


class ChangeLog:
    def __init__(self, releases, changes):
        releases.sort(key=attrgetter('datetime'))
        changes.sort(key=attrgetter('datetime'))

        current_version = SemanticVersion()
        current_release= releases.pop(0)
        current_changes = []
        self.change_groups = []
        for change in changes:
            if change.datetime > current_release.datetime:
                change_group = ChangeGroup(current_release, current_changes, current_version)
                current_release = releases.pop(0)
                current_changes = []
                current_version = change_group.semantic_version
                self.change_groups.insert(0, change_group)
            current_changes.insert(0, change)

        self.change_groups.insert(0, ChangeGroup(current_release, current_changes, current_version))


    def get_latest_version(self):
        return self.change_groups[0].semantic_version


    @classmethod
    def parse_changelog(klass, changelog_string):
        try:
            changelog_data = json.loads(changelog_string)
        except json.JSONDecodeError as e:
            raise InvalidJsonFormatError('invalid changelog format.\n({})',format(e))

        if CHANGELOG_KEY_DATETIME_FORMAT not in changelog_data:
            datetime_format = DEFAULT_DATETIME_FORMAT
        else:
            datetime_format = changelog_data[CHANGELOG_KEY_DATETIME_FORMAT]

        if CHANGELOG_KEY_UTC_OFFSET_HOURS not in changelog_data:
            raise MissingKeyFormatError('key {} is required.'.format(CHANGELOG_KEY_UTC_OFFSET_HOURS))

        change_timezone = timezone(timedelta(hours=changelog_data[CHANGELOG_KEY_UTC_OFFSET_HOURS]))

        releases = []
        releases.append(Release(datetime.max.replace(tzinfo=change_timezone), ReleaseClass.PRIVATE))
        if CHANGELOG_KEY_RELEASES in changelog_data:
            for release_datetime_string in changelog_data[CHANGELOG_KEY_RELEASES].keys():
                assert isinstance(release_datetime_string, str)
                try:
                    datetime.strptime(release_datetime_string, datetime_format).replace(tzinfo=change_timezone)
                except ValueError as e:
                    raise InvalidDatetimeError('release datetime "{}" is invalid.\n({})'.format(release_datetime_string, e))
            for release_datetime_string, release_definition in changelog_data[CHANGELOG_KEY_RELEASES].items():
                release_datetime = datetime.strptime(release_datetime_string, datetime_format).replace(tzinfo=change_timezone)
                release_class_value, release_comment = next(iter(release_definition.items()))
                release_class = ReleaseClass.get_from_value(release_class_value)
                releases.append(Release(release_datetime, release_class, release_comment))

        if CHANGELOG_KEY_CHANGE_TYPES not in changelog_data:
            raise MissingKeyFormatError('key {} is required.'.format(CHANGELOG_KEY_CHANGE_TYPES))

        change_type_definitions = changelog_data[CHANGELOG_KEY_CHANGE_TYPES]
        change_class_values = set(change_type_definitions.keys())
        valid_class_values = set([ change_class.value for change_class in ChangeClass ])
        change_types = list(chain.from_iterable(change_type_definitions.values()))
        if len(change_types) != len(set(change_types)):
            raise InvalidChangeTypeError('change type is duplicated')

        if change_class_values != valid_class_values:
            raise InvalidChangeClassError('change classes should be {}'.format(', '.join(valid_class_values)))

        changes = []
        for change_datetime_string, change_definitions in changelog_data[CHANGELOG_KEY_CHANGES].items():
            assert isinstance(change_datetime_string, str)
            try:
                change_datetime = datetime.strptime(change_datetime_string, datetime_format).replace(tzinfo=change_timezone)
            except ValueError as e:
                raise InvalidDatetimeError('change datetime "{}" is invalid.\n({})'.format(change_datetime_string, e))

            for change_definition in change_definitions:
                change_type, change_comment = next(iter(change_definition.items()))
                found_change_class = None
                for change_class_value, change_types in change_type_definitions.items():
                    if change_type in change_types:
                        found_change_class = ChangeClass.get_from_value(change_class_value)
                        break
                if found_change_class is None:
                    raise InvalidChangeTypeError('change type "{}" is invalid.'.format(change_type))

                changes.append(Change(change_datetime, found_change_class, change_type, change_comment))

        return klass(releases, changes)

    @classmethod
    def generate_initial_changelog_data(klass, utc_offset_hours):
        return {
            CHANGELOG_KEY_CHANGES: {
                datetime.now(timezone.utc).strftime(DEFAULT_DATETIME_FORMAT): [
                    {
                        'others': 'changelog is generated.',
                    },
                ],
            },
            CHANGELOG_KEY_CHANGE_TYPES: {
                ChangeClass.MAJOR.value: [
                    'specification change',
                    '!!!forced major update',
                ],
                ChangeClass.MINOR.value: [
                    'new feature',
                    '!!!forced minor update',
                ],
                ChangeClass.PATCH.value: [
                    'bug fix',
                    'performance improvement',
                    '!!!forced patch update',
                ],
                ChangeClass.INTERNAL.value: [
                    'refactoring',
                    'others',
                ]
            },
            CHANGELOG_KEY_UTC_OFFSET_HOURS: utc_offset_hours,
            CHANGELOG_KEY_DATETIME_FORMAT: DEFAULT_DATETIME_FORMAT,
        }

    @classmethod
    def initialize_changelog(klass, changelog_file_path, utc_offset_hours):
        if path.exists(changelog_file_path):
            raise ChangeLogAlreadyExistsError('{} already exists.'.format(changelog_file_path))
        else:
            changelog_data = klass.generate_initial_changelog_data(utc_offset_hours)
            with open(changelog_file_path, mode='wt') as fd:
                json.dump(changelog_data, fd, indent=2)

    def print_changelog(self):
        for change_group in self.change_groups:
            sys.stdout.write('{} ({})\n'.format(change_group.semantic_version, change_group.release.datetime.isoformat()))
            for change in change_group.changes:
                sys.stdout.write('- {}: [{}] {}\n'.format(change.datetime.isoformat(), change.change_type, change.comment))

    def print_latest_version(self):
        sys.stdout.write('{}\n'.format(self.get_latest_version()))


class ExitStatus(IntEnum):
    SUCCESS = 0
    UNSUPPORTED_PYTHON_VERSION_ERROR = EXIT_STATUS_UNSUPPORTED_PYTHON_VERSION_ERROR
    FORMAT_ERROR = 2
    CHANGELOG_ALREADY_EXISTS_ERROR = 3
    ARGUMENT_ERROR = 4
    UNEXPECTED_ERROR = 99



if __name__ == '__main__':
    try:
        parser = argparse.ArgumentParser(description='changelog loader')
        subparsers = parser.add_subparsers()

        init_command_parser = subparsers.add_parser(CMD_INIT, help='{} -h'.format(CMD_INIT))
        init_command_parser.set_defaults(command=CMD_INIT)
        init_command_parser.add_argument(
            '-u', '--utc_time_offset',
            type=int,
            help='UTC time offset in hours',
            default=DEFAULT_UTC_OFFSET_HOURS,
        )

        calc_command_parser = subparsers.add_parser(CMD_CALC, help='{} -h'.format(CMD_CALC))
        calc_command_parser.set_defaults(command=CMD_CALC)

        print_command_parser = subparsers.add_parser(CMD_PRINT, help='{} -h'.format(CMD_PRINT))
        print_command_parser.set_defaults(command=CMD_PRINT)

        for subparser in [ init_command_parser, calc_command_parser, print_command_parser ]:
            subparser.add_argument(
                '-f', '--file',
                type=str,
                help='file path of changelog',
                default='changelog.json',
            )

        args = parser.parse_args()
        if not hasattr(args, 'command'):
            raise ArgumentError('command is required.')

        command = args.command
        if args.command == CMD_INIT:
            ChangeLog.initialize_changelog(args.file, args.utc_time_offset)
        else:
            with open(args.file, mode='rt') as fd:
                changelog_string = fd.read()
            changelog = ChangeLog.parse_changelog(changelog_string)
            if args.command == CMD_CALC:
                changelog.print_latest_version()
            elif args.command == CMD_PRINT:
                changelog.print_changelog()

        exit(ExitStatus.SUCCESS.value)

    except json.JSONDecodeError as e:
        sys.stderr.write('{}\n'.format(e))
        exit(ExitStatus.FORMAT_ERROR.value)
    
    except ChangeLogAlreadyExistsError as e:
        sys.stderr.write('{}\n'.format(e))
        exit(ExitStatus.CHANGELOG_ALREADY_EXISTS_ERROR.value)

    except argparse.ArgumentError as e:
        raise ArgumentError(str(e))

    except ArgumentError as e:
        sys.stderr.write('{}\n'.format(e))
        parser.print_help(file=sys.stderr)
        exit(ExitStatus.ARGUMENT_ERROR.value)

    except Exception as e:
        sys.stderr.write('{}\n'.format(e))
        exit(ExitStatus.UNEXPECTED_ERROR.value)
