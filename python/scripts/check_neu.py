# MODE: SCRIPT\n\nimport sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import loop_cockpit as lc

cnt = lc.count_tasks_in_file(lc.NEU_MD)
print('NEU task count:', cnt)
print('\nNEU.md content:\n')
print(lc.read_text_file(lc.NEU_MD))