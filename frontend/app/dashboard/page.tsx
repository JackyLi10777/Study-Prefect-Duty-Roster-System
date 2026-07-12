import { DailyVerseHero } from "@/components/DailyVerseHero";
import { selectDailyVerse } from "@/lib/devotional";

export default function DashboardPage() {
  const verse = selectDailyVerse(new Date(), "dashboard-hero");

  return (
    <div>
      <DailyVerseHero verse={verse} />

      <section className="mt-8 grid gap-4 md:grid-cols-3">
        {[
          ["Generate & Publish", "Prepare the weekly duty roster with fairness and room rules protected."],
          ["Leave Adjustment", "Modify a published roster with patience, transparency, and care."],
          ["Fairness Audit", "Review load, history weight, and responsibility as service, not privilege."]
        ].map(([title, body]) => (
          <article className="rounded-lg border border-[color:var(--line)] bg-white/70 p-5 shadow-calm dark:bg-white/5" key={title}>
            <h2 className="font-semibold">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-[color:var(--muted)]">{body}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

