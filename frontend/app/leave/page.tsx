import { PageHeader } from "@/components/PageHeader";

export default function LeavePage() {
  return (
    <div>
      <PageHeader kicker="Leave Adjustment / 發布後修改" title="Post-publication Adjustment">
        This workflow will help find compliant substitutes after publication while preserving fairness, patience, and care for affected students.
      </PageHeader>
      <section className="rounded-lg border border-[color:var(--line)] bg-white/70 p-6 dark:bg-white/5">
        <h2 className="font-semibold">Next implementation target</h2>
        <p className="mt-2 leading-7 text-[color:var(--muted)]">
          Connect published roster data, leave requests, substitute recommendation, and weight transfer validation.
        </p>
      </section>
    </div>
  );
}

