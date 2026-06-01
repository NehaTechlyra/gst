import re

# Read the file
with open('sales/templates/sales/order_detail.html', 'r') as f:
    lines = f.readlines()

# Track nesting level and analyze - proper handling of multiple tags per line
nesting_level = 0
if_stack = []

print("Analyzing template file for unclosed if blocks (handling multiple tags per line):\n")
print("=" * 100)

for line_num, line in enumerate(lines, 1):
    original_line = line.rstrip()
    
    # Count all opening ifs, elifs, and endifs on this line
    if_count = len(re.findall(r'{%\s*if\s+', line))
    elif_count = len(re.findall(r'{%\s*elif\s+', line))
    else_count = len(re.findall(r'{%\s*else\s*%}', line))
    endif_count = len(re.findall(r'{%\s*endif\s*%}', line))
    
    if if_count > 0 or endif_count > 0:
        old_level = nesting_level
        # Process if tags
        for i in range(if_count):
            nesting_level += 1
            if_stack.append((line_num, original_line))
        
        # Process endif tags
        for i in range(endif_count):
            if nesting_level > 0:
                if_stack.pop()
                nesting_level -= 1
        
        if old_level != nesting_level or if_count > 0 or endif_count > 0:
            action = ""
            if if_count > 0:
                action += f"IF(x{if_count}) "
            if endif_count > 0:
                action += f"ENDIF(x{endif_count}) "
            print(f"Line {line_num}: {action}(nesting {old_level}->{nesting_level})")
            print(f"  Content: {original_line[:100]}")

print("\n" + "=" * 100)
print(f"\nFinal nesting level: {nesting_level}")

if nesting_level > 0:
    print(f"\nUNCLOSED BLOCKS FOUND: {nesting_level} if block(s) not closed")
    print("\nUnclosed if blocks (in order of appearance):")
    for idx, (line_num, content) in enumerate(if_stack, 1):
        print(f"\n{idx}. Line {line_num}")
        print(f"   Content: {content[:120]}")
else:
    print("\nAll if blocks are properly closed!")
