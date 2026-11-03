# Contributing

Thanks for helping. Bug reports, fixes and new languages tested on real videos are all welcome.

## Before you start
- **Bugs and ideas:** open an issue with the bug or feature template.
- **Code changes:** open an issue first, or comment on an existing one, so we agree on the approach before you write it. One issue per PR.
- **Features:** the project adds a feature when real output shows a need (see [ROADMAP.md](ROADMAP.md)). An issue with a video where the output goes wrong is the best way to propose one.

## Setup
You need Python 3.12 or higher and ffmpeg.
```bash
git clone https://github.com/<you>/subtitles-generator.git    # your fork
cd subtitles-generator
python3.12 -m venv venv
source venv/bin/activate
pip install -e ".[dev]" -c constraints.txt
```
Add `.[dev,separate]` to work on vocal separation.

## Making a change
1. Create a branch from `main`, named after the issue: `feat/issue-12-short-name`, `fix/issue-12-short-name` or `docs/issue-12-short-name`.
2. Make the change, matching the existing code style. Keep comments short and useful.
3. Add a test for it, and check that the test fails without your change. Run all tests:
   ```bash
   pytest
   ```
   The tests use fakes for the models, the translators and ffmpeg, so they need no keys or downloads.
4. Run the CLI on a real video and check the subtitles. Say in the PR which video (language, length) and what changed in the output.
5. Open a PR that links the issue (`Closes #12`).

## Rules on main
- **Signed commits:** every commit must be signed. See GitHub's guide to [signing commits](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).
- **Tests:** the `tests` check must pass, on a branch that is up to date with `main`. If `main` moves on, merge it into your branch.
- **Merging:** the maintainer reviews and merges with a merge commit. Please don't squash or rebase a branch that is already in a PR.

## Secrets
Never paste `.env`, API keys or Google service account files into an issue, PR or log. When you share `work/<video name>/run.log`, check it first.

## License
By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
