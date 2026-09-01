const assert = require('node:assert/strict');
const { test } = require('node:test');
const {
  prepareIssue,
  prepareReview,
  publishPullRequest,
  postReview,
} = require('./automation.cjs');

const BASE_SHA = 'a'.repeat(40);
const HEAD_SHA = 'b'.repeat(40);
const RUN_URL = 'https://github.com/octocat/support-demo/actions/runs/123';
const ENV_NAMES = [
  'ISSUE_NUMBER', 'TRIGGERING_ACTOR', 'PR_NUMBER', 'BRANCH', 'BASE_REF',
  'RUN_URL', 'REVIEWED_SHA', 'REVIEWED_BASE_SHA', 'CODEX_FINAL_MESSAGE',
];

async function withEnv(values, run) {
  const previous = Object.fromEntries(ENV_NAMES.map((name) => [name, process.env[name]]));
  for (const name of ENV_NAMES) {
    if (values[name] === undefined) delete process.env[name];
    else process.env[name] = String(values[name]);
  }
  try {
    return await run();
  } finally {
    for (const name of ENV_NAMES) {
      if (previous[name] === undefined) delete process.env[name];
      else process.env[name] = previous[name];
    }
  }
}

function apiError(status) {
  return Object.assign(new Error(`HTTP ${status}`), { status });
}

function fixture() {
  const state = {
    permissions: { maintainer: 'maintain', writer: 'write', admin: 'admin', reader: 'read' },
    permissionErrors: {},
    userTypes: {},
    issue: {
      number: 42, state: 'open', title: 'Correct ticket status', body: 'Reproduce the bug.',
      html_url: 'https://github.com/octocat/support-demo/issues/42',
    },
    repository: { default_branch: 'main' },
    baseSha: BASE_SHA,
    refExists: false,
    refError: null,
    openPulls: [],
    pr: {
      number: 91, state: 'open', html_url: 'https://github.com/octocat/support-demo/pull/91',
      base: { ref: 'main', sha: BASE_SHA },
      head: { ref: 'codex/issue-42', sha: HEAD_SHA, repo: { full_name: 'octocat/support-demo' } },
    },
    comments: [],
  };
  const calls = [];
  const record = (name, fn) => async (args) => {
    calls.push({ name, args });
    return fn(args);
  };
  const github = {
    rest: {
      repos: {
        getCollaboratorPermissionLevel: record('repos.permission', ({ username }) => {
          if (state.permissionErrors[username]) throw state.permissionErrors[username];
          return { data: {
            permission: state.permissions[username] || 'none',
            user: { login: username, type: state.userTypes[username] || 'User' },
          } };
        }),
        get: record('repos.get', () => ({ data: state.repository })),
        getBranch: record('repos.getBranch', () => ({ data: { commit: { sha: state.baseSha } } })),
      },
      git: {
        getRef: record('git.getRef', () => {
          if (state.refError) throw state.refError;
          if (!state.refExists) throw apiError(404);
          return { data: { object: { sha: HEAD_SHA } } };
        }),
      },
      issues: {
        get: record('issues.get', () => ({ data: state.issue })),
        listComments: record('issues.listComments', ({ page = 1, per_page }) => ({
          data: state.comments.slice((page - 1) * per_page, page * per_page),
        })),
        createComment: record('issues.createComment', ({ body }) => {
          const comment = { id: state.comments.length + 1, body, user: { login: 'github-actions[bot]', type: 'Bot' } };
          state.comments.push(comment);
          return { data: comment };
        }),
        updateComment: record('issues.updateComment', ({ comment_id, body }) => {
          const comment = state.comments.find(({ id }) => id === comment_id);
          comment.body = body;
          return { data: comment };
        }),
      },
      pulls: {
        get: record('pulls.get', () => ({ data: state.pr })),
        list: record('pulls.list', () => ({ data: state.openPulls })),
        create: record('pulls.create', () => {
          state.openPulls.push(state.pr);
          return { data: state.pr };
        }),
      },
    },
    async paginate(method, args) {
      const results = [];
      for (let page = 1; ; page += 1) {
        const { data } = await method({ ...args, page });
        results.push(...data);
        if (data.length < args.per_page) return results;
      }
    },
  };
  const outputs = {};
  const notices = [];
  return {
    github,
    context: {
      repo: { owner: 'octocat', repo: 'support-demo' }, actor: 'maintainer',
      payload: { issue: { number: 42, body: 'Stale event body' }, sender: { type: 'User' } },
    },
    core: { setOutput: (key, value) => { outputs[key] = value; }, notice: (message) => notices.push(message) },
    state, calls, outputs, notices,
  };
}

