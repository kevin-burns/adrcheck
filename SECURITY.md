# Security

## Reporting

Report a vulnerability privately through GitHub's security advisories for this repository, or to the
maintainer listed in `.github/CODEOWNERS`. Do not open a public issue for it. You will get an
acknowledgement within a week and a fix or a reasoned decision within thirty days.

## What adrcheck does with your code and keys

- adrcheck sends the diff of each judged commit, the post-change text of the changed files, and the text
  of the selected ADRs to the model provider you configure. Nothing else leaves the machine. A commit
  that touches no governed path makes no call.
- Keys are read from the environment by `src/adrcheck/adapters/providers.py` and nowhere else. They are
  never written to the report, the cache, or a log.
- The obligation cache under `.adrcheck/obligations/` holds compiled text derived from your ADRs. It is
  safe to commit and contains no code or diff.
- The GitHub Action needs `contents: read` and, for the comment, `pull-requests: write`. It posts one
  comment and writes the job summary. It does not push, open pull requests, or read other repositories.

## Supply chain

- Actions are pinned to commit SHAs. Dependabot updates them weekly.
- Python dependencies are locked in `uv.lock`; the lock is what CI installs.
- `gitleaks` runs in the pre-commit gate and in CI.
