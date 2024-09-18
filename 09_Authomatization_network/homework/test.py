import os
path = 'httptest/dir2/page.htmlarg1=value&arg2'
# print(os.path.normpath(path.lstrip('?')))
# if '?' in path:
path, query = path.split('?', maxsplit=1)

print(path)