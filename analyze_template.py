import re
import sys

# Read the file
with open('sales/templates/sales/order_detail.html', 'r') as f:
    lines = f.readlines()

# Track nesting level and analyze
nesting_level = 0
if_stack = []  # Store (line_num, content) of unclosed if blocks

print("Analyzing template file for unclosed if blocks:\n")
print("=" * 80)

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
        print(f"Line {line_num}: IF opened (nesting={nesting_level})")
        print(f"  Content: {original_line[:100]}")
        
    elif elif_match:
        print(f"Line {line_num}: ELIF (nesting={nesting_level})")
        
    elif else_match:
        print(f"Line {line_num}: ELSE (nesting={nesting_level})")
        
    elif endif_match:
        if nesting_level > 0:
            unclosed = if_stack.pop()
            print(f"Line {line_num}: ENDIF (nesting={nesting_level})")
            print(f"  Closes IF from line {unclosed[0]}")
            nesting_level -= 1
        else:
            print(f"Line {line_num}: ERROR - ENDIF without matching IF!")

print("\n" + "=" * 80)
print(f"\nFinal nesting level: {nesting_level}")

if nesting_level > 0:
    print(f"\nUNCLOSED BLOCKS FOUND: {nesting_level} if block(s) not closed")
    print("\nUnclosed if blocks:")
    for line_num, content in if_stack:
        next_line_idx = line_num
        next_content = lines[next_line_idx] if next_line_idx < len(lines) else "EOF"
        print(f"\nLine {line_num}: IF block")
        print(f"  Content: {content[:100]}")
        print(f"  Next line ({line_num + 1}): {next_content.rstrip()[:100]}")
else:
    print("\nAll if blocks are properly closed!")
