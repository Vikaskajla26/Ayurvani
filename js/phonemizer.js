// Unicode transliterator from Devanagari to SLP1
function devanagariToSlp1(text) {
  const vowels = {
    '\u0905': 'a', '\u0906': 'A', '\u0907': 'i', '\u0908': 'I', '\u0909': 'u', '\u090A': 'U',
    '\u090B': 'f', '\u0960': 'F', '\u090C': 'x', '\u0961': 'X', '\u090F': 'e', '\u0910': 'E',
    '\u0913': 'o', '\u0914': 'O'
  };
  const vowelSigns = {
    '\u093E': 'A', '\u093F': 'i', '\u0940': 'I', '\u0941': 'u', '\u0942': 'U',
    '\u0943': 'f', '\u0944': 'F', '\u0962': 'x', '\u0963': 'X', '\u0947': 'e',
    '\u0948': 'E', '\u094B': 'o', '\u094C': 'O'
  };
  const consonants = {
    '\u0915': 'k', '\u0916': 'K', '\u0917': 'g', '\u0918': 'G', '\u0919': 'N',
    '\u091A': 'c', '\u091B': 'C', '\u091C': 'j', '\u091D': 'J', '\u091E': 'Y',
    '\u091F': 'w', '\u0920': 'W', '\u0921': 'q', '\u0922': 'Q', '\u0923': 'R',
    '\u0924': 't', '\u0925': 'T', '\u0926': 'd', '\u0927': 'D', '\u0928': 'n',
    '\u092A': 'p', '\u092B': 'P', '\u092C': 'b', '\u092D': 'B', '\u092E': 'm',
    '\u092F': 'y', '\u0930': 'r', '\u0932': 'l', '\u0935': 'v', '\u0936': 'S',
    '\u0937': 'z', '\u0938': 's', '\u0939': 'h', '\u0933': 'L'
  };
  const markers = {
    '\u0902': 'M', // Anusvara
    '\u0903': 'H', // Visarga
    '\u0901': '~', // Candrabindu
    '\u093D': "'", // Avagraha
    '\u1CF5': 'Z', // Jihvamuliya ᳵ
    '\u1CF6': 'V'  // Upadhmaniya ᳶ
  };

  let slp1 = "";
  let i = 0;
  while (i < text.length) {
    let ch = text[i];
    if (vowels[ch]) {
      slp1 += vowels[ch];
      i++;
    } else if (consonants[ch]) {
      let mappedCons = consonants[ch];
      let nextCh = i + 1 < text.length ? text[i + 1] : '';
      if (vowelSigns[nextCh]) {
        slp1 += mappedCons + vowelSigns[nextCh];
        i += 2;
      } else if (nextCh === '\u094D') { // Halant
        slp1 += mappedCons;
        i += 2;
      } else {
        slp1 += mappedCons + 'a';
        i++;
      }
    } else if (markers[ch]) {
      slp1 += markers[ch];
      i++;
    } else if (ch === ' ' || ch === '।') {
      slp1 += ' ';
      i++;
    } else if (ch === '॥' || ch === '|') {
      slp1 += ' | ';
      i++;
    } else {
      slp1 += ch;
      i++;
    }
  }
  
  // Vedic extensions and pauses
  slp1 = slp1.replace(/~y/g, 'y~');
  slp1 = slp1.replace(/\./g, '|');
  return slp1.replace(/\s+/g, ' ');
}

class SanskritChandasPhonemizer {
  static normalize(text) {
    if (!text) return "";
    
    // 1. Strip editorial bracketing
    let s = text.replace(/[()""''“”‘’‌‍\-\[\]]/g, '');
    
    // 2. Strip verse-number blocks and digits
    s = s.replace(/\s*[०-९0-9]+\s*[।॥]+/g, '॥');
    s = s.replace(/[०-९0-9]+/g, '');
    
    // 3. Expand Om
    s = s.replace(/ॐ/g, 'ओम्');
    
    // 4. Visarga before unvoiced k-varga (क ख) -> jihvamuliya, p-varga (प फ) -> upadhmaniya
    s = s.replace(/ः([कख])/g, '\u1CF5$1');
    s = s.replace(/ः([पफ])/g, '\u1CF6$1');
    
    // 5. Anusvara rewrites
    const vargaCons = {
      'क': 'ङ्', 'ख': 'ङ्', 'ग': 'ङ्', 'घ': 'ङ्', 'ङ': 'ङ्',
      'च': 'ञ्', 'छ': 'ञ्', 'ज': 'ञ्', 'झ': 'ञ्', 'ञ': 'ञ्',
      'ट': 'ण्', 'ठ': 'ण्', 'ड': 'ण्', 'ढ': 'ण्', 'ण': 'ण्',
      'त': 'न्', 'थ': 'न्', 'द': 'न्', 'ध': 'न्', 'न': 'न्',
      'प': 'म्', 'फ': 'म्', 'ब': 'म्', 'भ': 'म्', 'म': 'म्'
    };
    const nonVargaKeep = new Set('रलवशषसह');
    const wordEnd = new Set([' ', '\t', '\n', '।', '॥']);
    
    let out = "";
    for (let i = 0; i < s.length; i++) {
      let ch = s[i];
      if (ch === 'ं') {
        let nxt = i + 1 < s.length ? s[i + 1] : '';
        if (vargaCons[nxt]) {
          out += vargaCons[nxt];
        } else if (nxt === 'य') {
          out += 'ँ';
        } else if (nonVargaKeep.has(nxt)) {
          out += 'ं';
        } else if (nxt === '' || wordEnd.has(nxt)) {
          out += 'म्';
        } else {
          out += 'ं';
        }
      } else {
        out += ch;
      }
    }
    s = out;
    
    // collapse whitespaces and duplicate dandas
    s = s.replace(/\s+/g, ' ');
    s = s.replace(/(॥)(\s*॥)+/g, '॥');
    s = s.replace(/(।)(\s*।)+/g, '।');
    return s.trim();
  }

