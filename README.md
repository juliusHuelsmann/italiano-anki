# anki-italiano

My custom italian decks. I'm currently learning italian.
- Notes are stored as CSV files under `notes/` next to the corresponding `.md` file that describes its content.
- Study modes ("practices") are stored as JSON under `practices/`.
- Tag conventions are placed in `taxonomy/tag_schema.md`
- Scripts update notes and generate filtered decks via AnkiConnect.

Requirements (all free):
- Anki Desktop
- AnkiConnect add-on (Anki must be running for scripts to talk to it)
- Python 3.10+

## Initial setup Ubuntu

### 1) Install Anki
The apt package is outdated LTS. The snap package is new enough. If you want a newer version or are on a different OS, download from github.

```bash
sudo snap install anki-desktop
```

### 2) Install Plugins
Open 
```bash
anki-desktop
```

- `Tools/Add-ons/Get Add-ons/`: enter (Code=2055492159)
- `Tools/Add-ons/View files/`: Copy the repo folder `addon/italiano_practice_builder` into the file addons21
  - Check for updates
  - [Optional] Adjust `target` to whatever anki complains does not exist during the build process (you'll see that later)


### 3) Create deck

Create a deck called Italiano

### 4) Change settings
Tools -> Manage Note Types -> Italiano::Cloze

**Front side**
```html
{{SentenceCloze}}

<br><br>

<input id="typeans">
```

**back side**
```html
{{FrontSide}}

<hr id=answer>

Correct: <span id="correct">{{Answer}}</span>

<script>
(function() {
    function normalize(s) {
        return s
            .toLowerCase()
            .normalize("NFD")
            .replace(/[\u0300-\u036f]/g, "")   // remove accents
            .replace(/\s+/g, " ")
            .trim();
    }

    const input = document.getElementById("typeans");
    const correct = document.getElementById("correct").innerText;

    if (!input) return;

    const user = normalize(input.value);
    const expected = normalize(correct);

    const result = document.createElement("div");

    if (user === expected) {
        result.innerHTML = "<b style='color:green'>✓ Correct</b>";
    } else {
        result.innerHTML =
            "<b style='color:red'>✗ Your answer:</b> " + input.value +
            "<br><b>Expected:</b> " + correct;
    }

    input.replaceWith(result);
})();
</script>

<br><br>
{{FullSentenceIT}}
<br>
{{TranslationEN}}
<br><br>
{{Extra}}
```

This allows me to type in the answer, and be a bit forgiving when i dont wanna type accents or capitalize.

## Release Ubuntu

### Start anki desktop
```bash
anki-desktop
```

### Import the changes
```bash
./release.sh
```

### Import the filters
Tools -> Reload Italiano practices (filtered decks).

## Notes:
- Scripts only manage notes tagged `managed::italiano_repo`.
- Tags starting with `my::` are treated as manual tags and are never removed.
