'use strict';

// Called by actions/github-script. Keep issue and model text in API arguments,
// never in generated JavaScript, shell commands, or workflow expressions.
const BOT_LOGIN = 'github-actions[bot]';
const ISSUE_MARKER = '<!-- codex-issue-implementation -->';
const REVIEW_MARKER = '<!-- codex-pr-review -->';
const WRITE_PERMISSIONS = new Set(['write', 'maintain', 'admin']);

function positiveInteger(value, name) {
  const decimal = typeof value === 'number' ? String(value) : value;
  if (typeof decimal !== 'string' || !/^[1-9][0-9]*$/.test(decimal)) {
    throw new Error(`${name} must be a positive safe integer from an input or event.`);
  }
  const number = Number(decimal);
  if (!Number.isSafeInteger(number)) {
    throw new Error(`${name} must be a positive safe integer from an input or event.`);
  }
  return number;
}

function checkedSha(value, name) {
  if (typeof value !== 'string' || !/^[a-fA-F0-9]{40}$/.test(value)) {
    throw new Error(`${name} must be a full 40-character commit SHA.`);
  }
  return value;
}

function requiredEnvironment(name) {
  const value = process.env[name];
  if (typeof value !== 'string' || !value.trim()) {
    throw new Error(`${name} is required and must not be empty.`);
  }
  return value;
}

function workflowRunUrl() {
  const value = requiredEnvironment('RUN_URL');
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new Error('RUN_URL must be a valid HTTPS workflow-run URL.');
  }
  if (url.protocol !== 'https:' || url.username || url.password || value.length > 2048 || /[\s<>]/.test(value)) {
    throw new Error('RUN_URL must be a valid HTTPS workflow-run URL.');
  }
  return url.href;
}

function output(core, values) {
  for (const [key, value] of Object.entries(values)) core.setOutput(key, String(value));
}

async function trustedActors({ github, context, core }) {
  // github.actor remains the original actor on a rerun. Checking only the
  // rerunning maintainer would let an untrusted original event spend secrets.
  const actors = new Set([context.actor, process.env.TRIGGERING_ACTOR || context.actor]);
  for (const actor of actors) {
    if (typeof actor !== 'string' || !actor || /\[bot\]$/i.test(actor)
      || (actor === context.actor && context.payload.sender?.type === 'Bot')) {
      core.notice('Issue implementation skipped: both initiating actors must be human repository writers.');
      return false;
    }
    let permission;
    try {
      ({ data: permission } = await github.rest.repos.getCollaboratorPermissionLevel({
        ...context.repo, username: actor,
      }));
    } catch (error) {
      if (error.status !== 403 && error.status !== 404) throw error;
      core.notice(`Issue implementation skipped: cannot verify write permission for ${actor}.`);
      return false;
    }
    if (!WRITE_PERMISSIONS.has(permission.permission) || permission.user?.type === 'Bot') {
      core.notice(`Issue implementation skipped: ${actor} must be a human repository writer.`);
      return false;
    }
  }
  return true;
}

function isOpenIssue(issue) {
  return issue.state === 'open' && !issue.pull_request;
}

function isSameRepositoryOpenPullRequest(pr, context) {
  const expected = `${context.repo.owner}/${context.repo.repo}`.toLowerCase();
  return pr.state === 'open' && pr.head?.repo?.full_name?.toLowerCase() === expected;
}

async function openPullRequest(github, context, branch) {
  const { data } = await github.rest.pulls.list({
    ...context.repo, state: 'open', head: `${context.repo.owner}:${branch}`, per_page: 1,
  });
  return data[0];
}

async function upsertBotComment({ github, context }, issueNumber, marker, body) {
  const comments = await github.paginate(github.rest.issues.listComments, {
    ...context.repo, issue_number: issueNumber, per_page: 100,
  });
  const previous = comments.find((comment) => comment.user?.login === BOT_LOGIN
    && comment.user?.type === 'Bot' && comment.body?.startsWith(marker));
  if (previous) {
    if (previous.body !== body) {
      await github.rest.issues.updateComment({ ...context.repo, comment_id: previous.id, body });
    }
  } else {
    await github.rest.issues.createComment({ ...context.repo, issue_number: issueNumber, body });
  }
}

async function prepareIssue({ github, context, core }) {
  output(core, { should_implement: 'false', existing_pr: '' });
  const number = positiveInteger(process.env.ISSUE_NUMBER || context.payload.issue?.number, 'ISSUE_NUMBER');
  if (!await trustedActors({ github, context, core })) return;

  const { data: issue } = await github.rest.issues.get({ ...context.repo, issue_number: number });
  if (!isOpenIssue(issue)) {
    core.notice(`Issue implementation skipped: #${number} must be an open issue, not a pull request.`);
    return;
  }

  const { data: repository } = await github.rest.repos.get(context.repo);
  const baseRef = repository.default_branch;
  if (typeof baseRef !== 'string' || !baseRef) throw new Error('The repository has no default branch.');
  const { data: base } = await github.rest.repos.getBranch({ ...context.repo, branch: baseRef });
  const baseSha = checkedSha(base.commit?.sha, 'Default branch SHA');
  const branch = `codex/issue-${number}`;
  output(core, {
    issue_number: number,
    base_ref: baseRef,
    base_sha: baseSha,
    branch,
    issue_json: JSON.stringify({
      number, title: issue.title || '',
      body: (issue.body || '').replace(/<!--[\s\S]*?(?:-->|$)/g, '').slice(0, 50000),
      url: issue.html_url,
    }),
  });

  const existing = await openPullRequest(github, context, branch);
  if (existing) {
    output(core, { existing_pr: existing.number });
    core.notice(`Issue implementation skipped: pull request #${existing.number} already uses ${branch}.`);
    return;
  }

  try {
    await github.rest.git.getRef({ ...context.repo, ref: `heads/${branch}` });
  } catch (error) {
    if (error.status !== 404) throw error;
    output(core, { should_implement: 'true' });
    return;
  }
  throw new Error(`Branch ${branch} already exists without an open pull request. Inspect it and open a PR manually, or preserve its work and rename/delete it before retrying. The workflow will not overwrite it.`);
}

