import re

# Read the current file
with open('ai-code-gen-app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the HTML template using regex
pattern = r'HTML_TEMPLATE = r"""(.*?)"""'
match = re.search(pattern, content, re.DOTALL)

if match:
    html_content = match.group(1)
    
    # Replace the entire HTML_TEMPLATE assignment with a file reference
    new_content = content.replace(match.group(0), 'HTML_TEMPLATE_FILE = "template.html"')
    
    # Write the modified Python file
    with open('ai-code-gen-app-new.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    # Write the HTML template to a separate file
    with open('template.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print('HTML extracted successfully')
else:
    print('HTML template not found')