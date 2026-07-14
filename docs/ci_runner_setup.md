# Gitea Actions Runner Setup

`.github/workflows/python-ci.yml` 需要 Gitea Actions runner 才能执行。仓库只提交 workflow，不会自动创建 runner；任务会一直显示 `pending / Waiting to run`，直到有 runner 的标签与 `runs-on` 匹配。

## Required labels

The workflow uses these labels:

- `ubuntu-latest` for Ubuntu Python 3.11/3.12 jobs;
- `macos-latest` for macOS Python 3.11/3.12 jobs;
- `windows-latest` for Windows Python 3.11/3.12 jobs and the real cover/block visual job.

The `windows-latest` runner must be an actual Windows host. The visual job intentionally exercises the installed Windows Python environment; a Linux container with a renamed label is not equivalent evidence.

## Register and start a runner

Install the Gitea `act_runner` binary on a trusted host, obtain a repository or organization registration token from Gitea, and keep the token outside the repository. Registration is host-specific; do not copy a `.runner` file between machines.

The non-interactive shape is:

```text
act_runner register --no-interactive \
  --instance <GITEA_URL> \
  --token <REGISTRATION_TOKEN> \
  --name <RUNNER_NAME> \
  --labels <LABEL>:host
act_runner daemon
```

Register one runner for each required host label, or use an administrator-managed runner pool that advertises all three labels. Do not put the real registration token in shell history, workflow files, or documentation.

## Verify the repository gate

After the daemon is online, push a harmless documentation change or use `workflow_dispatch`. The expected evidence is:

1. all seven jobs leave `pending`;
2. the Windows visual job runs `tests/test_portable_visuals.py` and the installed-CLI strict sample build;
3. the commit status is `success` for the full matrix and the Windows visual job.

If jobs remain `Waiting to run`, inspect runner registration and labels before changing Python code. The workflow is deliberately label-specific so a successful Linux job cannot be mistaken for Windows coverage.

See the [Gitea Act Runner documentation](https://docs.gitea.com/1.22/usage/actions/act-runner) for installation, registration, labels, and daemon operation.