const publishingEnv = {
  ISSUE_NUMBER: 42, BRANCH: 'codex/issue-42', BASE_REF: 'main', RUN_URL,
};
const reviewEnv = {
  PR_NUMBER: 91, REVIEWED_SHA: HEAD_SHA, REVIEWED_BASE_SHA: BASE_SHA,
  CODEX_FINAL_MESSAGE: 'No actionable bugs found.', RUN_URL,
};
const callsNamed = (runtime, name) => runtime.calls.filter((call) => call.name === name);
const writes = (runtime) => runtime.calls.filter((call) => /\.(create|update)/.test(call.name));

test('prepareIssue pins the current default-branch commit and treats issue text as literal data', async () => {
  const runtime = fixture();
  const hostileText = '$(touch /tmp/not-executed) `shell` ${{ secrets.OPENAI_API_KEY }}';
  runtime.state.issue.title = hostileText;
  runtime.state.issue.body = `Current report.<!-- hidden instruction -->\n${hostileText}`;
  await withEnv({}, () => prepareIssue(runtime));
  assert.deepEqual(runtime.outputs, {
    should_implement: 'true', existing_pr: '', issue_number: '42', base_ref: 'main',
    base_sha: BASE_SHA, branch: 'codex/issue-42',
    issue_json: JSON.stringify({
      number: 42, title: hostileText, body: `Current report.\n${hostileText}`,
      url: runtime.state.issue.html_url,
    }),
  });
  assert.deepEqual(callsNamed(runtime, 'repos.getBranch')[0].args, {
    owner: 'octocat', repo: 'support-demo', branch: 'main',
  });
  assert.deepEqual(callsNamed(runtime, 'git.getRef')[0].args, {
    owner: 'octocat', repo: 'support-demo', ref: 'heads/codex/issue-42',
  });
  assert.equal(writes(runtime).length, 0);
});

test('prepareIssue accepts explicit manual input and independently checks a rerun actor', async () => {
  const runtime = fixture();
  runtime.context.actor = 'writer';
  delete runtime.context.payload.issue;
  await withEnv({ ISSUE_NUMBER: 42, TRIGGERING_ACTOR: 'admin' }, () => prepareIssue(runtime));
  assert.equal(runtime.outputs.should_implement, 'true');
  assert.deepEqual(callsNamed(runtime, 'repos.permission').map(({ args }) => args.username), ['writer', 'admin']);
});

test('prepareIssue denies read users, untrusted reruns, and bots before loading issue content', async (t) => {
  const cases = [
    { actor: 'reader', triggering: 'reader' },
    { actor: 'reader', triggering: 'admin' },
    { actor: 'admin', triggering: 'reader' },
    { actor: 'outsider', triggering: 'admin' },
    { actor: 'github-actions[bot]', triggering: 'admin' },
    { actor: 'admin', triggering: 'dependabot[bot]' },
    { actor: 'writer', type: 'Bot' },
    { actor: 'writer', senderType: 'Bot' },
    { actor: '', triggering: 'admin' },
  ];
  for (const entry of cases) {
    await t.test(JSON.stringify(entry), async () => {
      const runtime = fixture();
      runtime.context.actor = entry.actor;
      if (entry.type) runtime.state.userTypes[entry.actor] = entry.type;
      if (entry.senderType) runtime.context.payload.sender.type = entry.senderType;
      await withEnv({ TRIGGERING_ACTOR: entry.triggering }, () => prepareIssue(runtime));
      assert.equal(runtime.outputs.should_implement, 'false');
      assert.equal(runtime.notices.length, 1);
      assert.equal(callsNamed(runtime, 'issues.get').length, 0);
      assert.equal(writes(runtime).length, 0);
    });
  }
});

