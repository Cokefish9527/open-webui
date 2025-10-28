// runner.js
const fastify = require('fastify')({ logger: true });
const path = require('path');

// 1) 注册可用工具列表
const tools = [
  { name: 'tiktok_login', script: './tiktok_login.js' },
  { name: 'tiktok_fetch_creator', script: './tiktok_fetch_creator.js' },
  { name: 'tiktok_fetch_video', script: './tiktok_fetch_video.js' },
  { name: 'tiktok_publish_video', script: './tiktok_publish_video.js' }
];

fastify.get('/health', async () => ({ status: true }));
fastify.get('/tools', async () => ({ status: 'ok', data: tools.map(t => t.name) }));

fastify.post('/execute', async (request, reply) => {
  const { tool, arguments: rawArgs = {}, metadata: reqMetadata = {} } = request.body || {};
  const entry = tools.find(t => t.name === tool);
  if (!entry) {
    reply.code(400);
    return { status: 'error', message: `tool ${tool} not registered` };
  }

  try {
    const script = require(path.resolve(__dirname, entry.script));
    const handler =
      (typeof script === 'function' && script) ||
      script.run ||
      script.execute ||
      script.default;

    if (typeof handler !== 'function') {
      throw new TypeError(`Script ${entry.script} 未导出 run/execute 函数`);
    }

    const payload = {
      ...(typeof rawArgs === 'object' && rawArgs !== null ? rawArgs : {}),
      arguments:
        typeof rawArgs?.arguments === 'object' && rawArgs.arguments !== null
          ? rawArgs.arguments
          : {},
      metadata: {
        ...(rawArgs?.metadata || {}),
        ...(reqMetadata || {})
      }
    };

    const result = await handler(payload);

    // Runner 约定返回带有 status 的对象
    return result && typeof result === 'object'
      ? result
      : { status: 'ok', artifacts: result };
  } catch (error) {
    request.log.error(error, 'runner-execute-failed');
    reply.code(500);
    return {
      status: 'error',
      message: error.message,
      stack: process.env.NODE_ENV === 'development' ? error.stack : undefined
    };
  }
});

const PORT = process.env.PORT || 8081;
const HOST = process.env.HOST || '0.0.0.0';

fastify.listen({ host: HOST, port: PORT })
  .then(() => console.log(`Playwright MCP Runner listening on ${HOST}:${PORT}`))
  .catch(err => {
    fastify.log.error(err);
    process.exit(1);
  });
