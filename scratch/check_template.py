
import re
import sys

def check_template(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tags = re.findall(r'{%\s*(if|elif|else|endif|for|empty|endfor|block|endblock|comment|endcomment|autoescape|endautoescape|filter|endfilter|with|endwith|spaceless|endspaceless|localize|endlocalize|cache|endcache|verbatim|endverbatim|regroup)\s*.*?%}', content)
    
    stack = []
    line_numbers = []
    # Find all tags with line numbers
    all_tags = []
    for m in re.finditer(r'{%\s*(if|elif|else|endif|for|empty|endfor|block|endblock|comment|endcomment|autoescape|endautoescape|filter|endfilter|with|endwith|spaceless|endspaceless|localize|endlocalize|cache|endcache|verbatim|endverbatim|regroup)\s*.*?%}', content):
        line_no = content.count('\n', 0, m.start()) + 1
        all_tags.append((m.group(1), line_no, m.group(0)))

    for tag, line_no, full_tag in all_tags:
        if tag in ['if', 'for', 'block', 'comment', 'autoescape', 'filter', 'with', 'spaceless', 'localize', 'cache', 'verbatim']:
            stack.append((tag, line_no))
        elif tag == 'endif':
            if not stack or stack[-1][0] != 'if':
                print(f"Error: unmatched endif at line {line_no}")
            else:
                stack.pop()
        elif tag == 'endfor':
            if not stack or stack[-1][0] != 'for':
                print(f"Error: unmatched endfor at line {line_no}")
            else:
                stack.pop()
        elif tag == 'endblock':
            if not stack or stack[-1][0] != 'block':
                print(f"Error: unmatched endblock at line {line_no}")
            else:
                stack.pop()
        # Add others as needed
    
    for tag, line_no in stack:
        print(f"Error: unclosed {tag} from line {line_no}")

if __name__ == "__main__":
    check_template(sys.argv[1])
