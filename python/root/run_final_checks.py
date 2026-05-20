from finalization_validations import validate_finalization_comprehensive
ok,msg,warnings = validate_finalization_comprehensive()
print('OK:', ok)
print('MSG:', msg)
print('WARNINGS:', warnings)