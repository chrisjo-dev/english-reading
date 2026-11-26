// 단어 쓰기 동의어 판정(assets/drill.js synOf, 시안 W26, W27). 함수 두 개만 떼어 돌린다
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const js = fs.readFileSync(new URL('../assets/drill.js', import.meta.url), 'utf8');
const part = (a, b) => js.slice(js.indexOf(a), js.indexOf(b));
const synOf = new Function(part('function norm(', 'function dist(') + part('function synOf(', 'function answer(') + 'return synOf;')();

test('동의어와 그 활용형은 안내, 아닌 말은 틀림', () => {
  const c = { l: 'en', w: 'serving', sy: ['helping', 'portion'] };
  assert.equal(synOf(c, 'portion'), 'portion');
  assert.equal(synOf(c, 'Portions'), 'portion');  // 빈칸은 예문 속 꼴로 쓴다
  assert.equal(synOf(c, 'help'), undefined);      // 동의어에서 어미를 떼는 쪽은 보지 않는다
  assert.equal(synOf({ l: 'en', w: 'x' }, 'portion'), undefined);  // sy 없는 예전 카드
});

test('독일어는 관사를 붙여 써도, 일본어는 가타카나와 읽기로 써도 알아본다', () => {
  assert.equal(synOf({ l: 'de', w: 'Gesetz', sy: ['Recht'] }, 'das Recht'), 'Recht');
  assert.equal(synOf({ l: 'ja', w: '近く', sy: ['きんじょ', '近所'] }, 'キンジョ'), 'きんじょ');
});
