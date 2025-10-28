<script lang="ts">
  import { onMount } from 'svelte';
  import { toast } from 'svelte-sonner';
  import {
    listSocialAccounts,
    createSocialAccount,
    prepareSocialAccount,
    listSocialPosts,
    createSocialPost,
    publishSocialPost,
    type SocialAccount,
    type SocialPost,
    type MCPExecutionResponse
  } from '$lib/apis/social';

  const STEPS = [
    {
      id: 0,
      title: '绑定账号',
      description: '填写基础信息，系统自动创建 Playwright 凭证模板与浏览器配置目录。'
    },
    {
      id: 1,
      title: '完成登录',
      description: '通过交互式向导或自动凭证完成登录，确保账号处于可用状态。'
    },
    {
      id: 2,
      title: '首次发布',
      description: '上传视频并填写文案，立即触发一次示例发布以验证流程。'
    }
  ];

  interface WizardAccountForm {
    platform: string;
    handle: string;
    display_name?: string;
    vpn_profile_id?: string;
    auto_prepare: boolean;
  }

  interface PreparePayload {
    interactive?: boolean;
    interactive_timeout?: number;
  }

  interface PublishDraft {
    title: string;
    caption: string;
    video_path: string;
    hashtags: string;
  }

  let currentStep = 0;
  let loadingAccounts = false;
  let loadingPosts = false;
  let processing = false;
  let infoMessage: string | null = null;
  let errorMessage: string | null = null;

  let accounts: SocialAccount[] = [];
  let recentPosts: SocialPost[] = [];
  let createdAccount: SocialAccount | null = null;
  let selectedAccountId = '';
  let latestPost: SocialPost | null = null;

  let accountForm: WizardAccountForm = {
    platform: 'tiktok',
    handle: '',
    display_name: '',
    vpn_profile_id: '',
    auto_prepare: true
  };

  let publishDraft: PublishDraft = {
    title: '',
    caption: '',
    video_path: '',
    hashtags: ''
  };

  $: selectedAccount = accounts.find((acc) => acc.id === selectedAccountId) || null;

  function accountStatusClass(status: string): string {
    if (status === 'active') {
      return 'inline-flex items-center rounded-full bg-success-100 px-2 py-0.5 text-xs font-medium text-success-700';
    }
    if (status === 'suspended') {
      return 'inline-flex items-center rounded-full bg-error-100 px-2 py-0.5 text-xs font-medium text-error-700';
    }
    return 'inline-flex items-center rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700';
  }

  function postStatusClass(status: string): string {
    if (status === 'published') {
      return 'inline-flex items-center rounded-full bg-success-100 px-2 py-0.5 text-xs font-medium text-success-700';
    }
    if (status === 'failed') {
      return 'inline-flex items-center rounded-full bg-error-100 px-2 py-0.5 text-xs font-medium text-error-700';
    }
    return 'inline-flex items-center rounded-full bg-primary-100 px-2 py-0.5 text-xs font-medium text-primary-700';
  }

  function resetMessages() {
    infoMessage = null;
    errorMessage = null;
  }

  async function ensureToken(): Promise<string> {
    const token = localStorage.getItem('token');
    if (!token) {
      toast.error('未检测到登录凭证，请重新登录后再试。');
      throw new Error('NO_TOKEN');
    }
    return token;
  }

  async function loadExisting() {
    try {
      const token = await ensureToken();
      loadingAccounts = true;
      loadingPosts = true;
      accounts = await listSocialAccounts(token);
      if (!selectedAccountId && accounts.length > 0) {
        selectedAccountId = accounts[0].id;
      }
      recentPosts = await listSocialPosts(token);
    } catch (error) {
      const message = (error as any)?.detail ?? (error as any)?.message ?? '加载数据失败';
      toast.error(message);
    } finally {
      loadingAccounts = false;
      loadingPosts = false;
    }
  }

  function resetAccountForm() {
    accountForm = {
      platform: 'tiktok',
      handle: '',
      display_name: '',
      vpn_profile_id: '',
      auto_prepare: true
    };
  }

  async function createAccount() {
    resetMessages();
    if (!accountForm.handle.trim()) {
      errorMessage = '请输入账号 Handle。';
      return;
    }

    try {
      processing = true;
      const token = await ensureToken();
      const payload = {
        platform: accountForm.platform,
        handle: accountForm.handle.trim(),
        display_name: accountForm.display_name?.trim() || undefined,
        vpn_profile_id: accountForm.vpn_profile_id?.trim() || undefined,
        auto_prepare: accountForm.auto_prepare
      };

      const result = await createSocialAccount(token, payload);
      createdAccount = result;
      selectedAccountId = result.id;
      latestPost = null;
      infoMessage = `账号 "${result.handle}" 已创建，凭证模板与浏览器目录已初始化。`;
      resetAccountForm();
      currentStep = 1;
      await loadExisting();

      if (payload.auto_prepare) {
        await launchInteractiveLogin(true);
      }
    } catch (error) {
      const message = (error as any)?.detail ?? (error as any)?.message ?? '创建账号失败';
      errorMessage = message;
    } finally {
      processing = false;
    }
  }

  async function launchInteractiveLogin(interactive: boolean) {
    resetMessages();
    if (!selectedAccount) {
      errorMessage = '请先创建或选择一个账号。';
      return;
    }

    try {
      processing = true;
      const token = await ensureToken();
      const payload: PreparePayload = {
        interactive,
        interactive_timeout: 300000
      };
      const res: MCPExecutionResponse = await prepareSocialAccount(token, selectedAccount.id, payload);
      await loadExisting();
      infoMessage = res.message ?? (interactive ? '请在浏览器中完成授权后返回本页。' : '已尝试自动登录，请在运行记录中确认结果。');
    } catch (error) {
      const message = (error as any)?.detail ?? (error as any)?.message ?? '触发登录流程失败';
      errorMessage = message;
    } finally {
      processing = false;
    }
  }

  async function createAndPublish() {
    resetMessages();
    if (!selectedAccount) {
      errorMessage = '请先创建或选择一个账号。';
      return;
    }
    if (!publishDraft.video_path.trim()) {
      errorMessage = '请填写视频文件路径。';
      return;
    }

    try {
      processing = true;
      const token = await ensureToken();
      const postPayload = {
        account_id: selectedAccount.id,
        title: publishDraft.title?.trim() || undefined,
        caption: publishDraft.caption?.trim() || undefined,
        media_assets: { video: publishDraft.video_path.trim() },
        metadata: publishDraft.hashtags
          ? {
              hashtags: publishDraft.hashtags
                .split(',')
                .map((tag) => tag.trim())
                .filter(Boolean)
            }
          : undefined
      };

      const post = await createSocialPost(token, postPayload);
      latestPost = post;
      const res = await publishSocialPost(token, post.id);
      infoMessage = res?.result?.message ?? '已触发发布流程，可在运行记录中查看状态。';
      currentStep = 2;
      await loadExisting();
    } catch (error) {
      const message = (error as any)?.detail ?? (error as any)?.message ?? '创建/发布任务失败';
      errorMessage = message;
    } finally {
      processing = false;
    }
  }

  function selectAccount(id: string) {
    selectedAccountId = id;
    createdAccount = accounts.find((acc) => acc.id === id) ?? null;
    resetMessages();
  }

  onMount(() => {
    loadExisting();
  });
