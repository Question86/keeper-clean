# MODE: SCRIPT\n\nimport json
import os
import sys

# Guard: refuse to proceed if repository is locked due to an incident
if os.path.exists('docs/LOCKED_BY_INCIDENT.md'):
    print('ERROR: Repository locked by INCIDENT_0001. Resolve incident and remove docs/LOCKED_BY_INCIDENT.md to proceed.')
    sys.exit(7)


def main():
    cj = 'current.json'
    try:
        with open(cj, 'r', encoding='utf-8') as fh:
            data = json.load(fh)
    except Exception as e:
        print('ERROR: failed to read current.json ->', e)
        return 2

    tr = data.get('TASK_REGISTER')
    if not tr:
        print('ERROR: TASK_REGISTER not found in current.json')
        return 3

    path = tr.get('path')
    print('TASK_REGISTER.path:', path)
    if not path:
        print('ERROR: TASK_REGISTER.path is empty')
        return 4

    exists = os.path.exists(path)
    print('exists:', exists)
    if not exists:
        print('ERROR: path does not exist:', path)
        return 5

    print('\n--- beginning of file:', path, '---')
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            for i, line in enumerate(fh):
                if i >= 40:
                    break
                print(line.rstrip())
    except Exception as e:
        print('ERROR: failed to open file ->', e)
        return 6

    print('--- end preview ---')
    return 0


if __name__ == '__main__':
    sys.exit(main())
