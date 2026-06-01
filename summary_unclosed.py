import re

# Read the file
with open('sales/templates/sales/order_detail.html', 'r') as f:
    lines = f.readlines()

# Track nesting level and analyze
nesting_level = 0
if_stack = []  # Store (line_num, content) of unclosed if blocks

for line_num, line in enumerate(lines, 1):
    original_line = line.rstrip()
    
    # Check for if blocks
    if_match = re.search(r'{%\s*if\s+', line)
    elif_match = re.search(r'{%\s*elif\s+', line)
    else_match = re.search(r'{%\s*else\s*%}', line)
    endif_match = re.search(r'{%\s*endif\s*%}', line)
    
    if if_match:
        nesting_level += 1
        if_stack.append((line_num, original_line))
        
    elif elif_match:
        pass
        
    elif else_match:
        pass
        
    elif endif_match:
        if nesting_level > 0:
            if_stack.pop()
            nesting_level -= 1

# Generate summary report
print("=" * 100)
print("UNCLOSED IF BLOCKS ANALYSIS REPORT")
print("=" * 100)
print(f"\nTotal unclosed IF blocks: {nesting_level}\n")

if nesting_level > 0:
    print("UNCLOSED IF BLOCKS (ordered by line number):\n")
    for idx, (line_num, content) in enumerate(if_stack, 1):
        print(f"{idx}. Line {line_num}")
        print(f"   Content: {content[:120]}")
        if line_num < len(lines):
            next_line = lines[line_num].rstrip()[:120]
            print(f"   Next line {line_num + 1}: {next_line}")
        print()
