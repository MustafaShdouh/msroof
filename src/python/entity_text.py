"""A normalized matching view that projects names back to exact source text."""
import re
import json
from pathlib import Path
from .preprocessing import normalize_financial_numbers

MARK = re.compile(r"[\u064b-\u065f\u0670]")
VIEW_RULES = json.loads((Path(__file__).resolve().parents[2]/'config/contracts/source_text_view.json').read_text(encoding='utf-8'))
DISPLAY_CONTROL = re.compile(VIEW_RULES['ignoredDisplayControls'])
JOINED_MASK = re.compile(r"(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4})(?=(?:from|to)\s)", re.I)


class EntityText:
    def __init__(self, source):
        self.source, chars, self.starts, self.ends = source, [], [], []
        index = 0
        while index < len(source):
            start, char = index, source[index]
            index += 1
            if DISPLAY_CONTROL.fullmatch(char):
                continue
            if char == "\\" and index < len(source) and source[index] in "nr":
                escaped = source[index]
                index += 1
                if escaped == "r":
                    continue
                char = "\n"
            if MARK.fullmatch(char):
                if self.ends:
                    self.ends[-1] = index
                continue
            char = normalize_financial_numbers(char)
            if char.isspace():
                if not chars:
                    continue
                if chars[-1] == " ":
                    self.ends[-1] = index
                    continue
                char = " "
            chars.append(char)
            self.starts.append(start)
            self.ends.append(index)
        if chars and chars[-1] == " ":
            chars.pop(); self.starts.pop(); self.ends.pop()
        text = "".join(chars)
        for match in reversed(list(JOINED_MASK.finditer(text))):
            at = match.end()
            chars.insert(at, " ")
            position = self.ends[at - 1]
            self.starts.insert(at, position)
            self.ends.insert(at, position)
        self.text = "".join(chars)

    def exact(self, start, end):
        if not 0 <= start < end <= len(self.text):
            return None
        return self.source[self.starts[start]:self.ends[end - 1]]