</script>

<svelte:head>
  <title>社交账号自动化 · 智能向导</title>
</svelte:head>

<div class="mx-auto max-w-6xl px-6 py-10 space-y-10">
  <header class="space-y-2">
    <h1 class="text-3xl font-semibold text-base-900 dark:text-base-100">社交账号自动化向导</h1>
    <p class="text-base text-base-500 dark:text-base-400">
      帮助你在几分钟内完成账号绑定、登录验证与首次发布。系统会自动生成 Playwright 凭证模板及浏览器配置目录，并提供交互式登录引导。
    </p>
  </header>

  <section class="bg-base-100 dark:bg-base-900 border border-base-200 dark:border-base-800 rounded-xl shadow-sm">
    <ol class="sm:flex sm:divide-x divide-base-200 dark:divide-base-800">
      {#each STEPS as step}
        <li class="flex-1">
          <button
            class="w-full px-4 py-5 text-left transition hover:bg-base-50 dark:hover:bg-base-900/70"
            class:text-primary-600={currentStep === step.id}
            on:click={() => (currentStep = step.id)}
          >
            <div class="text-sm font-medium uppercase tracking-wide">{`Step ${step.id + 1}`}</div>
            <div class="mt-1 text-lg font-semibold">{step.title}</div>
            <p class="mt-1 text-sm text-base-500 dark:text-base-400">{step.description}</p>
          </button>
        </li>
      {/each}
    </ol>
  </section>

  {#if errorMessage}
    <div class="rounded-lg border border-error-200 bg-error-50 px-4 py-3 text-error-700">{errorMessage}</div>
  {/if}

  {#if infoMessage}
    <div class="rounded-lg border border-primary-200 bg-primary-50 px-4 py-3 text-primary-700">{infoMessage}</div>
  {/if}

  <div class="grid gap-8 lg:grid-cols-[2fr,1fr]">
    <section class="space-y-10">
      {#if currentStep === 0}
        <div class="space-y-6">
          <h2 class="text-2xl font-semibold text-base-900 dark:text-base-100">① 填写账号信息</h2>
          <p class="text-base text-base-500 dark:text-base-400">
            仅需提供账号基础信息，系统会自动生成凭证模板与浏览器配置目录。创建完成后可立即进入交互式登录步骤。
          </p>

          <form
            class="grid gap-5 max-w-3xl bg-base-100 dark:bg-base-900 border border-base-200 dark:border-base-800 rounded-xl p-6"
            on:submit|preventDefault={createAccount}
          >
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="text-sm font-medium text-base-600 dark:text-base-300">平台</label>
                <input class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2" value={accountForm.platform} readonly />
              </div>
              <div>
                <label class="text-sm font-medium text-base-600 dark:text-base-300">账号 Handle *</label>
                <input
                  class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                  placeholder="例如 tiktok_official"
                  bind:value={accountForm.handle}
                  required
                />
              </div>
            </div>

            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="text-sm font-medium text-base-600 dark:text-base-300">账号昵称</label>
                <input
                  class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                  placeholder="用于后台展示，可选"
                  bind:value={accountForm.display_name}
                />
              </div>
              <div>
                <label class="text-sm font-medium text-base-600 dark:text-base-300">VPN 配置 ID</label>
                <input
                  class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                  placeholder="对应代理配置文件名，可选"
                  bind:value={accountForm.vpn_profile_id}
                />
              </div>
            </div>

            <label class="flex items-center gap-3 rounded-lg border border-base-300 dark:border-base-700 bg-base-50 dark:bg-base-900 px-4 py-3">
              <input type="checkbox" bind:checked={accountForm.auto_prepare} />
              <div>
                <div class="text-sm font-semibold">创建后立即提示登录</div>
                <p class="text-xs text-base-500 dark:text-base-400">勾选后账号创建成功会自动启动交互式登录流程。</p>
              </div>
            </label>

            <div class="flex gap-3">
              <button
                class="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60"
                type="submit"
                disabled={processing}
              >
                {processing ? '创建中...' : '创建账号'}
              </button>
              <button
                type="button"
                class="inline-flex items-center justify-center rounded-lg border border-base-300 dark:border-base-700 px-4 py-2 text-sm font-medium text-base-600 dark:text-base-200 hover:bg-base-50 dark:hover:bg-base-900"
                on:click={resetAccountForm}
                disabled={processing}
              >
                重置表单
              </button>
            </div>
          </form>
        </div>
      {/if}

      {#if currentStep === 1}
        <div class="space-y-6">
          <h2 class="text-2xl font-semibold text-base-900 dark:text-base-100">② 登录与验证</h2>
          <p class="text-base text-base-500 dark:text-base-400">
            选择要验证的账号，可选择交互式登录（推荐）或自动登录。交互式登录会打开浏览器等待你完成短信、验证码等操作。
          </p>

          <div class="space-y-3">
            <label class="text-sm font-medium text-base-600 dark:text-base-300">选择账号</label>
            <select
              bind:value={selectedAccountId}
              class="w-full max-w-md rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
            >
              <option value="" disabled>请选择账号</option>
              {#each accounts as acc}
                <option value={acc.id}>{acc.handle} · {acc.status}</option>
              {/each}
            </select>
          </div>

          {#if selectedAccount}
            <div class="grid gap-4 md:grid-cols-2">
              <div class="rounded-xl border border-base-200 dark:border-base-800 bg-base-100 dark:bg-base-900 p-6 space-y-3">
                <h3 class="text-lg font-semibold">交互式登录（推荐）</h3>
                <p class="text-sm text-base-500 dark:text-base-400">
                  Runner 会打开 TikTok 登录页面，请在弹出的浏览器窗口中完成登录。完成后脚本将自动保存 Cookie 并更新账号状态。
                </p>
                <button
                  class="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 disabled:opacity-60"
                  on:click={() => launchInteractiveLogin(true)}
                  disabled={processing}
                >
                  {processing ? '等待完成...' : '打开登录向导'}
                </button>
              </div>

              <div class="rounded-xl border border-base-200 dark:border-base-800 bg-base-100 dark:bg-base-900 p-6 space-y-3">
                <h3 class="text-lg font-semibold">自动登录</h3>
                <p class="text-sm text-base-500 dark:text-base-400">
                  前提：凭证模板中已经填写用户名 / 密码。脚本将尝试自动提交表单并更新 Cookie。
                </p>
                <button
                  class="inline-flex items-center justify-center rounded-lg border border-base-300 dark:border-base-700 px-4 py-2 text-sm font-medium text-base-600 dark:text-base-200 hover:bg-base-50 dark:hover:bg-base-900 disabled:opacity-60"
                  on:click={() => launchInteractiveLogin(false)}
                  disabled={processing}
                >
                  {processing ? '执行中...' : '尝试自动登录'}
                </button>
              </div>
            </div>

            <div class="rounded-xl border border-base-200 dark:border-base-800 bg-base-50 dark:bg-base-900 px-4 py-3 text-sm text-base-500 dark:text-base-400">
              登录完成后，可在右侧“账号列表”中确认状态是否更新为 <strong>active</strong>，或查看运行记录里的截图与日志。
            </div>
          {:else}
            <div class="rounded-lg border border-base-200 dark:border-base-800 bg-base-50 dark:bg-base-900 px-4 py-3 text-sm text-base-500 dark:text-base-400">
              尚未选择账号。请先创建或从右侧选择一个已有账号。
            </div>
          {/if}
        </div>
      {/if}

      {#if currentStep === 2}
        <div class="space-y-6">
          <h2 class="text-2xl font-semibold text-base-900 dark:text-base-100">③ 创建并发布示例内容</h2>
          <p class="text-base text-base-500 dark:text-base-400">
            用一次示例发布来验证流程是否稳定。你可以随时在运行记录中查阅截图、日志与 Cookie 保存情况。
          </p>

          <div class="space-y-3">
            <label class="text-sm font-medium text-base-600 dark:text-base-300">选择发布账号</label>
            <select
              bind:value={selectedAccountId}
              class="w-full max-w-md rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
            >
              <option value="" disabled>请选择账号</option>
              {#each accounts as acc}
                <option value={acc.id}>{acc.handle} · {acc.status}</option>
              {/each}
            </select>
          </div>

          <form
            class="grid gap-5 max-w-3xl bg-base-100 dark:bg-base-900 border border-base-200 dark:border-base-800 rounded-xl p-6"
            on:submit|preventDefault={createAndPublish}
          >
            <div class="grid gap-4 sm:grid-cols-2">
              <div>
                <label class="text-sm font-medium text-base-600 dark:text-base-300">标题</label>
                <input
                  class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                  placeholder="用于内部记录，可选"
                  bind:value={publishDraft.title}
                />
              </div>
              <div>
                <label class="text-sm font-medium text-base-600 dark:text-base-300">视频文件路径 *</label>
                <input
                  class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                  placeholder="例如 D:/videos/demo.mp4"
                  bind:value={publishDraft.video_path}
                  required
                />
              </div>
            </div>

            <div>
              <label class="text-sm font-medium text-base-600 dark:text-base-300">文案 / Caption</label>
              <textarea
                rows={4}
                class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                placeholder="支持粘贴模板，可包含 {变量} 供上游流程替换"
                bind:value={publishDraft.caption}
              />
            </div>

            <div>
              <label class="text-sm font-medium text-base-600 dark:text-base-300">Hashtags</label>
              <input
                class="mt-1 w-full rounded-lg border border-base-300 dark:border-base-700 bg-transparent px-3 py-2"
                placeholder="使用英文逗号分隔，例如 #AI,#demo"
                bind:value={publishDraft.hashtags}
              />
            </div>

            <button
              class="inline-flex items-center justify-center rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-primary-700 disabled:cursor-not-allowed disabled:opacity-60"
              type="submit"
              disabled={processing}
            >
              {processing ? '执行中...' : '创建并立即发布'}
            </button>
          </form>

          {#if latestPost}
            <div class="rounded-xl border border-success-300 bg-success-50 px-4 py-3 text-success-700">
              已创建并触发任务 {latestPost.id}。请在右侧“运行记录”内确认状态与截图。
            </div>
          {/if}
        </div>
      {/if}
    </section>

    <aside class="space-y-6">
      <div class="rounded-xl border border-base-200 dark:border-base-800 bg-base-100 dark:bg-base-900 p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">账号列表</h3>
          <button
            class="text-sm text-primary-600 hover:text-primary-700"
            on:click={loadExisting}
            disabled={loadingAccounts || processing}
          >
            刷新
          </button>
        </div>

        {#if loadingAccounts}
          <p class="text-sm text-base-500">加载中...</p>
        {:else if accounts.length === 0}
          <p class="text-sm text-base-500">暂无账号，先在左侧完成第一步。</p>
        {:else}
          <ul class="space-y-3 max-h-64 overflow-auto pr-1">
            {#each accounts as acc}
              <li
                class="rounded-lg border border-base-200 dark:border-base-800 px-3 py-2 cursor-pointer transition hover:bg-base-50 dark:hover:bg-base-900"
                class:border-primary-300={selectedAccountId === acc.id}
                on:click={() => selectAccount(acc.id)}
              >
                <div class="flex items-center justify-between text-sm font-medium">
                  <span>{acc.handle}</span>
                  <span class={accountStatusClass(acc.status)}>{acc.status}</span>
                </div>
                <div class="mt-1 text-xs text-base-500 dark:text-base-400 truncate">
                  凭证: {acc.encrypted_credentials_ref}
                </div>
                <div class="mt-1 text-xs text-base-500 dark:text-base-400 truncate">
                  Profile: {acc.playwright_profile_path || '-'}
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <div class="rounded-xl border border-base-200 dark:border-base-800 bg-base-100 dark:bg-base-900 p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-semibold">最近发布记录</h3>
          <button
            class="text-sm text-primary-600 hover:text-primary-700"
            on:click={loadExisting}
            disabled={loadingPosts || processing}
          >
            刷新
          </button>
        </div>

        {#if loadingPosts}
          <p class="text-sm text-base-500">加载中...</p>
        {:else if recentPosts.length === 0}
          <p class="text-sm text-base-500">暂未有发布记录。</p>
        {:else}
          <ul class="space-y-3 max-h-64 overflow-auto pr-1">
            {#each recentPosts.slice(0, 10) as post}
              <li class="rounded-lg border border-base-200 dark:border-base-800 px-3 py-2 text-sm">
                <div class="flex items-center justify-between">
                  <span class="font-medium">{post.title ?? '未命名发布'}</span>
                  <span class={postStatusClass(post.status)}>{post.status}</span>
                </div>
                <div class="mt-1 text-xs text-base-500 dark:text-base-400 truncate">
                  账号: {accounts.find((acc) => acc.id === post.account_id)?.handle ?? post.account_id}
                </div>
                <div class="mt-1 text-xs text-base-500 dark:text-base-400">
                  更新时间: {post.updated_at ? new Date(post.updated_at * 1000).toLocaleString() : '-'}
                </div>
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    </aside>
  </div>
</div>
