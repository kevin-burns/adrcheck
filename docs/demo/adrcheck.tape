# adrcheck on the small planted repository: the judge first, then the free tier. The raw render is 98 s;
# the README GIF cuts the two model waits to two seconds each (docs/img/README.md has the recipe).
# Render from the repository root with a judge key in the environment (the tape uses openai:gpt-6-luna):
#   ADRCHECK_DEMO_REPO=/path/to/planted vhs docs/demo/adrcheck.tape
# The planted repository: uv run python evals/planted/build.py /path/to/planted, then adrcheck compile there once.
Output "docs/img/demo.gif"
Output "docs/demo/adrcheck.mp4"
Set Shell zsh
Set FontSize 15
Set Width 1180
Set Height 720
Set Padding 16
Set Framerate 20
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
Type "# The judge: a model reads the diff against the record and says why."
Enter
Sleep 2000ms
Type "adrcheck check --commit 36f6b01 --model openai:gpt-6-luna --format md"
Enter
Sleep 24s
Type "clear"
Enter
Type "# Direction two: the code moved on, the record did not."
Enter
Sleep 2500ms
Type "git show --format='%h %s' --stat b90ba4c | head -3"
Enter
Sleep 2500ms
Type "adrcheck check --commit b90ba4c --model openai:gpt-6-luna --format md"
Enter
Sleep 16s
Type "clear"
Enter
Type "# No key? The free tier matches the compiled obligations' patterns. No model call."
Enter
Sleep 2500ms
Type "adrcheck check --commit 36f6b01 --tier free --format md"
Enter
Sleep 6s
Type "# Same record, same line. The judge adds the reason; the free tier is instant and free."
Enter
Sleep 5s
