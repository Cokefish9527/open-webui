import json
import re
from collections import defaultdict


def load_openapi_spec(file_path):
    """Load the OpenAPI specification from a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_endpoints(spec):
    """Extract all endpoints from the OpenAPI spec."""
    endpoints = []
    for path, methods in spec.get('paths', {}).items():
        for method, details in methods.items():
            endpoint = {
                'path': path,
                'method': method.upper(),
                'summary': details.get('summary', ''),
                'description': details.get('description', ''),
                'tags': details.get('tags', []),
                'operationId': details.get('operationId', '')
            }
            endpoints.append(endpoint)
    return endpoints


def analyze_endpoints(endpoints):
    """Analyze endpoints for the tasks."""
    # 1. Check for duplicate tags
    tag_counts = defaultdict(int)
    for endpoint in endpoints:
        for tag in endpoint['tags']:
            tag_counts[tag] += 1

    duplicate_tags = {tag: count for tag, count in tag_counts.items() if count > 1}

    # 2. Check for Chinese descriptions
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    endpoints_without_chinese = []
    for endpoint in endpoints:
        if not chinese_pattern.search(endpoint['summary']) and not chinese_pattern.search(endpoint['description']):
            endpoints_without_chinese.append(endpoint)

    # 3. Group endpoints by tags
    endpoints_by_tag = defaultdict(list)
    for endpoint in endpoints:
        for tag in endpoint['tags']:
            endpoints_by_tag[tag].append(endpoint)
        if not endpoint['tags']:
            endpoints_by_tag['untagged'].append(endpoint)

    return {
        'duplicate_tags': duplicate_tags,
        'endpoints_without_chinese': endpoints_without_chinese,
        'endpoints_by_tag': dict(endpoints_by_tag)
    }


def generate_markdown_report(endpoints, analysis):
    """生成 API 接口清单（按标签分组）。"""
    report = "# API接口清单\n\n"

    # Group endpoints by tags
    endpoints_by_tag = defaultdict(list)
    for endpoint in endpoints:
        for tag in endpoint['tags']:
            endpoints_by_tag[tag].append(endpoint)
        if not endpoint['tags']:
            endpoints_by_tag['untagged'].append(endpoint)

    # Generate report for each tag
    for tag, tag_endpoints in endpoints_by_tag.items():
        report += f"## {tag if tag != 'untagged' else '未分类'}\n\n"
        report += "| 路径 | 方法 | 操作ID | 摘要 | 描述 |\n"
        report += "|------|------|--------|------|------|\n"

        for endpoint in tag_endpoints:
            summary = endpoint['summary'] if endpoint['summary'] else "摘要缺失"
            description = endpoint['description'] if endpoint['description'] else "暂无描述"
            report += f"| {endpoint['path']} | {endpoint['method']} | {endpoint['operationId']} | {summary} | {description} |\n"

        report += "\n"

    return report


def main():
    # Load the OpenAPI specification
    spec = load_openapi_spec('openapi.json')

    # Extract endpoints
    endpoints = extract_endpoints(spec)

    # Analyze endpoints
    analysis = analyze_endpoints(endpoints)

    # Generate markdown report
    report = generate_markdown_report(endpoints, analysis)

    # Save the report
    with open('API接口清单.md', 'w', encoding='utf-8') as f:
        f.write(report)

    print("API接口清单已生成: API接口清单.md")

    # Print analysis results
    print("\n=== 分析结果 ===")

    # Check for duplicate tags
    if analysis['duplicate_tags']:
        print("\n1. 重复的标签:")
        for tag, count in analysis['duplicate_tags'].items():
            print(f"   - {tag}: {count} 个接口")
    else:
        print("\n1. 标签检查: 未发现重复标签")

    # Check for endpoints without Chinese descriptions
    if analysis['endpoints_without_chinese']:
        print(f"\n2. 缺少中文摘要/描述的接口 ({len(analysis['endpoints_without_chinese'])} 个):")
        for endpoint in analysis['endpoints_without_chinese'][:10]:  # Show first 10
            print(f"   - {endpoint['method']} {endpoint['path']} ({endpoint['operationId']})")
        if len(analysis['endpoints_without_chinese']) > 10:
            print(f"   ... 其余 {len(analysis['endpoints_without_chinese']) - 10} 个接口")
    else:
        print("\n2. 中文描述检查: 全部接口均包含中文")

    # Summary statistics
    print(f"\n3. 接口统计:")
    print(f"   - 总接口数: {len(endpoints)}")
    print(f"   - 标签数: {len(analysis['endpoints_by_tag'])}")

    for tag, tag_endpoints in analysis['endpoints_by_tag'].items():
        tag_name = tag if tag != 'untagged' else '未分类'
        print(f"   - {tag_name}: {len(tag_endpoints)} 个接口")


if __name__ == "__main__":
    main()

