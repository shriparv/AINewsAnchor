
def truncate_description(lines, max_chars=4980):
    final_desc = ""
    for line in lines:
        if len(final_desc) + len(line) + 1 > max_chars:
            if not final_desc:
                return line[:max_chars-3] + "..."
            footer = "\n\n...[Content Truncated due to YouTube limits]"
            if len(final_desc) + len(footer) <= max_chars:
                final_desc += footer
            break
        final_desc += line + "\n"
    return final_desc.strip()

# Test Case 1: Short description
lines = ["Heading", "Body line 1", "Body line 2"]
print(f"Test 1 Length: {len(truncate_description(lines, 100))}")
print(truncate_description(lines, 100))

# Test Case 2: Exact limit
lines = ["A" * 50, "B" * 50]
print(f"Test 2 Length: {len(truncate_description(lines, 60))}")
print(truncate_description(lines, 60))

# Test Case 3: Over limit
lines = ["A" * 2000, "B" * 2000, "C" * 2000]
result = truncate_description(lines, 5000)
print(f"Test 3 Length: {len(result)}")
print(f"Contains footer: {'[Content Truncated' in result}")
