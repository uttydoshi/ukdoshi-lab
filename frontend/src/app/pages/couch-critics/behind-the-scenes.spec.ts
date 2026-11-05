import { dollars, duration, llmCalls, steps } from './behind-the-scenes';
import { Span, Trace } from './runs';

function span(name: string, kind: Span['kind'], start: number, end: number, extra: Partial<Span> = {}): Span {
  return {
    span_id: name,
    parent_id: kind === 'request' ? null : 'Recap',
    name,
    kind,
    start,
    end,
    duration_ms: Math.round((end - start) * 1000),
    status: 'ok',
    note: '',
    attributes: {},
    ...extra,
  };
}

// A made-up 10-second recap: fetch the run for 1 s, then write the recap for 8 s.
const TRACE: Trace = {
  trace_id: 'a'.repeat(32),
  name: 'Recap',
  spans: [
    span('Recap', 'request', 100, 110),
    span('Fetch the run', 'data', 100, 101),
    span('Write the recap', 'llm', 102, 110, {
      attributes: {
        'gen_ai.response.model': 'claude-opus-5-5',
        'gen_ai.usage.input_tokens': 1334,
        'gen_ai.usage.output_tokens': 959,
        'lab.cost_usd': 0.024516,
      },
    }),
  ],
};

describe('behind the scenes', () => {
  it('writes times and costs simply', () => {
    expect(duration(20)).toBe('20 ms');
    expect(duration(420)).toBe('0.42 s');
    expect(duration(12756)).toBe('12.8 s');
    expect(dollars(0.024516)).toBe('$0.025');
    expect(dollars(0.0004)).toBe('under $0.001');
  });

  it('places each step on the timeline of the whole request', () => {
    const [fetch, write] = steps(TRACE);
    expect([fetch.kind, fetch.left, fetch.width, fetch.time]).toEqual(['Data', 0, 10, '1.0 s']);
    expect([write.kind, write.left, write.width, write.time]).toEqual(['LLM', 20, 80, '8.0 s']);
  });

  it("reads each Claude call's model, tokens and cost", () => {
    expect(llmCalls(TRACE)).toEqual([
      { name: 'Write the recap', model: 'claude-opus-5-5', tokensIn: 1334, tokensOut: 959, cost: 0.024516, time: '8.0 s' },
    ]);
  });
});
