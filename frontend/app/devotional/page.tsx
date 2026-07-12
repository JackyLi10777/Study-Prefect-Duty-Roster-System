import { PageHeader } from "@/components/PageHeader";
import { getFoundationalVerse, selectDailyVerse } from "@/lib/devotional";

export default function DevotionalPage() {
  const daily = selectDailyVerse();
  const foundational = getFoundationalVerse();

  return (
    <div>
      <PageHeader kicker="Daily Verse / 每日金句" title="Devotional Library">
        The devotional module is the spiritual center of the system, keeping servant leadership visible inside daily administration.
      </PageHeader>
      <div className="grid gap-5">
        {[foundational, daily].map((verse) => (
          <article className="rounded-lg border border-[color:var(--line)] bg-white/70 p-6 dark:bg-white/5" key={verse.id}>
            <p className="text-sm font-semibold text-[color:var(--brand)]">{verse.source.reference.zh}</p>
            <h2 className="mt-2 text-xl font-semibold">{verse.reflection.zh.title}</h2>
            <p className="mt-3 leading-8">{verse.scripture.zh}</p>
            <p className="mt-4 leading-7 text-[color:var(--muted)]">{verse.reflection.zh.body}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