async function prepareReview({ github, context, core }) {
  output(core, { should_review: 'false' });
  const number = positiveInteger(process.env.PR_NUMBER || context.payload.pull_request?.number, 'PR_NUMBER');
  const { data: pr } = await github.rest.pulls.get({ ...context.repo, pull_number: number });
  if (!isSameRepositoryOpenPullRequest(pr, context)) {
    core.notice(`PR review skipped: #${number} must be open and from this repository.`);
    return;
  }
  const baseSha = checkedSha(pr.base?.sha, 'PR base SHA');
  const headSha = checkedSha(pr.head?.sha, 'PR head SHA');
  if (typeof pr.head.ref !== 'string' || !pr.head.ref) throw new Error('The PR head branch is missing.');
  output(core, {
    pr_number: number, base_sha: baseSha, head_sha: headSha, head_ref: pr.head.ref, should_review: 'true',
  });
}

async function publishPullRequest({ github, context, core }) {
  const number = positiveInteger(process.env.ISSUE_NUMBER, 'ISSUE_NUMBER');
  const branch = requiredEnvironment('BRANCH');
  if (branch !== `codex/issue-${number}`) throw new Error(`BRANCH must be codex/issue-${number}.`);
  const baseRef = requiredEnvironment('BASE_REF');
  const runUrl = workflowRunUrl();
  const { data: issue } = await github.rest.issues.get({ ...context.repo, issue_number: number });
  if (!isOpenIssue(issue)) throw new Error(`#${number} must still be an open issue before creating a pull request.`);

  let pr = await openPullRequest(github, context, branch);
  if (!pr) {
    ({ data: pr } = await github.rest.pulls.create({
      ...context.repo, head: branch, base: baseRef,
      title: `[Codex] ${issue.title || ''}`.trim().slice(0, 240),
      body: [
        `Closes #${number}`,
        '',
        'Implemented by the Codex issue workflow.',
        '',
        '## Verification',
        '',
        'The workflow completed these required checks before publishing this pull request:',
        '- Backend tests',
        '- Frontend tests',
        '- Frontend production build',
        '- Bug-fix evidence gate',
        '- GitHub automation-helper tests',
        '',
        `[Workflow evidence](<${runUrl}>)`,
        '',
        'Human review and an explicit merge decision are required. This automation does not approve or merge pull requests.',
      ].join('\n'),
    }));
  }
  output(core, { pr_number: pr.number, pr_url: pr.html_url });
  await upsertBotComment({ github, context }, number, ISSUE_MARKER, [
    ISSUE_MARKER,
    `Codex implementation: [pull request #${pr.number}](<${pr.html_url}>).`,
    '',
    `[Workflow run](<${runUrl}>). Human review and a merge decision are required.`,
  ].join('\n'));
}

async function postReview({ github, context, core }) {
  const number = positiveInteger(process.env.PR_NUMBER, 'PR_NUMBER');
  const reviewedSha = checkedSha(process.env.REVIEWED_SHA, 'REVIEWED_SHA');
  const reviewedBaseSha = checkedSha(process.env.REVIEWED_BASE_SHA, 'REVIEWED_BASE_SHA');
  const { data: pr } = await github.rest.pulls.get({ ...context.repo, pull_number: number });
  if (!isSameRepositoryOpenPullRequest(pr, context)
    || pr.head.sha.toLowerCase() !== reviewedSha.toLowerCase()
    || pr.base?.sha?.toLowerCase() !== reviewedBaseSha.toLowerCase()) {
    core.notice(`PR review not posted: #${number} is closed, from a fork, or its base/head changed after the review started.`);
    return;
  }
  const report = requiredEnvironment('CODEX_FINAL_MESSAGE').trim();
  const runUrl = workflowRunUrl();
  const boundedReport = report.length > 55000
    ? `${report.slice(0, 55000)}\n\n_Report truncated; see the workflow run for full output._`
    : report;
  await upsertBotComment({ github, context }, number, REVIEW_MARKER, [
    REVIEW_MARKER,
    '## Codex PR review',
    '',
    `Reviewed base: \`${reviewedBaseSha}\``,
    `Reviewed head: \`${reviewedSha}\``,
    '',
    boundedReport,
    '',
    `[Workflow run](<${runUrl}>) · Advisory only; human review and a merge decision are required.`,
  ].join('\n'));
}

module.exports = { prepareIssue, prepareReview, publishPullRequest, postReview };
