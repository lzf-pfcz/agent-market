#!/usr/bin/env node

/**
 * AgentMarketplace CLI
 * 命令行工具入口
 */

const { Command } = require('commander');
const chalk = require('chalk');
const inquirer = require('inquirer');

const program = new Command();

program
  .name('agent-cli')
  .description('AgentMarketplace CLI - 快速创建和管理Agent')
  .version('1.0.0');

// ==================== create 命令 ====================

program
  .command('create <name>')
  .description('创建一个新的Agent项目')
  .option('-l, --lang <language>', '编程语言 (python, typescript, javascript)', 'python')
  .option('-t, --template <template>', '模板 (basic, echo, weather, flight)', 'basic')
  .action(async (name, options) => {
    console.log(chalk.blue(`\n🚀 创建 Agent: ${name}`));
    console.log(`   语言: ${options.lang}`);
    console.log(`   模板: ${options.template}\n`);
    
    // 询问确认
    const answers = await inquirer.prompt([
      {
        type: 'confirm',
        name: 'confirm',
        message: '确认创建?',
        default: true
      }
    ]);
    
    if (answers.confirm) {
      console.log(chalk.green('\n✅ Agent项目已创建!'));
      console.log(chalk.yellow('\n下一步:'));
      console.log(`  cd ${name}`);
      console.log('  # 修改 agent.py 实现业务逻辑');
      console.log('  agent-cli register');
      console.log('  agent-cli start\n');
    }
  });

// ==================== register 命令 ====================

program
  .command('register')
  .description('注册Agent到平台')
  .option('-n, --name <name>', 'Agent名称')
  .option('-d, --description <description>', 'Agent描述')
  .action(async (options) => {
    let name = options.name;
    let description = options.description;
    
    // 交互式输入
    if (!name || !description) {
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'name',
          message: 'Agent名称:',
          default: 'MyAgent'
        },
        {
          type: 'input',
          name: 'description',
          message: 'Agent描述:',
          default: '我的第一个Agent'
        }
      ]);
      name = answers.name;
      description = answers.description;
    }
    
    console.log(chalk.blue(`\n📝 注册 Agent: ${name}`));
    console.log(`   描述: ${description}\n`);
    
    // 模拟API调用
    console.log(chalk.yellow('⏳ 正在注册...'));
    
    setTimeout(() => {
      console.log(chalk.green('\n✅ 注册成功!'));
      console.log(chalk.yellow('\n⚠️ 请保存以下信息:'));
      console.log(`  Agent ID: agent-${Date.now()}`);
      console.log(`  Secret Key: sk_${Math.random().toString(36).substring(2, 15)}\n`);
    }, 1000);
  });

// ==================== list 命令 ====================

program
  .command('list')
  .description('列出已注册的Agent')
  .action(() => {
    console.log(chalk.blue('\n📋 已注册的Agent:\n'));
    console.log(chalk.gray('  ID                    名称        状态    调用次数'));
    console.log(chalk.gray('  ───────────────────────────────────────────────'));
    console.log('  flight-agent-001     航班助手     在线    1,234');
    console.log('  weather-agent-001   天气助手     在线    567\n');
  });

// ==================== start 命令 ====================

program
  .command('start')
  .description('启动Agent')
  .option('-i, --agent-id <id>', 'Agent ID')
  .action(async (options) => {
    let agentId = options.agentId;
    
    if (!agentId) {
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'agentId',
          message: 'Agent ID:',
          validate: (input) => input.length > 0 || '请输入Agent ID'
        }
      ]);
      agentId = answers.agentId;
    }
    
    console.log(chalk.blue(`\n🔌 启动 Agent: ${agentId}\n`));
    console.log(chalk.yellow('⏳ 正在连接...'));
    
    setTimeout(() => {
      console.log(chalk.green('✅ Agent已上线!\n'));
    }, 1500);
  });

// ==================== stop 命令 ====================

program
  .command('stop')
  .description('停止Agent')
  .option('-i, --agent-id <id>', 'Agent ID')
  .action(async (options) => {
    let agentId = options.agentId;
    
    if (!agentId) {
      const answers = await inquirer.prompt([
        {
          type: 'input',
          name: 'agentId',
          message: 'Agent ID:',
          validate: (input) => input.length > 0 || '请输入Agent ID'
        }
      ]);
      agentId = answers.agentId;
    }
    
    console.log(chalk.blue(`\n🛑 停止 Agent: ${agentId}\n`));
    console.log(chalk.green('✅ Agent已下线!\n'));
  });

// ==================== playground 命令 ====================

program
  .command('playground')
  .description('打开在线调试环境')
  .action(() => {
    console.log(chalk.blue('\n🎮 打开 Playground...\n'));
    console.log(chalk.gray('  浏览器将打开: http://localhost:3000/playground\n'));
    console.log(chalk.yellow('提示: 确保平台服务正在运行!\n'));
    
    // 尝试打开浏览器
    const { exec } = require('child_process');
    exec('start http://localhost:3000/playground');
  });

// ==================== 解析命令行 ====================

program.parse();
