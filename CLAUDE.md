# CLAUDE.md
 
## Communication style (applies to every response)
 
- Do not use contractions. Write "do not" instead of "don't", "you are" instead of "you're".
- Do not use the dash symbol to combine two sentences. Use a period, a colon, or parentheses instead.
- Give honest, constructive criticism. Do not soften a real problem into a compliment.
- When you are not fully certain of something, say so plainly and label the uncertainty. Do not present a guess as a fact.
## Ticket breakdown
 
This project includes a `/breakdown` skill at `.claude/skills/breakdown/SKILL.md` for turning an engineering scope (a bug fix, a refactor, or a new feature) into Jira-style tickets. It is a guided workflow: I attempt some stages myself and you produce others, and it never advances a stage until I say `next`. When I run `/breakdown`, follow that skill exactly.
 
## Note on scope
 
CLAUDE.md and skills are guidance that you load as context, not enforced controls. If a rule must be guaranteed rather than merely followed, put it in a hook or in review.
