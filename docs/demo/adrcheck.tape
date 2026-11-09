# adrcheck in 66 seconds on the small planted repository, both directions, free tier (no model, no key).
# Render: ADRCHECK_DEMO_REPO=/path/to/planted vhs docs/demo/adrcheck.tape, from the repository root; the planted
# repository comes from: uv run python evals/planted/build.py /path/to/planted, then adrcheck compile there once.
Output "docs/img/demo.gif"
Output "docs/demo/adrcheck.mp4"
Set Shell zsh
Set FontSize 16
Set Width 1180
Set Height 640
Set Padding 18
Set TypingSpeed 35ms
Set Theme "Catppuccin Mocha"

Hide
Type `cd "$ADRCHECK_DEMO_REPO" && export PATH=$HOME/.local/bin:$PATH && export PROMPT='%F{green}❯%f ' && setopt interactivecomments && clear`
Enter
Sleep 500ms
Show

Type "# An ADR says what the code must do. adrcheck holds code to it, both directions."
Enter
Sleep 2500ms
Type "sed -n '/## Decision/,/^## Consequences/p' docs/adr/0001-*.md | head -4"
Enter
Sleep 3500ms
Type "git show --format='%h %s' --stat 36f6b01 | head -4 && git show 36f6b01 | grep '^+from'"
Enter
Sleep 3500ms
Type "adrcheck check --commit 36f6b01 --tier free --format md"
Enter
Sleep 7s
Type "clear"
Enter
Type "# Direction two: the code moved on, the record did not."
Enter
Sleep 2500ms
Type "git show --format='%h %s' --stat b90ba4c | head -3"
Enter
Sleep 2500ms
Type "adrcheck check --commit b90ba4c --tier free --format md"
Enter
Sleep 6s
Type "adrcheck explain --adr 4 | head -5"
Enter
Sleep 6s
Type "# That was the free tier: no model call, no key. Patterns from the compiled obligations, and the stale sweep."
Enter
Sleep 3500ms
Type "# Add a model with --model and your API key: the judge reads the diff and writes why, on every finding."
Enter
Sleep 5s
