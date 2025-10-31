import json
import re
from collections import defaultdict

def load_openapi_spec(file_path):
    """Load the OpenAPI specification from a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_billing_endpoints(spec):
    """Extract billing-related endpoints from the OpenAPI spec."""
    billing_endpoints = []
    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            # Check if the path or tags contain billing-related terms
            if 'billing' in path.lower() or any('billing' in tag.lower() for tag in details.get('tags', [])) or \
               '计费' in details.get('summary', '') or '计费' in details.get('description', ''):
                endpoint = {
                    'path': path,
                    'method': method.upper(),
                    'summary': details.get('summary', ''),
                    'description': details.get('description', ''),
                    'tags': details.get('tags', []),
                    'operationId': details.get('operationId', '')
                }
                billing_endpoints.append(endpoint)
    return billing_endpoints

def check_chinese_descriptions(endpoints):
    """Check if endpoints have Chinese descriptions."""
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    missing_chinese = []
    
    for endpoint in endpoints:
        # Check if either summary or description contains Chinese characters
        has_chinese = (chinese_pattern.search(endpoint['summary'] or '') or 
                      chinese_pattern.search(endpoint['description'] or ''))
        if not has_chinese:
            missing_chinese.append(endpoint)
    
    return missing_chinese

def check_duplicate_tags(endpoints):
    """Check for duplicate tags in billing endpoints."""
    tag_counts = defaultdict(int)
    for endpoint in endpoints:
        for tag in endpoint['tags']:
            tag_counts[tag] += 1
    
    # Find tags that appear more than once
    duplicate_tags = {tag: count for tag, count in tag_counts.items() if count > 1}
    return duplicate_tags

def generate_billing_report(endpoints):
    """Generate a detailed report for billing APIs."""
    report = "# 计费管理API接口分析报告\n\n"
    
    # Summary
    report += "## 1. 接口概览\n"
    report += f"- 总计费接口数: {len(endpoints)}\n\n"
    
    # Group by tags
    endpoints_by_tag = defaultdict(list)
    for endpoint in endpoints:
        for tag in endpoint['tags']:
            endpoints_by_tag[tag].append(endpoint)
        if not endpoint['tags']:
            endpoints_by_tag['未分类'].append(endpoint)
    
    # List endpoints by tag
    report += "## 2. 接口详情\n\n"
    for tag, tag_endpoints in endpoints_by_tag.items():
        report += f"### {tag}\n\n"
        report += "| 路径 | 方法 | 操作ID | 摘要 |\n"
        report += "|------|------|--------|------|\n"
        
        for endpoint in tag_endpoints:
            summary = endpoint['summary'] if endpoint['summary'] else "（无摘要）"
            report += f"| {endpoint['path']} | {endpoint['method']} | {endpoint['operationId']} | {summary} |\n"
        
        report += "\n"
    
    return report

def main():
    # Load the OpenAPI specification
    spec = load_openapi_spec('openapi.json')
    
    # Extract billing endpoints
    billing_endpoints = extract_billing_endpoints(spec)
    
    # Check for Chinese descriptions
    missing_chinese = check_chinese_descriptions(billing_endpoints)
    
    # Check for duplicate tags
    duplicate_tags = check_duplicate_tags(billing_endpoints)
    
    # Generate report
    report = generate_billing_report(billing_endpoints)
    
    # Save the report
    with open('计费管理API分析报告.md', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print("计费管理API分析报告已生成: 计费管理API分析报告.md")
    
    # Print analysis results
    print("\n=== 计费管理API分析结果 ===")
    
    # Summary
    print(f"1. 总计费接口数: {len(billing_endpoints)}")
    
    # Check for duplicate tags
    if duplicate_tags:
        print("\n2. 重复的标签:")
        for tag, count in duplicate_tags.items():
            print(f"   - {tag}: {count} 个接口")
    else:
        print("\n2. 标签检查: 未发现重复标签")
    
    # Check for endpoints without Chinese descriptions
    if missing_chinese:
        print(f"\n3. 缺少中文描述的接口 ({len(missing_chinese)} 个):")
        for endpoint in missing_chinese:
            print(f"   - {endpoint['method']} {endpoint['path']} ({endpoint['operationId']})")
    else:
        print("\n3. 中文描述检查: 所有计费接口都有中文描述")
    
    # List all billing endpoints
    print(f"\n4. 计费管理接口列表:")
    for endpoint in billing_endpoints:
        tag_str = ", ".join(endpoint['tags']) if endpoint['tags'] else "未分类"
        print(f"   - [{endpoint['method']}] {endpoint['path']} - {endpoint['summary']} (标签: {tag_str})")

if __name__ == "__main__":
    main()