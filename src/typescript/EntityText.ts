/** Normalize for matching while keeping source offsets for exact name output. */
import { normalizeFinancialNumbers } from './Preprocessing.ts';
import viewRules from '../../config/contracts/source_text_view.json' with { type: 'json' };
const MARK = /[\u064b-\u065f\u0670]/;
const DISPLAY_CONTROL = new RegExp(viewRules.ignoredDisplayControls);
const JOINED_MASK = /(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4})(?=(?:from|to)\s)/gi;

export class EntityText {
  source: string;
  text: string;
  starts: number[] = [];
  ends: number[] = [];
  constructor(source: string) {
    this.source = source;
    const chars: string[] = [];
    let index = 0;
    while (index < source.length) {
      const start = index;
      let char = source[index++];
      if (DISPLAY_CONTROL.test(char)) continue;
      if (char === '\\' && index < source.length && (source[index] === 'n' || source[index] === 'r')) {
        const escaped = source[index++];
        if (escaped === 'r') continue;
        char = '\n';
      }
      if (MARK.test(char)) {
        if (this.ends.length) this.ends[this.ends.length - 1] = index;
        continue;
      }
      char = normalizeFinancialNumbers(char);
      if (/\s/.test(char)) {
        if (!chars.length) continue;
        if (chars[chars.length - 1] === ' ') {
          this.ends[this.ends.length - 1] = index;
          continue;
        }
        char = ' ';
      }
      chars.push(char); this.starts.push(start); this.ends.push(index);
    }
    if (chars[chars.length - 1] === ' ') { chars.pop(); this.starts.pop(); this.ends.pop(); }
    const joined = [...chars.join('').matchAll(JOINED_MASK)];
    for (let i = joined.length - 1; i >= 0; i--) {
      const match = joined[i];
      const at = match.index! + match[0].length;
      const position = this.ends[at - 1];
      chars.splice(at, 0, ' '); this.starts.splice(at, 0, position); this.ends.splice(at, 0, position);
    }
    this.text = chars.join('');
  }
  exact(start: number, end: number): string | null {
    return start >= 0 && start < end && end <= this.text.length ? this.source.slice(this.starts[start], this.ends[end - 1]) : null;
  }
}