test('prepareIssue treats permission 403/404 as denied but propagates unexpected API failures', async (t) => {
  for (const status of [403, 404, 500]) {
    await t.test(String(status), async () => {
      const runtime = fixture();
      runtime.state.permissionErrors.maintainer = apiError(status);
      await withEnv({}, async () => {
        if (status === 500) await assert.rejects(prepareIssue(runtime), /HTTP 500/);
        else await prepareIssue(runtime);
      });
      assert.equal(runtime.outputs.should_implement, 'false');
      assert.equal(callsNamed(runtime, 'issues.get').length, 0);
    });
  }
});

test('prepareIssue preserves an existing open PR without inspecting or modifying its branch', async () => {
  const runtime = fixture();
  runtime.state.openPulls = [runtime.state.pr];
  runtime.state.refExists = true;
  await withEnv({}, () => prepareIssue(runtime));
  assert.equal(runtime.outputs.should_implement, 'false');
  assert.equal(runtime.outputs.existing_pr, '91');
  assert.equal(callsNamed(runtime, 'git.getRef').length, 0);
  assert.equal(writes(runtime).length, 0);
  assert.equal(callsNamed(runtime, 'pulls.list')[0].args.head, 'octocat:codex/issue-42');
});

test('prepareIssue refuses an orphaned branch and does not confuse API errors with a missing branch', async () => {
  const runtime = fixture();
  runtime.state.refExists = true;
  await withEnv({}, () => assert.rejects(prepareIssue(runtime), /already exists.*manual/i));
  assert.equal(runtime.outputs.should_implement, 'false');
  assert.equal(writes(runtime).length, 0);
  runtime.state.refExists = false;
  runtime.state.refError = apiError(503);
  await withEnv({}, () => assert.rejects(prepareIssue(runtime), /HTTP 503/));
});

test('issue numbers must be positive safe decimal integers', async (t) => {
  for (const value of ['0', '-1', '1.5', '1e3', '0x2a', '42x', ' 42', '01', '9007199254740992']) {
    await t.test(value, async () => {
      const runtime = fixture();
      await withEnv({ ISSUE_NUMBER: value }, () => assert.rejects(prepareIssue(runtime), /ISSUE_NUMBER.*positive safe integer/));
      assert.equal(runtime.calls.length, 0);
    });
  }
  const runtime = fixture();
  delete runtime.context.payload.issue;
  await withEnv({}, () => assert.rejects(prepareIssue(runtime), /ISSUE_NUMBER.*positive safe integer/));
});

test('prepareIssue ignores closed issues and pull requests', async (t) => {
  for (const change of [{ state: 'closed' }, { pull_request: {} }]) {
    await t.test(JSON.stringify(change), async () => {
      const runtime = fixture();
      Object.assign(runtime.state.issue, change);
      await withEnv({}, () => prepareIssue(runtime));
      assert.equal(runtime.outputs.should_implement, 'false');
      assert.equal(runtime.notices.length, 1);
      assert.equal(callsNamed(runtime, 'repos.get').length, 0);
    });
  }
});

test('prepareIssue bounds issue content and removes closed or unclosed HTML comments', async () => {
  const runtime = fixture();
  runtime.state.issue.body = '<!--ignore-->before' + 'x'.repeat(60000);
  await withEnv({}, () => prepareIssue(runtime));
  const body = JSON.parse(runtime.outputs.issue_json).body;
  assert.equal(body.length, 50000);
  assert.ok(body.startsWith('before'));
  runtime.state.issue.body = 'before<!-- unclosed hidden instructions';
  await withEnv({}, () => prepareIssue(runtime));
  assert.equal(JSON.parse(runtime.outputs.issue_json).body, 'before');
  runtime.state.baseSha = 'main';
  await withEnv({}, () => assert.rejects(prepareIssue(runtime), /SHA/));
});

