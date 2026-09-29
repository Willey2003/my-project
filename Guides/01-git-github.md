---
tags: [devops-prep, guide]
---
# Phase 1 - Git & GitHub Fundamentals

**Plan week:** 1 · **Hours:** 10 · **Cert:** none (portfolio) · **Deliverable:** a `devops-lab` repo on GitHub with clean branch + PR history. It is home base for every lab from now on.

## Why this matters at Senior/Principal level
Every change you make for the next 70 weeks (Ansible, Terraform, manifests, policies) is code reviewed through Git. Interviewers for Staff roles look at *how* you work in Git: small commits, readable history, PR descriptions that explain the why.

## Core concepts
- **Snapshots, not diffs.** Each commit points to a *tree* (directory snapshot) plus parent commit(s), author, message. Blobs are content-addressed (SHA). Identical files are stored once.
- **Three areas:** working tree -> `git add` -> index (staging) -> `git commit` -> repository. `git status` tells you which area each change is in.
- **Refs:** a branch is a movable pointer to a commit. `HEAD` points to the current branch (or directly at a commit = "detached HEAD"). Tags are fixed pointers.
- **Merging:** fast-forward (just move the pointer) vs three-way merge (creates a merge commit). **Rebase** replays your commits on top of another base: linear history, but rewrites SHAs, so never rebase commits others already pulled.
- **Undo toolbox:**
  | Situation | Command |
  |---|---|
  | Unstage a file | `git restore --staged f` |
  | Discard local edits to a file | `git restore f` |
  | Fix the last commit message / add a forgotten file | `git commit --amend` (only if not pushed) |
  | Undo a pushed commit safely | `git revert <sha>` (new commit that inverts it) |
  | Move branch back, keep changes staged/unstaged/discard | `git reset --soft/--mixed/--hard <sha>` |
  | "I lost a commit" | `git reflog`, then `git branch rescue <sha>` |
- **Remotes:** `origin` is just a name. `fetch` downloads, `pull` = fetch + merge (or rebase with `pull.rebase=true`), `push -u` sets upstream.
- **GitHub collaboration:** fork -> branch -> PR -> review -> squash/merge. Protect `main`: require PR, require status checks (you will add CI in week 21), no force-push.

## Command cheat sheet
```bash
git config --global user.name "Gaganpreet Singh"
git config --global user.email "<your github email>"
git config --global init.defaultBranch main
git config --global pull.rebase true
git config --global alias.lg "log --oneline --graph --decorate --all"

git switch -c feature/lvm-lab        # new branch
git add -p                           # stage hunks interactively - makes small, focused commits
git commit -m "linux: add LVM loop-device lab"
git push -u origin feature/lvm-lab
gh pr create --fill                  # GitHub CLI
git stash push -m wip ; git stash pop
git bisect start ; git bisect bad ; git bisect good v1.0   # find the commit that broke something
git log -S "password" --all          # find when a string appeared (secret leak hunting)
```

## Labs (week 1, ~10 h)
1. Install Git, set identity, create an SSH key (`ssh-keygen -t ed25519`) and add it to GitHub. Enable 2FA.
2. Create `devops-lab`. Commit the `prep/lab` folder from this kit as the first commit. Add the `.gitignore` provided.
3. Branching drill: create two branches that edit the same line of `README.md`, merge one, then resolve the conflict in the second. Repeat with `rebase` instead of `merge` and compare `git lg`.
4. Undo drill: make three commits, then practise each row of the undo table. Recover a "lost" commit with `reflog`.
5. PR workflow: branch protection on `main`, open a PR from a branch, review it yourself (comment on a line), squash-merge.
6. Fork any small public repo, fix a typo, open a PR to your fork's main (practise the fork flow without bothering maintainers).
7. Write `CONTRIBUTING.md` for your repo: branch naming (`feat/`, `fix/`, `lab/`), commit style (Conventional Commits), PR template.

## Self-check
1. What does a commit object contain?
2. When is rebase dangerous?
3. `reset --hard` vs `revert`: which one do you use on a shared branch and why?
4. What is detached HEAD and how do you save work done there?
5. How would you remove a secret that was pushed three commits ago? (Hint: rotate the secret first; then `git filter-repo`; force-push; tell collaborators.)

<details><summary>Answers</summary>

1. A tree SHA, parent SHA(s), author/committer + timestamps, message.
2. When the commits were already pushed and others based work on them: rewritten SHAs diverge from their copies.
3. `revert`: it adds a new commit and does not rewrite shared history.
4. HEAD points at a commit, not a branch; `git switch -c rescue` keeps the work.
5. Rotate first (the secret is compromised the moment it was public), then rewrite history and force-push.
</details>

## Resources
- Pro Git book (free): https://git-scm.com/book
- Your PDF: git-and-github-pro.pdf (9 chapters) - read ch.1-5 on days 1-2, ch.6-9 on days 3-4.
- Practice: https://learngitbranching.js.org/ (visual branching/rebase drills)


---
[[Home]] · [[Schedule]]
