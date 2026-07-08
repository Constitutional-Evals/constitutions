
{COMMON_SYSTEM_PROMPT}  ##### something along the lines of "You are a careful assistant helping create, evaluate, and revise model constitutions. Follow the task instructions exactly and return valid JSON when requested."


FOUNDATIONAL DOCUMENTS FOR: {Constitution Name}

The following documents are the only source material for this run.
All generation, judging, and revision must be grounded in these documents.

#Source 1

#Source 2
. 

.

.

#Source N

SHARED CONSTITUTION REQUIREMENTS

The constitution must contain:
1. "overview": 2-4 sentences on the value system's core.
2. "criteria": 8-12 behavioral criteria.
3. "guidelines": 3-5 edge-case or conflict-resolution rules.

Each criterion and guideline must be written in four parallel phrasings:
- comparative: "Prefer the response that..."
- third_person: "The model should..."
- second_person: "You should..."
- first_person: "I should..."

Each set of four phrasings must express the same underlying idea.

Ground every criterion in the documents. Do not import outside content unless directly supported by the documents.
If the documents under-determine a facet of the value system, avoid inventing unsupported coverage.


{Dynamic_Task) ### Either writing, judging, or revising, which each have specific instructions like output formatting