test('prepareReview loads current PR base/head SHAs instead of event or default-branch SHAs', async () => {
  const runtime = fixture();
  runtime.context.payload.pull_request = { number: 91, base: { sha: 'c'.repeat(40) }, head: { sha: 'd'.repeat(40) } };
  await withEnv({}, () => prepareReview(runtime));
  assert.deepEqual(runtime.outputs, {
    should_review: 'true', pr_number: '91', base_sha: BASE_SHA, head_sha: HEAD_SHA, head_ref: 'codex/issue-42',
  });
  assert.deepEqual(callsNamed(runtime, 'pulls.get')[0].args, { owner: 'octocat', repo: 'support-demo', pull_number: 91 });
  assert.equal(callsNamed(runtime, 'repos.getBranch').length, 0);
  assert.equal(writes(runtime).length, 0);
});

test('prepareReview supports manual input but refuses missing, malformed, or unsafe numbers and SHAs', async () => {
  const runtime = fixture();
  await withEnv({ PR_NUMBER: 91 }, () => prepareReview(runtime));
  assert.equal(runtime.outputs.should_review, 'true');
  await withEnv({}, () => assert.rejects(prepareReview(runtime), /PR_NUMBER.*positive safe integer/));
  await withEnv({ PR_NUMBER: '1; echo unsafe' }, () => assert.rejects(prepareReview(runtime), /PR_NUMBER.*positive safe integer/));
  runtime.state.pr.base.sha = 'main';
  await withEnv({ PR_NUMBER: 91 }, () => assert.rejects(prepareReview(runtime), /SHA/));
  runtime.state.pr.base.sha = BASE_SHA;
  runtime.state.pr.head.sha = 'b'.repeat(41);
  await withEnv({ PR_NUMBER: 91 }, () => assert.rejects(prepareReview(runtime), /SHA/));
});

test('prepareReview skips closed PRs, forks, and deleted fork repositories', async (t) => {
  for (const variant of ['closed', 'fork', 'deleted']) {
    await t.test(variant, async () => {
      const runtime = fixture();
      if (variant === 'closed') runtime.state.pr.state = 'closed';
      if (variant === 'fork') runtime.state.pr.head.repo.full_name = 'outsider/support-demo';
      if (variant === 'deleted') runtime.state.pr.head.repo = null;
      await withEnv({ PR_NUMBER: 91 }, () => prepareReview(runtime));
      assert.equal(runtime.outputs.should_review, 'false');
      assert.equal(runtime.notices.length, 1);
      assert.equal(writes(runtime).length, 0);
    });
  }
});