  static toSequence(text) {
    let normalized = this.normalize(text);
    // Map Vedic extensions back to Visarga for VITS symbols mapping compatibility
    normalized = normalized.replace(/\u1CF5/g, 'ः').replace(/\u1CF6/g, 'ः');
    const seq = [];
    for (let i = 0; i < normalized.length; i++) {
      let ch = normalized[i];
      let idx = SANS_SYMBOLS.indexOf(ch);
      if (idx !== -1) {
        seq.push(idx);
      }
    }
    if (seq.length > 0 && seq[seq.length - 1] !== SANS_SYMBOLS.indexOf('।') && seq[seq.length - 1] !== SANS_SYMBOLS.indexOf('॥')) {
      seq.push(SANS_SYMBOLS.indexOf('।'));
    }
    return seq;
  }

  static syllabify(slp1) {
    const vowels = new Set('aAiIuUfFxXeEoO');
    const seps = new Set([' ', '|']);
    const syllables = [];
    const onsetBuf = [];

    const attachTrailingToLast = (cons) => {
      if (syllables.length === 0) return;
      const text = cons.join('');
      syllables[syllables.length - 1].coda += text;
      syllables[syllables.length - 1].text += text;
    };

    let i = 0;
    while (i < slp1.length) {
      const c = slp1[i];
      if (c === "'") {
        i++;
        continue;
      }
      if (seps.has(c)) {
        attachTrailingToLast(onsetBuf);
        onsetBuf.length = 0;
        if (syllables.length > 0) {
          if (c === '|') {
            syllables[syllables.length - 1].is_pada_final = true;
            syllables[syllables.length - 1].is_word_final = true;
          } else if (c === ' ') {
            syllables[syllables.length - 1].is_word_final = true;
          }
        }
        i++;
        continue;
      }
      if (vowels.has(c)) {
        const syl = {
          text: onsetBuf.join('') + c,
          onset: onsetBuf.join(''),
          vowel: c,
          coda: '',
          is_word_final: false,
          is_pada_final: false,
          weight: 'L',
          weight_cause: 'light'
        };
        syllables.push(syl);
        onsetBuf.length = 0;
        i++;

        const consBetween = [];
        while (i < slp1.length && !vowels.has(slp1[i]) && !seps.has(slp1[i]) && slp1[i] !== "'") {
          const cc = slp1[i];
          if (cc === '~' && consBetween.length > 0) {
            consBetween[consBetween.length - 1] += '~';
          } else {
            consBetween.push(cc);
          }
          i++;
        }
        if (i < slp1.length && vowels.has(slp1[i])) {
          if (consBetween.length >= 2) {
            const codaPart = consBetween.slice(0, -1);
            const onsetPart = consBetween.slice(-1);
            syllables[syllables.length - 1].coda = codaPart.join('');
            syllables[syllables.length - 1].text += syllables[syllables.length - 1].coda;
            onsetBuf.push(...onsetPart);
          } else if (consBetween.length === 1) {
            onsetBuf.push(...consBetween);
          }
        } else {
          syllables[syllables.length - 1].coda = consBetween.join('');
          syllables[syllables.length - 1].text += syllables[syllables.length - 1].coda;
          onsetBuf.length = 0;
        }
        continue;
      }
      if (c === '~' && onsetBuf.length > 0) {
        onsetBuf[onsetBuf.length - 1] += '~';
      } else {
        onsetBuf.push(c);
      }
      i++;
    }

    attachTrailingToLast(onsetBuf);
    if (syllables.length > 0) {
      syllables[syllables.length - 1].is_word_final = true;
      syllables[syllables.length - 1].is_pada_final = true;
    }
    return syllables;
  }

  static tagWeights(syllables) {
    const longVowels = new Set('AIUFXeEoO');
    const clusterChars = (str) => str.split('').filter(c => c !== '~');

    for (let k = 0; k < syllables.length; k++) {
      const s = syllables[k];
      const v = s.vowel;
      if (longVowels.has(v)) {
        s.weight = 'G';
        s.weight_cause = 'long_vowel';
        continue;
      }
      let gap = clusterChars(s.coda);
      if (!s.is_pada_final && k + 1 < syllables.length) {
        gap = gap.concat(clusterChars(syllables[k + 1].onset));
      }
      if (gap.length > 0 && gap[0] === 'H') {
        s.weight = 'G';
        s.weight_cause = 'visarga';
        continue;
      }
      if (gap.length > 0 && gap[0] === 'M') {
        s.weight = 'G';
        s.weight_cause = 'anusvara';
        continue;
      }
      if (gap.length >= 2) {
        s.weight = 'G';
        s.weight_cause = 'cluster';
        continue;
      }
      if (s.is_pada_final) {
        s.weight = 'G';
        s.weight_cause = 'pada_final_anceps';
        continue;
      }
      s.weight = 'L';
      s.weight_cause = 'light';
    }
  }

  static scan(text) {
    const norm = this.normalize(text);
    const slp1 = devanagariToSlp1(norm);
    const syls = this.syllabify(slp1);
    this.tagWeights(syls);
    
    const sylText = syls.map(s => s.text + (s.is_pada_final ? '‖' : (s.is_word_final ? '·' : ''))).join(' ');
    const pattern = syls.map(s => s.weight).join('');
    
    return {
      syls: syls,
      sylText: sylText,
      pattern: pattern
    };
  }
}
