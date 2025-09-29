# 测试上下文管理器实现
class TestSessionManager:
    def __enter__(self):
        print("进入上下文管理器")
        self.db = "模拟数据库会话"
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("退出上下文管理器")
        if hasattr(self, 'db'):
            print("关闭数据库会话")

def get_test_session():
    """获取测试会话"""
    return TestSessionManager()

# 测试上下文管理器
print("测试上下文管理器实现:")
try:
    with get_test_session() as db:
        print(f"会话对象: {db}")
    print("测试成功!")
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc()