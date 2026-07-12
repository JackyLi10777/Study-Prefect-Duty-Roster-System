import { PageHeader } from "@/components/PageHeader";
import { selectDailyVerse } from "@/lib/devotional";

export default function RosterPage() {
  const verse = selectDailyVerse(new Date(), "roster-generation");

  return (
    <div>
      <PageHeader kicker="Generate Roster / 排值班表" title="Weekly Duty Roster">
        Generate and publish a weekly roster while protecting AHP eligibility, room schedules, no-consecutive-duty rules, and fairness by history weight.
      </PageHeader>

      <section className="rounded-lg border border-[color:var(--line)] bg-white/70 p-6 dark:bg-white/5">
        <p className="text-sm font-semibold text-[color:var(--brand)]">{verse.source.reference.zh}</p>
        <p className="mt-3 leading-8">{verse.scripture.zh}</p>
        <p className="mt-4 text-sm text-[color:var(--muted)]">{verse.reflection.zh.prayer}</p>
      </section>
    </div>
  );
}

