# Development workflow

Keep `main` current and passing CI. Each new feature or fix starts from updated
`main` on a short-lived branch and gets a focused pull request. One PR should
deliver one independently verifiable outcome; split dependent work into sequential
PRs rather than accumulating the remaining roadmap on one branch.

Commit coherent, tested increments with descriptive messages. Preserve meaningful
individual commits using a merge commit by default; do not squash a long history
of completed work into one commit. Finish and merge the current PR after review
and passing checks before starting unrelated features. Do not bypass failed checks
or automatically merge work the user has not authorized to merge.

Before a merge, inspect CI for the exact head commit: backend tests/build/audit,
frontend lint/types/tests/build/audit, browser journeys and secret checks. A local
passing test run does not replace remote CI. Document material limits and remaining
product work without calling unimplemented features complete.

Check the repository-local author identity before committing (`git var
GIT_AUTHOR_IDENT`). Use the intended contributor's verified GitHub email or their
GitHub-provided noreply address. Verify GitHub attribution after the first push.
Never change global Git identity for this project. Rewriting published history
requires explicit authorization, a recoverable backup, preserved content/dates,
and a force-with-lease push restricted to the reviewed branch.

GitHub normally counts qualifying commits when they reach the default branch and
their author email belongs to the intended account; its contribution graph may
take up to 24 hours to refresh. See [GitHub's contribution guidance](https://docs.github.com/en/account-and-profile/how-tos/contribution-settings/troubleshooting-missing-contributions).
Do not fabricate commits or alter dates to manufacture activity.
