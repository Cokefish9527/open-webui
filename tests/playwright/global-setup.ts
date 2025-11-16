import { execSync } from 'child_process';
import { resolve } from 'path';

async function globalSetup(): Promise<void> {
  console.log('Running global setup...');
  
  // 确保测试账号已创建
  try {
    const scriptPath = resolve(process.cwd(), 'scripts', 'prepare_test_accounts.py');
    console.log(`Running account preparation script: ${scriptPath}`);
    
    // 执行账号准备脚本
    execSync(`python ${scriptPath}`, {
      cwd: process.cwd(),
      stdio: 'inherit',
      env: {
        ...process.env,
        E2E_TENANT_NAME: process.env.E2E_TENANT_NAME || "福州华商时代自动化测试",
        E2E_TEST_ACCOUNT_PASSWORD: process.env.E2E_TEST_ACCOUNT_PASSWORD || "H@SaiAutoTest2025!"
      }
    });
    
    console.log('Account preparation completed successfully');
  } catch (error) {
    console.warn('Account preparation failed:', error);
    console.warn('Continuing with tests anyway...');
  }
  
  console.log('Global setup completed');
}

export default globalSetup;