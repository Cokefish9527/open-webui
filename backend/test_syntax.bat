@echo off
setlocal enabledelayedexpansion

echo ========================================
echo 批处理脚本语法测试
echo ========================================

:: 测试选择逻辑
set /p CHOICE="请输入选择 (1-6): "

if "%CHOICE%"=="1" (
    echo 选择1: 完整工作流测试
) else if "%CHOICE%"=="2" (
    echo 选择2: 简单快速测试
) else if "%CHOICE%"=="3" (
    echo 选择3: 回收站完整测试
) else if "%CHOICE%"=="4" (
    echo 选择4: 回收站修复验证
) else if "%CHOICE%"=="5" (
    echo 选择5: 删除目录专项测试
) else if "%CHOICE%"=="6" (
    echo 选择6: 退出
) else (
    echo 无效选择
)

echo 测试完成
pause