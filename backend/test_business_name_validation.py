import sys
import os

# 添加项目路径到sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from open_webui.utils.n8n_client import ExecutionRequest

def test_business_name_validation():
    """测试business_name字段验证"""
    
    # 测试1: business_name存在的情况
    print("测试1: business_name存在的情况")
    try:
        request_with_business = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message",
            business_name="test_business"
        )
        payload = request_with_business.to_webhook_payload()
        print("✅ 成功生成payload:", payload)
        assert "business_name" in payload
        assert payload["business_name"] == "test_business"
        print("✅ business_name字段正确包含在payload中")
    except Exception as e:
        print("❌ 错误:", e)
        return False
    
    # 测试2: business_name为None的情况
    print("\n测试2: business_name为None的情况")
    try:
        request_without_business = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message",
            business_name=None
        )
        payload = request_without_business.to_webhook_payload()
        print("❌ 应该抛出异常但没有抛出")
        return False
    except ValueError as e:
        print("✅ 正确抛出ValueError异常:", e)
    except Exception as e:
        print("❌ 抛出了错误的异常类型:", e)
        return False
    
    # 测试3: business_name为空字符串的情况
    print("\n测试3: business_name为空字符串的情况")
    try:
        request_empty_business = ExecutionRequest(
            workflow_id="test_workflow",
            session_id="test_session",
            user_id="test_user",
            message="test_message",
            business_name=""
        )
        payload = request_empty_business.to_webhook_payload()
        print("❌ 应该抛出异常但没有抛出")
        return False
    except ValueError as e:
        print("✅ 正确抛出ValueError异常:", e)
    except Exception as e:
        print("❌ 抛出了错误的异常类型:", e)
        return False
        
    print("\n🎉 所有测试通过!")
    return True

if __name__ == "__main__":
    test_business_name_validation()