test('publishPullRequest creates an advisory PR and links it back to its issue', async () => {
  const runtime = fixture();
  const hostileTitle = 'Fix `$(echo unsafe)` and ${{ secrets.OPENAI_API_KEY }}';
  runtime.state.issue.title = hostileTitle;
  await withEnv(publishingEnv, () => publishPullRequest(runtime));
  const created = callsNamed(runtime, 'pulls.create')[0].args;
  assert.equal(created.title, `[Codex] ${hostileTitle}`);
  assert.equal(created.head, 'codex/issue-42');
  assert.equal(created.base, 'main');
  assert.match(created.body, /Closes #42/);
  for (const expected of [/Backend/, /Frontend/, /build/i, /evidence/i, /automation.helper tests/i, /human review/i, /merge decision/i]) {
    assert.match(created.body, expected);
  }
  assert.ok(created.body.includes(RUN_URL));
  assert.deepEqual(runtime.outputs, { pr_number: '91', pr_url: runtime.state.pr.html_url });
  const comment = callsNamed(runtime, 'issues.createComment')[0].args;
  assert.equal(comment.issue_number, 42);
  assert.ok(comment.body.startsWith('<!-- codex-issue-implementation -->'));
  assert.ok(comment.body.includes(runtime.state.pr.html_url));
  assert.ok(comment.body.includes(RUN_URL));
});

test('publishPullRequest reuses an existing PR and bot comment on retries without rewriting the PR', async () => {
  const runtime = fixture();
  await withEnv(publishingEnv, () => publishPullRequest(runtime));
  runtime.state.issue.title = 'Edited issue title must not overwrite the PR';
  await withEnv({ ...publishingEnv, RUN_URL: `${RUN_URL}4` }, () => publishPullRequest(runtime));
  assert.equal(callsNamed(runtime, 'pulls.create').length, 1);
  assert.equal(callsNamed(runtime, 'issues.createComment').length, 1);
  assert.equal(callsNamed(runtime, 'issues.updateComment').length, 1);
  assert.ok(runtime.state.comments[0].body.includes(`${RUN_URL}4`));
  assert.equal(callsNamed(runtime, 'git.getRef').length, 0);
});

test('publishPullRequest caps titles and only updates its own bot-authored marker comment across pages', async () => {
  const runtime = fixture();
  runtime.state.issue.title = 'x'.repeat(400);
  runtime.state.comments = Array.from({ length: 100 }, (_, index) => ({
    id: index + 1, body: '<!-- codex-issue-implementation --> human text', user: { login: 'maintainer', type: 'User' },
  }));
  runtime.state.comments.push({ id: 101, body: '<!-- codex-issue-implementation --> old', user: { login: 'github-actions[bot]', type: 'Bot' } });
  await withEnv(publishingEnv, () => publishPullRequest(runtime));
  assert.equal(callsNamed(runtime, 'pulls.create')[0].args.title.length, 240);
  assert.deepEqual(callsNamed(runtime, 'issues.listComments').map(({ args }) => args.page), [1, 2]);
  assert.equal(callsNamed(runtime, 'issues.updateComment')[0].args.comment_id, 101);
  assert.equal(runtime.state.comments[0].body, '<!-- codex-issue-implementation --> human text');
  assert.equal(callsNamed(runtime, 'issues.createComment').length, 0);
});

test('publishPullRequest rejects closed issues, PRs, wrong branches, and missing required inputs', async (t) => {
  const cases = [
    { issue: { state: 'closed' }, pattern: /open issue/ },
    { issue: { pull_request: {} }, pattern: /open issue/ },
    { env: { BRANCH: 'main' }, pattern: /BRANCH.*codex\/issue-42/ },
    { env: { BASE_REF: undefined }, pattern: /BASE_REF/ },
    { env: { RUN_URL: undefined }, pattern: /RUN_URL/ },
    { env: { RUN_URL: 'not-a-url' }, pattern: /RUN_URL.*HTTPS/ },
    { env: { RUN_URL: 'javascript:alert(1)' }, pattern: /RUN_URL.*HTTPS/ },
    { env: { RUN_URL: 'https://username:password@example.com/run' }, pattern: /RUN_URL.*HTTPS/ },
  ];
  for (const entry of cases) {
    await t.test(JSON.stringify(entry), async () => {
      const runtime = fixture();
      Object.assign(runtime.state.issue, entry.issue);
      await withEnv({ ...publishingEnv, ...entry.env }, () => assert.rejects(publishPullRequest(runtime), entry.pattern));
      assert.equal(writes(runtime).length, 0);
    });
  }
});

test('postReview publishes literal advisory findings for the exact reviewed commit', async () => {
  const runtime = fixture();
  const report = 'File `backend/app/main.py:12`: $(touch /tmp/not-executed)\n${{ secrets.OPENAI_API_KEY }}\n```js\nthrow "literal";\n```';
  await withEnv({ ...reviewEnv, CODEX_FINAL_MESSAGE: report }, () => postReview(runtime));
  const posted = callsNamed(runtime, 'issues.createComment')[0].args;
  assert.equal(posted.issue_number, 91);
  assert.ok(posted.body.startsWith('<!-- codex-pr-review -->'));
  assert.ok(posted.body.includes(HEAD_SHA));
  assert.ok(posted.body.includes(BASE_SHA));
  assert.ok(posted.body.includes(report));
  assert.ok(posted.body.includes(RUN_URL));
  assert.match(posted.body, /advisory/i);
  assert.equal(writes(runtime).length, 1);
});

test('postReview refuses changed heads, changed bases, closed PRs, and forks instead of posting outdated findings', async (t) => {
  for (const variant of ['stale', 'base-moved-or-retargeted', 'closed', 'fork']) {
    await t.test(variant, async () => {
      const runtime = fixture();
      if (variant === 'stale') runtime.state.pr.head.sha = 'c'.repeat(40);
      if (variant === 'base-moved-or-retargeted') runtime.state.pr.base.sha = 'c'.repeat(40);
      if (variant === 'closed') runtime.state.pr.state = 'closed';
      if (variant === 'fork') runtime.state.pr.head.repo.full_name = 'outsider/support-demo';
      await withEnv(reviewEnv, () => postReview(runtime));
      assert.equal(writes(runtime).length, 0);
      assert.equal(runtime.notices.length, 1);
    });
  }
});

test('postReview never overwrites a human, another bot, or a quoted marker comment', async () => {
  const runtime = fixture();
  runtime.state.comments = [
    { id: 1, body: '<!-- codex-pr-review --> human report', user: { login: 'maintainer', type: 'User' } },
    { id: 2, body: '<!-- codex-pr-review --> other bot', user: { login: 'other[bot]', type: 'Bot' } },
    { id: 3, body: 'Quoted: <!-- codex-pr-review -->', user: { login: 'github-actions[bot]', type: 'Bot' } },
  ];
  await withEnv(reviewEnv, () => postReview(runtime));
  await withEnv({ ...reviewEnv, CODEX_FINAL_MESSAGE: 'Updated findings' }, () => postReview(runtime));
  assert.equal(callsNamed(runtime, 'issues.createComment').length, 1);
  assert.equal(callsNamed(runtime, 'issues.updateComment')[0].args.comment_id, 4);
  assert.equal(runtime.state.comments[0].body, '<!-- codex-pr-review --> human report');
  assert.equal(runtime.state.comments[1].body, '<!-- codex-pr-review --> other bot');
  assert.equal(runtime.state.comments[2].body, 'Quoted: <!-- codex-pr-review -->');
});

test('postReview bounds long reports and clearly rejects empty output or malformed reviewed SHAs', async () => {
  const runtime = fixture();
  await withEnv({ ...reviewEnv, CODEX_FINAL_MESSAGE: 'x'.repeat(70000) }, () => postReview(runtime));
  const body = callsNamed(runtime, 'issues.createComment')[0].args.body;
  assert.ok(body.length < 65536);
  assert.ok(body.includes('x'.repeat(55000)));
  assert.ok(!body.includes('x'.repeat(55001)));
  assert.match(body, /truncated/i);
  await withEnv({ ...reviewEnv, CODEX_FINAL_MESSAGE: ' \n\t' }, () => assert.rejects(postReview(runtime), /CODEX_FINAL_MESSAGE.*empty/i));
  await withEnv({ ...reviewEnv, REVIEWED_SHA: 'main' }, () => assert.rejects(postReview(runtime), /SHA/));
  await withEnv({ ...reviewEnv, REVIEWED_BASE_SHA: 'main' }, () => assert.rejects(postReview(runtime), /REVIEWED_BASE_SHA/));
  await withEnv({ ...reviewEnv, REVIEWED_BASE_SHA: undefined }, () => assert.rejects(postReview(runtime), /REVIEWED_BASE_SHA/));
});
