import type { DevotionalEntry } from "@/lib/devotional";

export function DailyVerseHero({ verse }: { verse: DevotionalEntry }) {
  return (
    <section className="chapel-panel rounded-lg px-6 py-8 md:px-10 md:py-10" aria-labelledby="daily-verse-title">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="page-kicker">Daily Verse / 每日金句</p>
          <h1 id="daily-verse-title" className="mt-2 max-w-3xl text-3xl font-semibold leading-tight md:text-5xl">
            {verse.reflection.zh.title}
          </h1>
        </div>
        <div className="hidden rounded-full border border-[color:var(--gold)] px-4 py-2 text-sm text-[color:var(--gold)] md:block">
          Mark 10:45
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-[1.08fr_0.92fr]">
        <div>
          <blockquote className="border-l-4 border-[color:var(--gold)] pl-5 text-xl leading-loose md:text-2xl">
            {verse.scripture.zh}
          </blockquote>
          <p className="mt-4 text-sm font-medium text-[color:var(--brand)]">{verse.source.reference.zh}</p>
        </div>

        <div className="grid gap-5">
          <div>
            <p className="text-sm font-semibold text-[color:var(--gold)]">Reflection / 靈修反思</p>
            <p className="mt-3 leading-8 text-[color:var(--muted)]">{verse.reflection.zh.body}</p>
          </div>
          <div className="rounded-lg border border-[color:var(--line)] bg-white/55 p-4 dark:bg-white/5">
            <p className="text-sm font-semibold text-[color:var(--brand)]">Prayer / 回應禱告</p>
            <p className="mt-2 leading-7">{verse.reflection.zh.prayer}</p>
          </div>
        </div>
      </div>
    </section>
  );
}

