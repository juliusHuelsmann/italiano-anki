# Tag schema

This repository uses a predictable tag taxonomy so practices remain stable.

Namespaces:
- managed::italiano_repo
  - Added automatically to all notes managed by the scripts.
- source::<folder>
  - Top-level folder under notes/, e.g. source::usage_and_nuance
- file::<csv_stem>
  - The CSV filename without extension, e.g. file::bello_bravo_buono_bene_piace
- level::<A1|A2|B1|B2|C1|C2>
- topic::<...> (optional)
- pos::<...> (optional)
- my::<...>
  - Reserved for manual tags I add manually in Anki (not in the files). Scripts will never remove tags starting with my::

Rules:
- Use spaces between tags (Anki style).
- Avoid punctuation other than :: and _.
